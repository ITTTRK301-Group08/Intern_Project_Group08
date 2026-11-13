from datetime import date, datetime
import logging

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerRole
from app.models.interview import InterviewQuestion, InterviewSession
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.models.profile_data import CareerRoleSkill
from app.models.student_profile import StudentProfile

logger = logging.getLogger(__name__)


def calculate_readiness_score(skill_items: list[dict]) -> float:
    """Tính điểm sẵn sàng nghề nghiệp theo công thức chuẩn SRS Section 6.3:

    Readiness = [ Sum(w_i * min(current_i / required_i, 1.0)) / Sum(w_i) ] * 100
    """
    if not skill_items:
        return 0.0

    total_weight = 0.0
    weighted_score = 0.0

    for item in skill_items:
        current = max(0, item.get("current_level", 0))
        required = max(1, item.get("required_level", 1))
        weight = max(0.1, item.get("weight", 1.0))

        ratio = min(current / required, 1.0)
        weighted_score += weight * ratio
        total_weight += weight

    if total_weight <= 0:
        return 0.0

    return round((weighted_score / total_weight) * 100, 1)


def get_latest_completed_analysis(db: Session, user_id: int) -> Analysis | None:
    return db.scalar(
        select(Analysis)
        .options(
            joinedload(Analysis.career_role),
            joinedload(Analysis.skill_gaps).joinedload(AnalysisSkillGap.skill),
        )
        .where(Analysis.user_id == user_id, Analysis.status == "completed")
        .order_by(desc(Analysis.completed_at), desc(Analysis.created_at))
        .limit(1)
    )


def get_dashboard_summary(db: Session, *, user_id: int) -> dict:
    latest_analysis = get_latest_completed_analysis(db, user_id)

    readiness_score = 0.0
    target_role_id = None
    target_role_name = None
    target_role_level = None
    total_skills = 0
    matched_skills = 0
    gap_skills = 0
    last_analyzed_at = None

    if latest_analysis:
        last_analyzed_at = latest_analysis.completed_at or latest_analysis.created_at
        if latest_analysis.career_role:
            target_role_id = latest_analysis.career_role.id
            target_role_name = latest_analysis.career_role.name
            target_role_level = latest_analysis.career_role.level

        # Lấy trọng số từ career_role_skills nếu có
        role_skills_weights = {}
        if latest_analysis.career_role_id:
            role_skills = db.scalars(
                select(CareerRoleSkill).where(
                    CareerRoleSkill.career_role_id == latest_analysis.career_role_id
                )
            ).all()
            for rs in role_skills:
                role_skills_weights[rs.skill_id] = rs.weight

        evaluated_items = []
        for sg in latest_analysis.skill_gaps:
            weight = role_skills_weights.get(sg.skill_id, 1.0)
            evaluated_items.append({
                "current_level": sg.current_level,
                "required_level": sg.target_level,
                "weight": weight,
            })
            total_skills += 1
            if sg.current_level >= sg.target_level:
                matched_skills += 1
            else:
                gap_skills += 1

        readiness_score = calculate_readiness_score(evaluated_items)
    else:
        # Nếu chưa có analysis nào hoàn thành, kiểm tra student_profile để lấy role mục tiêu nếu có
        profile = db.scalar(
            select(StudentProfile)
            .options(joinedload(StudentProfile.target_role))
            .where(StudentProfile.user_id == user_id)
        )
        if profile and profile.target_role:
            target_role_id = profile.target_role.id
            target_role_name = profile.target_role.name
            target_role_level = profile.target_role.level

    # Tổng số báo cáo phân tích
    total_analyses = db.scalar(
        select(func.count(Analysis.id)).where(Analysis.user_id == user_id)
    ) or 0

    # Tổng số phỏng vấn
    total_interviews = db.scalar(
        select(func.count(InterviewSession.id)).where(InterviewSession.user_id == user_id)
    ) or 0

    # Lộ trình học tập đang active
    active_plan = db.scalar(
        select(LearningPlan)
        .options(
            joinedload(LearningPlan.analysis).joinedload(Analysis.career_role),
            joinedload(LearningPlan.items),
        )
        .where(LearningPlan.user_id == user_id, LearningPlan.status == "active")
        .order_by(desc(LearningPlan.created_at))
        .limit(1)
    )

    active_plan_brief = None
    if active_plan:
        items = list(active_plan.items) if active_plan.items else []
        tot_tasks = len(items)
        comp_tasks = sum(1 for it in items if it.is_completed)
        prog = round((comp_tasks / tot_tasks) * 100, 1) if tot_tasks > 0 else 0.0
        days_left = max(0, (active_plan.end_date - date.today()).days)

        active_plan_brief = {
            "id": active_plan.id,
            "title": active_plan.title,
            "target_role": active_plan.analysis.career_role.name if (active_plan.analysis and active_plan.analysis.career_role) else None,
            "start_date": active_plan.start_date,
            "end_date": active_plan.end_date,
            "days_left": days_left,
            "total_tasks": tot_tasks,
            "completed_tasks": comp_tasks,
            "progress_percent": prog,
        }

    return {
        "readiness_score": readiness_score,
        "target_role_id": target_role_id,
        "target_role": target_role_name,
        "target_role_level": target_role_level,
        "total_analyses": total_analyses,
        "total_interviews": total_interviews,
        "total_skills_evaluated": total_skills,
        "skills_matched_count": matched_skills,
        "skills_gap_count": gap_skills,
        "active_plan": active_plan_brief,
        "last_analyzed_at": last_analyzed_at,
    }


def get_skill_radar_data(db: Session, *, user_id: int, analysis_id: int | None = None) -> dict:
    analysis = None
    if analysis_id is not None:
        analysis = db.scalar(
            select(Analysis)
            .options(
                joinedload(Analysis.career_role),
                joinedload(Analysis.skill_gaps).joinedload(AnalysisSkillGap.skill),
            )
            .where(Analysis.id == analysis_id, Analysis.user_id == user_id)
        )
    else:
        analysis = get_latest_completed_analysis(db, user_id)

    if not analysis:
        # Trả về kết quả rỗng có cấu trúc chuẩn nếu chưa có phân tích
        return {
            "role_id": None,
            "role_name": None,
            "role_level": None,
            "overall_readiness": 0.0,
            "skills": [],
        }

    # Lấy trọng số kỹ năng
    role_skills_weights = {}
    if analysis.career_role_id:
        role_skills = db.scalars(
            select(CareerRoleSkill).where(
                CareerRoleSkill.career_role_id == analysis.career_role_id
            )
        ).all()
        for rs in role_skills:
            role_skills_weights[rs.skill_id] = rs.weight

    radar_items = []
    calc_items = []
    for sg in analysis.skill_gaps:
        skill_name = sg.skill.name if sg.skill else f"Kỹ năng #{sg.skill_id}"
        gap = max(0, sg.target_level - sg.current_level)
        weight = role_skills_weights.get(sg.skill_id, 1.0)
        is_gap = sg.current_level < sg.target_level

        radar_items.append({
            "skill_id": sg.skill_id,
            "skill_name": skill_name,
            "current_level": sg.current_level,
            "required_level": sg.target_level,
            "gap_score": gap,
            "weight": weight,
            "is_gap": is_gap,
        })
        calc_items.append({
            "current_level": sg.current_level,
            "required_level": sg.target_level,
            "weight": weight,
        })

    overall_readiness = calculate_readiness_score(calc_items)

    return {
        "role_id": analysis.career_role_id,
        "role_name": analysis.career_role.name if analysis.career_role else None,
        "role_level": analysis.career_role.level if analysis.career_role else None,
        "overall_readiness": overall_readiness,
        "skills": radar_items,
    }


def get_learning_progress(db: Session, *, user_id: int) -> dict:
    plan = db.scalar(
        select(LearningPlan)
        .options(
            joinedload(LearningPlan.analysis).joinedload(Analysis.career_role),
            joinedload(LearningPlan.items),
        )
        .where(LearningPlan.user_id == user_id, LearningPlan.status == "active")
        .order_by(desc(LearningPlan.created_at))
        .limit(1)
    )

    if not plan:
        # Nếu không có active plan, thử lấy plan gần nhất
        plan = db.scalar(
            select(LearningPlan)
            .options(
                joinedload(LearningPlan.analysis).joinedload(Analysis.career_role),
                joinedload(LearningPlan.items),
            )
            .where(LearningPlan.user_id == user_id)
            .order_by(desc(LearningPlan.created_at))
            .limit(1)
        )

    if not plan:
        return {
            "has_active_plan": False,
            "plan": None,
            "weekly_breakdown": [],
        }

    items = list(plan.items) if plan.items else []
    total_tasks = len(items)
    completed_tasks = sum(1 for it in items if it.is_completed)
    progress_pct = (
        round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0.0
    )
    days_left = max(0, (plan.end_date - date.today()).days)

    plan_brief = {
        "id": plan.id,
        "title": plan.title,
        "target_role": plan.analysis.career_role.name if (plan.analysis and plan.analysis.career_role) else None,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "days_left": days_left,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress_percent": progress_pct,
    }

    # Thống kê theo từng tuần 1 đến 4
    weeks: dict[int, dict] = {w: {"total": 0, "completed": 0} for w in range(1, 5)}
    for it in items:
        w_num = it.week_number if 1 <= it.week_number <= 4 else 1
        weeks[w_num]["total"] += 1
        if it.is_completed:
            weeks[w_num]["completed"] += 1

    weekly_breakdown = []
    for w in range(1, 5):
        w_tot = weeks[w]["total"]
        w_comp = weeks[w]["completed"]
        w_pct = round((w_comp / w_tot) * 100, 1) if w_tot > 0 else 0.0
        weekly_breakdown.append({
            "week_number": w,
            "total_tasks": w_tot,
            "completed_tasks": w_comp,
            "progress_percent": w_pct,
        })

    return {
        "has_active_plan": plan.status == "active",
        "plan": plan_brief,
        "weekly_breakdown": weekly_breakdown,
    }


def get_interview_history(
    db: Session,
    *,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    offset = max(0, (page - 1) * page_size)

    total = db.scalar(
        select(func.count(InterviewSession.id)).where(InterviewSession.user_id == user_id)
    ) or 0

    sessions = db.scalars(
        select(InterviewSession)
        .options(
            joinedload(InterviewSession.career_role),
            joinedload(InterviewSession.questions),
        )
        .where(InterviewSession.user_id == user_id)
        .order_by(desc(InterviewSession.created_at))
        .offset(offset)
        .limit(page_size)
    ).unique().all()

    items = []
    for s in sessions:
        role_name = s.career_role.name if s.career_role else "Chưa xác định"
        items.append({
            "id": s.id,
            "career_role_id": s.career_role_id,
            "career_role_name": role_name,
            "status": s.status,
            "created_at": s.created_at,
            "question_count": len(s.questions) if s.questions else 0,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
