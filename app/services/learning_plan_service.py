from datetime import date, datetime, timedelta, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerRole, Skill
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.models.learning_resource import LearningResource
from app.models.profile_data import CareerRoleSkill

logger = logging.getLogger(__name__)

PLAN_NOT_FOUND = "LEARNING_PLAN_NOT_FOUND"
PLAN_FORBIDDEN = "LEARNING_PLAN_FORBIDDEN"
ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"
ANALYSIS_FORBIDDEN = "ANALYSIS_FORBIDDEN"
ANALYSIS_NOT_COMPLETED = "ANALYSIS_NOT_COMPLETED"
ACTIVE_PLAN_EXISTS = "ACTIVE_PLAN_EXISTS"
ITEM_NOT_FOUND = "LEARNING_PLAN_ITEM_NOT_FOUND"


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "data": {"code": code}, "message": message},
    )


def serialize_plan_item(item: LearningPlanItem) -> dict:
    resource_brief = None
    if item.resource:
        resource_brief = {
            "id": item.resource.id,
            "title": item.resource.title,
            "provider": item.resource.provider,
            "url": item.resource.url,
            "resource_type": item.resource.resource_type,
            "language": item.resource.language,
            "is_free": item.resource.is_free,
        }

    return {
        "id": item.id,
        "plan_id": item.plan_id,
        "skill_id": item.skill_id,
        "skill_name": item.skill.name if item.skill else f"Kỹ năng #{item.skill_id}",
        "resource_id": item.resource_id,
        "resource": resource_brief,
        "week_number": item.week_number,
        "task_description": item.task_description,
        "estimated_hours": item.estimated_hours,
        "is_completed": item.is_completed,
        "completed_at": item.completed_at,
    }


def serialize_plan(plan: LearningPlan, include_items: bool = True) -> dict:
    target_role_name = None
    if plan.analysis and plan.analysis.career_role:
        target_role_name = plan.analysis.career_role.name

    items_list = list(plan.items) if plan.items else []
    total_items = len(items_list)
    completed_items = sum(1 for it in items_list if it.is_completed)
    progress_percent = (
        round((completed_items / total_items) * 100, 1) if total_items > 0 else 0.0
    )

    data = {
        "id": plan.id,
        "user_id": plan.user_id,
        "analysis_id": plan.analysis_id,
        "target_role": target_role_name,
        "title": plan.title,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "status": plan.status,
        "created_at": plan.created_at,
        "total_items": total_items,
        "completed_items": completed_items,
        "progress_percent": progress_percent,
    }

    if include_items:
        data["items"] = [serialize_plan_item(item) for item in items_list]

    return data


def create_plan_from_analysis(
    db: Session,
    *,
    user_id: int,
    analysis_id: int,
    title: str | None = None,
    duration_days: int = 30,
) -> dict:
    # 1. Kiểm tra báo cáo phân tích
    analysis = db.scalar(
        select(Analysis)
        .options(
            joinedload(Analysis.career_role),
            joinedload(Analysis.skill_gaps).joinedload(AnalysisSkillGap.skill),
        )
        .where(Analysis.id == analysis_id)
    )
    if not analysis:
        raise _error(status.HTTP_404_NOT_FOUND, ANALYSIS_NOT_FOUND, "Không tìm thấy báo cáo phân tích.")
    if analysis.user_id != user_id:
        raise _error(status.HTTP_403_FORBIDDEN, ANALYSIS_FORBIDDEN, "Bạn không có quyền truy cập báo cáo phân tích này.")
    if analysis.status != "completed":
        raise _error(
            status.HTTP_400_BAD_REQUEST,
            ANALYSIS_NOT_COMPLETED,
            "Chỉ có thể tạo lộ trình học tập từ báo cáo phân tích đã hoàn thành.",
        )

    # 2. Quy tắc nghiệp vụ BR-06: Một báo cáo chỉ có tối đa 1 lộ trình đang hoạt động (active)
    existing_active = db.scalar(
        select(LearningPlan).where(
            LearningPlan.analysis_id == analysis_id,
            LearningPlan.status == "active",
        )
    )
    if existing_active:
        raise _error(
            status.HTTP_400_BAD_REQUEST,
            ACTIVE_PLAN_EXISTS,
            "Đã tồn tại một lộ trình học tập đang hoạt động cho báo cáo này. "
            "Vui lòng hoàn thành hoặc lưu trữ lộ trình trước khi tạo lộ trình mới.",
        )

    # 3. Xác định tiêu đề và khung thời gian
    role_name = analysis.career_role.name if analysis.career_role else "Chuyên môn mục tiêu"
    if not title or not title.strip():
        plan_title = f"Lộ trình 30 ngày chinh phục vị trí {role_name}"
    else:
        plan_title = title.strip()

    start_date = date.today()
    end_date = start_date + timedelta(days=duration_days)

    plan = LearningPlan(
        user_id=user_id,
        analysis_id=analysis_id,
        title=plan_title,
        start_date=start_date,
        end_date=end_date,
        status="active",
    )
    db.add(plan)
    db.flush()

    # 4. Xác định kỹ năng cần học từ báo cáo phân tích
    # Ưu tiên các kỹ năng có gap lớn (target_level - current_level > 0)
    gap_items = []
    for sg in analysis.skill_gaps:
        gap_size = max(0, sg.target_level - sg.current_level)
        gap_items.append({
            "skill": sg.skill,
            "gap_size": gap_size,
            "current_level": sg.current_level,
            "target_level": sg.target_level,
        })

    # Sắp xếp kỹ năng theo độ hụt lớn nhất trước
    gap_items.sort(key=lambda x: x["gap_size"], reverse=True)

    # Nếu không có kỹ năng nào bị hụt hoặc danh sách rỗng, lấy kỹ năng của role
    if not gap_items:
        if analysis.career_role_id:
            role_skills = db.scalars(
                select(CareerRoleSkill)
                .options(joinedload(CareerRoleSkill.skill))
                .where(CareerRoleSkill.career_role_id == analysis.career_role_id)
            ).all()
            gap_items = [
                {"skill": rs.skill, "gap_size": 1, "current_level": 2, "target_level": rs.required_level}
                for rs in role_skills if rs.skill
            ]
        if not gap_items:
            # Fallback lấy các kỹ năng phổ biến trong hệ thống
            fallback_skills = db.scalars(select(Skill).limit(3)).all()
            gap_items = [
                {"skill": s, "gap_size": 1, "current_level": 2, "target_level": 4}
                for s in fallback_skills
            ]

    # Lấy tài nguyên học tập cho các kỹ năng này
    skill_ids = [g["skill"].id for g in gap_items if g["skill"]]
    resources = db.scalars(
        select(LearningResource).where(
            LearningResource.skill_id.in_(skill_ids),
            LearningResource.is_active == True,  # noqa: E712
        )
    ).all()
    resource_map: dict[int, list[LearningResource]] = {}
    for res in resources:
        if res.skill_id not in resource_map:
            resource_map[res.skill_id] = []
        resource_map[res.skill_id].append(res)

    # 5. Phân bổ nhiệm vụ theo cấu trúc 4 tuần chuẩn của lộ trình 30 ngày
    # Tuần 1: Củng cố nền tảng lý thuyết & Kiến thức trọng tâm
    # Tuần 2: Nâng cao năng lực chuyên môn & Bài tập thực hành
    # Tuần 3: Ứng dụng thực tế & Triển khai Mini-project
    # Tuần 4: Tối ưu mã nguồn, Portfolio & Ôn luyện phỏng vấn
    primary_skills = gap_items[:3] if len(gap_items) >= 3 else gap_items

    tasks_to_add: list[LearningPlanItem] = []

    # Tuần 1
    for idx, item in enumerate(primary_skills):
        skill = item["skill"]
        res_list = resource_map.get(skill.id, [])
        doc_res = next((r for r in res_list if r.resource_type in ("documentation", "course")), None) or (res_list[0] if res_list else None)
        task_desc = f"Nắm vững lý thuyết nền tảng, kiến trúc và cú pháp cốt lõi của {skill.name} (mục tiêu nâng từ mức {item['current_level']} lên {item['target_level']})."
        tasks_to_add.append(
            LearningPlanItem(
                plan_id=plan.id,
                skill_id=skill.id,
                resource_id=doc_res.id if doc_res else None,
                week_number=1,
                task_description=task_desc,
                estimated_hours=6.0,
                is_completed=False,
            )
        )

    # Tuần 2
    for idx, item in enumerate(primary_skills):
        skill = item["skill"]
        res_list = resource_map.get(skill.id, [])
        practice_res = next((r for r in res_list if r.resource_type in ("practice", "course")), None) or (res_list[-1] if res_list else None)
        task_desc = f"Thực hành bài tập chuyên sâu, giải quyết vấn đề và xây dựng module xử lý với {skill.name}."
        tasks_to_add.append(
            LearningPlanItem(
                plan_id=plan.id,
                skill_id=skill.id,
                resource_id=practice_res.id if practice_res else None,
                week_number=2,
                task_description=task_desc,
                estimated_hours=8.0,
                is_completed=False,
            )
        )

    # Tuần 3
    for idx, item in enumerate(primary_skills[:2]):
        skill = item["skill"]
        res_list = resource_map.get(skill.id, [])
        res = res_list[0] if res_list else None
        task_desc = f"Xây dựng Mini-Project thực tế ứng dụng {skill.name} chuẩn hóa theo nghiệp vụ vị trí {role_name}."
        tasks_to_add.append(
            LearningPlanItem(
                plan_id=plan.id,
                skill_id=skill.id,
                resource_id=res.id if res else None,
                week_number=3,
                task_description=task_desc,
                estimated_hours=10.0,
                is_completed=False,
            )
        )

    # Tuần 4
    for idx, item in enumerate(primary_skills[:2]):
        skill = item["skill"]
        res_list = resource_map.get(skill.id, [])
        res = res_list[0] if res_list else None
        task_desc = f"Tối ưu mã nguồn, hoàn thiện README portfolio và ôn luyện bộ câu hỏi phỏng vấn trọng điểm về {skill.name}."
        tasks_to_add.append(
            LearningPlanItem(
                plan_id=plan.id,
                skill_id=skill.id,
                resource_id=res.id if res else None,
                week_number=4,
                task_description=task_desc,
                estimated_hours=6.0,
                is_completed=False,
            )
        )

    db.add_all(tasks_to_add)
    db.commit()
    db.refresh(plan)

    return serialize_plan(plan)


def get_user_plans(db: Session, *, user_id: int, include_archived: bool = True) -> list[dict]:
    query = (
        select(LearningPlan)
        .options(
            joinedload(LearningPlan.analysis).joinedload(Analysis.career_role),
            joinedload(LearningPlan.items),
        )
        .where(LearningPlan.user_id == user_id)
        .order_by(desc(LearningPlan.created_at))
    )
    if not include_archived:
        query = query.where(LearningPlan.status != "archived")

    plans = db.scalars(query).unique().all()
    return [serialize_plan(p, include_items=False) for p in plans]


def get_plan_detail(db: Session, *, user_id: int, plan_id: int) -> dict:
    plan = db.scalar(
        select(LearningPlan)
        .options(
            joinedload(LearningPlan.analysis).joinedload(Analysis.career_role),
            joinedload(LearningPlan.items).joinedload(LearningPlanItem.skill),
            joinedload(LearningPlan.items).joinedload(LearningPlanItem.resource),
        )
        .where(LearningPlan.id == plan_id)
    )
    if not plan:
        raise _error(status.HTTP_404_NOT_FOUND, PLAN_NOT_FOUND, "Không tìm thấy lộ trình học tập.")
    if plan.user_id != user_id:
        raise _error(status.HTTP_403_FORBIDDEN, PLAN_FORBIDDEN, "Bạn không có quyền truy cập lộ trình này.")

    return serialize_plan(plan, include_items=True)


def update_plan_status(db: Session, *, user_id: int, plan_id: int, new_status: str) -> dict:
    plan = db.scalar(
        select(LearningPlan)
        .options(
            joinedload(LearningPlan.analysis).joinedload(Analysis.career_role),
            joinedload(LearningPlan.items).joinedload(LearningPlanItem.skill),
            joinedload(LearningPlan.items).joinedload(LearningPlanItem.resource),
        )
        .where(LearningPlan.id == plan_id)
    )
    if not plan:
        raise _error(status.HTTP_404_NOT_FOUND, PLAN_NOT_FOUND, "Không tìm thấy lộ trình học tập.")
    if plan.user_id != user_id:
        raise _error(status.HTTP_403_FORBIDDEN, PLAN_FORBIDDEN, "Bạn không có quyền cập nhật lộ trình này.")

    if new_status == "active" and plan.status != "active":
        # Kiểm tra xem có lộ trình active khác cho analysis này không
        other_active = db.scalar(
            select(LearningPlan).where(
                LearningPlan.analysis_id == plan.analysis_id,
                LearningPlan.status == "active",
                LearningPlan.id != plan.id,
            )
        )
        if other_active:
            raise _error(
                status.HTTP_400_BAD_REQUEST,
                ACTIVE_PLAN_EXISTS,
                "Đã có một lộ trình khác đang hoạt động cho báo cáo này.",
            )

    plan.status = new_status
    db.commit()
    db.refresh(plan)
    return serialize_plan(plan, include_items=True)


def update_plan_item(
    db: Session,
    *,
    user_id: int,
    plan_id: int,
    item_id: int,
    is_completed: bool,
) -> dict:
    plan = db.scalar(
        select(LearningPlan).where(LearningPlan.id == plan_id)
    )
    if not plan:
        raise _error(status.HTTP_404_NOT_FOUND, PLAN_NOT_FOUND, "Không tìm thấy lộ trình học tập.")
    if plan.user_id != user_id:
        raise _error(status.HTTP_403_FORBIDDEN, PLAN_FORBIDDEN, "Bạn không có quyền chỉnh sửa lộ trình này.")

    item = db.scalar(
        select(LearningPlanItem)
        .options(
            joinedload(LearningPlanItem.skill),
            joinedload(LearningPlanItem.resource),
        )
        .where(LearningPlanItem.id == item_id, LearningPlanItem.plan_id == plan_id)
    )
    if not item:
        raise _error(status.HTTP_404_NOT_FOUND, ITEM_NOT_FOUND, "Không tìm thấy mục nhiệm vụ trong lộ trình.")

    item.is_completed = is_completed
    item.completed_at = datetime.now(timezone.utc) if is_completed else None
    db.commit()
    db.refresh(item)

    # Tự động kiểm tra nếu tất cả items đều hoàn thành, cập nhật trạng thái plan sang completed
    all_items = db.scalars(
        select(LearningPlanItem).where(LearningPlanItem.plan_id == plan_id)
    ).all()
    if all_items and all(it.is_completed for it in all_items):
        plan.status = "completed"
        db.commit()
    elif plan.status == "completed" and not is_completed:
        # Nếu đang completed mà bỏ tick 1 mục thì quay lại active
        plan.status = "active"
        db.commit()

    return serialize_plan_item(item)
