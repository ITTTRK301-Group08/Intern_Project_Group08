(function () {
  'use strict';

  if (window.__CareerMentorDemoApiLoaded__) return;
  window.__CareerMentorDemoApiLoaded__ = true;

  var DB_KEY = 'career_mentor_ghpages_db_v2';
  var nativeFetch = window.fetch.bind(window);

  function nowIso(offsetDays) {
    var d = new Date(Date.now() + (offsetDays || 0) * 86400000);
    return d.toISOString();
  }

  function todayIso(offsetDays) {
    return nowIso(offsetDays).slice(0, 10);
  }

  function createInitialDb() {
    var categories = [
      { id: 1, name: 'Software Development', slug: 'software-development', description: 'Xây dựng và phát triển các hệ thống phần mềm và ứng dụng web.', created_at: nowIso(-30) },
      { id: 2, name: 'Data and AI', slug: 'data-and-ai', description: 'Phân tích dữ liệu, trực quan hóa và xây dựng hệ thống trí tuệ nhân tạo.', created_at: nowIso(-30) },
      { id: 3, name: 'Cybersecurity', slug: 'cybersecurity', description: 'Bảo vệ hệ thống mạng, hạ tầng và an toàn thông tin.', created_at: nowIso(-30) },
      { id: 4, name: 'Product Design', slug: 'product-design', description: 'Nghiên cứu người dùng và thiết kế trải nghiệm sản phẩm số.', created_at: nowIso(-30) }
    ];

    var skills = [
      { id: 1, name: 'Python', description: 'Ngôn ngữ lập trình cho backend, tự động hóa và khoa học dữ liệu.', is_active: true, created_at: nowIso(-30) },
      { id: 2, name: 'SQL', description: 'Truy vấn và thiết kế cơ sở dữ liệu quan hệ.', is_active: true, created_at: nowIso(-30) },
      { id: 3, name: 'Git', description: 'Quản lý mã nguồn và phối hợp nhóm.', is_active: true, created_at: nowIso(-30) },
      { id: 4, name: 'REST APIs', description: 'Thiết kế và tích hợp dịch vụ HTTP API.', is_active: true, created_at: nowIso(-30) },
      { id: 5, name: 'JavaScript', description: 'Xây dựng giao diện web tương tác.', is_active: true, created_at: nowIso(-30) },
      { id: 6, name: 'HTML and CSS', description: 'Xây dựng cấu trúc và giao diện trang web.', is_active: true, created_at: nowIso(-30) },
      { id: 7, name: 'Data Visualization', description: 'Trực quan hóa và truyền đạt dữ liệu qua biểu đồ.', is_active: true, created_at: nowIso(-30) },
      { id: 8, name: 'Statistics', description: 'Áp dụng thống kê để phân tích dữ liệu.', is_active: true, created_at: nowIso(-30) },
      { id: 9, name: 'Machine Learning', description: 'Huấn luyện và đánh giá các mô hình học máy.', is_active: true, created_at: nowIso(-30) },
      { id: 10, name: 'Linux', description: 'Sử dụng và quản trị hệ điều hành Linux.', is_active: true, created_at: nowIso(-30) },
      { id: 11, name: 'Networking', description: 'Hiểu biết giao thức mạng, định tuyến và hạ tầng.', is_active: true, created_at: nowIso(-30) },
      { id: 12, name: 'Threat Modeling', description: 'Phân tích và đánh giá các mối đe dọa bảo mật.', is_active: true, created_at: nowIso(-30) },
      { id: 13, name: 'UX Research', description: 'Nghiên cứu nhu cầu người dùng có hệ thống.', is_active: true, created_at: nowIso(-30) },
      { id: 14, name: 'Wireframing', description: 'Thiết kế khung giao diện trước khi hoàn thiện chi tiết.', is_active: true, created_at: nowIso(-30) }
    ];

    var roles = [
      {
        id: 1, category_id: 1, name: 'Backend Developer', slug: 'backend-developer', level: 'Junior',
        description: 'Thiết kế và xây dựng hệ thống backend, API và cơ sở dữ liệu.', is_active: true, created_at: nowIso(-30),
        required_skills: [
          { skill_id: 1, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 2, required_level: 3, weight: 1.0, is_required: true },
          { skill_id: 3, required_level: 3, weight: 1.0, is_required: true },
          { skill_id: 4, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 10, required_level: 2, weight: 1.0, is_required: true }
        ]
      },
      {
        id: 2, category_id: 1, name: 'Frontend Developer', slug: 'frontend-developer', level: 'Fresher',
        description: 'Phát triển giao diện web tương tác, tối ưu trải nghiệm người dùng.', is_active: true, created_at: nowIso(-30),
        required_skills: [
          { skill_id: 5, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 6, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 3, required_level: 2, weight: 1.0, is_required: true },
          { skill_id: 4, required_level: 2, weight: 1.0, is_required: true }
        ]
      },
      {
        id: 3, category_id: 2, name: 'Data Analyst', slug: 'data-analyst', level: 'Intern',
        description: 'Thu thập, phân tích dữ liệu và xây dựng báo cáo trực quan.', is_active: true, created_at: nowIso(-30),
        required_skills: [
          { skill_id: 2, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 1, required_level: 3, weight: 1.0, is_required: true },
          { skill_id: 7, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 8, required_level: 3, weight: 1.0, is_required: true }
        ]
      },
      {
        id: 4, category_id: 2, name: 'Machine Learning Engineer', slug: 'machine-learning-engineer', level: 'Junior',
        description: 'Phát triển và vận hành các mô hình học máy thực tế.', is_active: true, created_at: nowIso(-30),
        required_skills: [
          { skill_id: 1, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 2, required_level: 2, weight: 1.0, is_required: true },
          { skill_id: 8, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 9, required_level: 5, weight: 2.0, is_required: true }
        ]
      },
      {
        id: 5, category_id: 3, name: 'Cybersecurity Analyst', slug: 'cybersecurity-analyst', level: 'Fresher',
        description: 'Giám sát hệ thống, phát hiện và giảm thiểu rủi ro an ninh mạng.', is_active: true, created_at: nowIso(-30),
        required_skills: [
          { skill_id: 10, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 11, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 12, required_level: 3, weight: 1.0, is_required: true }
        ]
      },
      {
        id: 6, category_id: 4, name: 'UX/UI Designer', slug: 'ux-ui-designer', level: 'Intern',
        description: 'Nghiên cứu trải nghiệm người dùng và thiết kế sản phẩm số trực quan.', is_active: true, created_at: nowIso(-30),
        required_skills: [
          { skill_id: 13, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 14, required_level: 4, weight: 1.5, is_required: true },
          { skill_id: 6, required_level: 2, weight: 1.0, is_required: true }
        ]
      }
    ];

    var resources = [
      { id: 1, slug: 'python-tutorial', skill_id: 1, title: 'Python Tutorial', provider: 'Python Software Foundation', url: 'https://docs.python.org/3/tutorial/', resource_type: 'documentation', description: 'Tài liệu hướng dẫn Python chính thức.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 2, slug: 'sqlbolt-lessons', skill_id: 2, title: 'Interactive SQL Lessons', provider: 'SQLBolt', url: 'https://sqlbolt.com/', resource_type: 'practice', description: 'Bài tập thực hành truy vấn SQL tương tác.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 3, slug: 'git-documentation', skill_id: 3, title: 'Git Documentation', provider: 'Git', url: 'https://git-scm.com/doc', resource_type: 'documentation', description: 'Tài liệu chuẩn về quản lý phiên bản Git.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 4, slug: 'mdn-javascript-guide', skill_id: 5, title: 'JavaScript Guide', provider: 'MDN', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', resource_type: 'documentation', description: 'Hướng dẫn cốt lõi về ngôn ngữ JavaScript.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 5, slug: 'mdn-html-css', skill_id: 6, title: 'Learn web development', provider: 'MDN', url: 'https://developer.mozilla.org/en-US/docs/Learn', resource_type: 'course', description: 'Khóa học nền tảng về HTML, CSS và lập trình web.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 6, slug: 'kaggle-python', skill_id: 1, title: 'Python Course', provider: 'Kaggle Learn', url: 'https://www.kaggle.com/learn/python', resource_type: 'course', description: 'Khóa thực hành nhanh ngôn ngữ Python.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 7, slug: 'kaggle-data-visualization', skill_id: 7, title: 'Data Visualization Course', provider: 'Kaggle Learn', url: 'https://www.kaggle.com/learn/data-visualization', resource_type: 'course', description: 'Thực hành trực quan hóa dữ liệu bằng biểu đồ.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 8, slug: 'kaggle-statistics', skill_id: 8, title: 'Intro to Statistics', provider: 'Kaggle Learn', url: 'https://www.kaggle.com/learn/intro-to-statistics', resource_type: 'course', description: 'Nhập môn thống kê ứng dụng cho dữ liệu.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 9, slug: 'google-ml-crash-course', skill_id: 9, title: 'Machine Learning Crash Course', provider: 'Google', url: 'https://developers.google.com/machine-learning/crash-course', resource_type: 'course', description: 'Khóa học Machine Learning thực tiễn từ Google.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 10, slug: 'linux-journey', skill_id: 10, title: 'Linux Journey', provider: 'Linux Journey', url: 'https://linuxjourney.com/', resource_type: 'course', description: 'Bài học tương tác làm quen với hệ điều hành Linux.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 11, slug: 'owasp-top-ten', skill_id: 12, title: 'OWASP Top 10', provider: 'OWASP', url: 'https://owasp.org/www-project-top-ten/', resource_type: 'documentation', description: 'Tài liệu chuẩn về 10 rủi ro bảo mật web phổ biến.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 12, slug: 'cloudflare-learning-networking', skill_id: 11, title: 'What is computer networking?', provider: 'Cloudflare', url: 'https://www.cloudflare.com/learning/network-layer/what-is-a-computer-network/', resource_type: 'article', description: 'Bài viết giới thiệu nền tảng mạng máy tính.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 13, slug: 'nng-ux-research', skill_id: 13, title: 'UX Research Cheat Sheet', provider: 'Nielsen Norman Group', url: 'https://www.nngroup.com/articles/ux-research-cheat-sheet/', resource_type: 'article', description: 'Tổng quan các phương pháp nghiên cứu trải nghiệm người dùng.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) },
      { id: 14, slug: 'figma-wireframing', skill_id: 14, title: 'Guide to wireframing', provider: 'Figma', url: 'https://www.figma.com/resource-library/what-is-wireframing/', resource_type: 'article', description: 'Hướng dẫn thiết kế wireframe từ Figma.', language: 'en', is_free: true, is_active: true, approval_status: 'approved', created_at: nowIso(-30) }
    ];

    var users = [
      { id: 1, email: 'admin@careermentor.vn', password: 'AdminPassword123!', role: 'admin', is_active: true, created_at: nowIso(-30), updated_at: nowIso(-1) },
      { id: 2, email: 'student@careermentor.vn', password: 'StudentPass123!', role: 'student', is_active: true, created_at: nowIso(-20), updated_at: nowIso(-1) }
    ];

    var profiles = {
      2: {
        id: 1,
        user_id: 2,
        email: 'student@careermentor.vn',
        full_name: 'Nguyễn Minh Khoa',
        major: 'Kỹ thuật phần mềm',
        university: 'Đại học Bách Khoa TP.HCM',
        strengths: ['Tư duy logic', 'Làm việc nhóm', 'Giải quyết vấn đề'],
        self_assessed_skills: [
          { skill_name: 'Python', level: 4 },
          { skill_name: 'SQL', level: 3 },
          { skill_name: 'Git', level: 3 },
          { skill_name: 'REST APIs', level: 3 },
          { skill_name: 'Linux', level: 1 }
        ],
        career_goal: 'Trở thành Junior Backend Developer chuyên FastAPI & MySQL',
        target_role_id: 1,
        bio: 'Sinh viên năm cuối định hướng phát triển hệ thống backend hiệu năng cao.',
        updated_at: nowIso(-2)
      }
    };

    var cvs = [
      {
        id: 1,
        user_id: 2,
        file_name: 'CV_NguyenMinhKhoa_Backend.pdf',
        file_size: 245760,
        extracted_text: 'Nguyễn Minh Khoa - Kỹ thuật phần mềm. Kinh nghiệm: Xây dựng REST API với Python FastAPI, thiết kế cơ sở dữ liệu SQL MySQL, quản lý mã nguồn với Git, làm quen Linux server cơ bản.',
        has_text: true,
        is_active: true,
        analysis_count: 2,
        created_at: nowIso(-14)
      }
    ];

    var analyses = [
      {
        id: 1,
        user_id: 2,
        cv_id: 1,
        career_role_id: 1,
        source_type: 'cv',
        status: 'completed',
        readiness_score: 68,
        summary: 'Điểm sẵn sàng nghề nghiệp: 68/100. Kỹ năng cần cải thiện: REST APIs, Linux.',
        created_at: nowIso(-12),
        completed_at: nowIso(-12),
        skills: [
          { skill_id: 1, skill_name: 'Python', current_level: 3, required_level: 4, gap_score: 1, has_evidence: true, evidence: 'Xây dựng REST API với Python FastAPI', recommendation: 'Luyện tập thêm async Python và tối ưu hiệu năng.' },
          { skill_id: 2, skill_name: 'SQL', current_level: 2, required_level: 3, gap_score: 1, has_evidence: true, evidence: 'Thiết kế cơ sở dữ liệu SQL MySQL', recommendation: 'Thực hành indexing và tối ưu câu truy vấn phức tạp.' },
          { skill_id: 3, skill_name: 'Git', current_level: 3, required_level: 3, gap_score: 0, has_evidence: true, evidence: 'Quản lý mã nguồn với Git', recommendation: 'Đã đạt mức yêu cầu.' },
          { skill_id: 4, skill_name: 'REST APIs', current_level: 2, required_level: 4, gap_score: 2, has_evidence: true, evidence: 'Xây dựng REST API với Python FastAPI', recommendation: 'Bổ sung kiến thức về phân trang, rate limiting và bảo mật JWT.' },
          { skill_id: 10, skill_name: 'Linux', current_level: 1, required_level: 2, gap_score: 1, has_evidence: true, evidence: 'Làm quen Linux server cơ bản', recommendation: 'Học thêm lệnh shell, quản lý tiến trình và Docker.' }
        ]
      },
      {
        id: 2,
        user_id: 2,
        cv_id: 1,
        career_role_id: 1,
        source_type: 'cv',
        status: 'completed',
        readiness_score: 83,
        summary: 'Điểm sẵn sàng nghề nghiệp: 83/100. Kỹ năng cần cải thiện: REST APIs, Linux.',
        created_at: nowIso(-3),
        completed_at: nowIso(-3),
        skills: [
          { skill_id: 1, skill_name: 'Python', current_level: 4, required_level: 4, gap_score: 0, has_evidence: true, evidence: 'Xây dựng REST API với Python FastAPI', recommendation: 'Đã đạt chuẩn vị trí mục tiêu.' },
          { skill_id: 2, skill_name: 'SQL', current_level: 3, required_level: 3, gap_score: 0, has_evidence: true, evidence: 'Thiết kế cơ sở dữ liệu SQL MySQL', recommendation: 'Đã đạt chuẩn vị trí mục tiêu.' },
          { skill_id: 3, skill_name: 'Git', current_level: 3, required_level: 3, gap_score: 0, has_evidence: true, evidence: 'Quản lý mã nguồn với Git', recommendation: 'Đã đạt chuẩn vị trí mục tiêu.' },
          { skill_id: 4, skill_name: 'REST APIs', current_level: 3, required_level: 4, gap_score: 1, has_evidence: true, evidence: 'Xây dựng REST API với Python FastAPI', recommendation: 'Hoàn thiện chuẩn hóa error handling và OpenAPI docs.' },
          { skill_id: 10, skill_name: 'Linux', current_level: 1, required_level: 2, gap_score: 1, has_evidence: true, evidence: 'Làm quen Linux server cơ bản', recommendation: 'Thực hành cấu hình Nginx reverse proxy và systemd.' }
        ]
      }
    ];

    var learningPlans = [
      {
        id: 1,
        user_id: 2,
        analysis_id: 2,
        title: 'Lộ trình 30 ngày chinh phục Backend Developer',
        status: 'active',
        start_date: todayIso(-7),
        end_date: todayIso(23),
        created_at: nowIso(-7),
        items: [
          { id: 1, plan_id: 1, skill_id: 4, resource_id: 1, week_number: 1, task_description: 'Thiết kế RESTful API chuẩn hóa status code, phân trang và Pydantic schema', estimated_hours: 4, is_completed: true, completed_at: nowIso(-6) },
          { id: 2, plan_id: 1, skill_id: 2, resource_id: 2, week_number: 1, task_description: 'Ôn tập SQL JOIN, Subquery và giải 10 bài tập trên SQLBolt', estimated_hours: 3, is_completed: true, completed_at: nowIso(-5) },
          { id: 3, plan_id: 1, skill_id: 10, resource_id: 10, week_number: 2, task_description: 'Hoàn thành bài học phân quyền file, shell script và process trên Linux Journey', estimated_hours: 4, is_completed: true, completed_at: nowIso(-3) },
          { id: 4, plan_id: 1, skill_id: 4, resource_id: 1, week_number: 2, task_description: 'Triển khai xác thực JWT + Refresh Token xoay vòng an toàn', estimated_hours: 5, is_completed: false, completed_at: null },
          { id: 5, plan_id: 1, skill_id: 1, resource_id: 6, week_number: 3, task_description: 'Xây dựng xử lý bất đồng bộ (async/await) và unit test với pytest', estimated_hours: 4, is_completed: false, completed_at: null },
          { id: 6, plan_id: 1, skill_id: 3, resource_id: 3, week_number: 3, task_description: 'Thực hành quy trình Git Flow, xử lý conflict và review Pull Request', estimated_hours: 2, is_completed: false, completed_at: null },
          { id: 7, plan_id: 1, skill_id: 10, resource_id: 10, week_number: 4, task_description: 'Đóng gói dự án FastAPI + MySQL bằng Docker Compose và cấu hình HTTPS', estimated_hours: 5, is_completed: false, completed_at: null },
          { id: 8, plan_id: 1, skill_id: 4, resource_id: 1, week_number: 4, task_description: 'Tổng hợp dự án cá nhân và chuẩn bị trả lời phỏng vấn hệ thống', estimated_hours: 4, is_completed: false, completed_at: null }
        ]
      }
    ];

    var interviews = [
      {
        id: 1,
        user_id: 2,
        career_role_id: 1,
        status: 'completed',
        total_score: 82.5,
        created_at: nowIso(-4),
        updated_at: nowIso(-4),
        completed_at: nowIso(-4),
        questions: [
          {
            id: 1, session_id: 1, question_order: 1,
            question_text: 'Hãy giải thích sự khác biệt giữa xác thực Stateful (Session/Cookie) và Stateless (JWT) trong REST API?',
            competency: 'REST APIs & Bảo mật',
            evaluation_criteria: ['Hiểu cơ chế lưu trạng thái', 'Ưu nhược điểm khi scale', 'Cách thu hồi token'],
            answer: { id: 1, question_id: 1, answer_text: 'Stateful lưu session trên server hoặc Redis còn JWT tự chứa thông tin được ký bằng secret key. Kết hợp thêm Refresh Token lưu DB để thu hồi khi logout.', score: 85.0, feedback: 'Giải thích rõ ràng, có đề cập cơ chế kết hợp Refresh Token để khắc phục điểm yếu thu hồi JWT.', created_at: nowIso(-4) }
          },
          {
            id: 2, session_id: 1, question_order: 2,
            question_text: 'Làm thế nào để tối ưu một câu truy vấn SQL chạy chậm trên bảng hàng triệu dòng?',
            competency: 'SQL & Cơ sở dữ liệu',
            evaluation_criteria: ['Sử dụng EXPLAIN', 'Đánh Index hợp lý', 'Tránh N+1 query'],
            answer: { id: 2, question_id: 2, answer_text: 'Dùng EXPLAIN kiểm tra execution plan, tạo index cho cột trong WHERE và JOIN, phân trang và tránh SELECT *.', score: 82.5, feedback: 'Đúng trọng tâm kỹ thuật tối ưu hóa truy vấn thực tế.', created_at: nowIso(-4) }
          },
          {
            id: 3, session_id: 1, question_order: 3,
            question_text: 'Trong Python/FastAPI, khi nào nên dùng async def và khi nào dùng def thông thường?',
            competency: 'Python Backend',
            evaluation_criteria: ['Event loop', 'I/O-bound vs CPU-bound', 'Blocking call'],
            answer: { id: 3, question_id: 3, answer_text: 'Dùng async def cho tác vụ I/O-bound (gọi API ngoài, DB async), dùng def cho tác vụ sync/blocking để FastAPI đẩy vào threadpool.', score: 80.0, feedback: 'Phân biệt chính xác tác vụ I/O-bound và blocking trong FastAPI.', created_at: nowIso(-4) }
          }
        ]
      }
    ];

    return {
      users: users,
      categories: categories,
      skills: skills,
      roles: roles,
      resources: resources,
      profiles: profiles,
      cvs: cvs,
      analyses: analyses,
      learningPlans: learningPlans,
      interviews: interviews,
      sessions: {
        'demo_access_1': 1,
        'demo_access_2': 2
      },
      refreshTokens: {
        'demo_refresh_1': 1,
        'demo_refresh_2': 2
      },
      nextIds: { user: 3, cat: 5, skill: 15, role: 7, resource: 15, cv: 2, analysis: 3, plan: 2, planItem: 9, interview: 2, question: 4, answer: 4 }
    };
  }

  function loadDb() {
    try {
      var raw = localStorage.getItem(DB_KEY);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    var db = createInitialDb();
    saveDb(db);
    return db;
  }

  function saveDb(db) {
    try {
      localStorage.setItem(DB_KEY, JSON.stringify(db));
    } catch (_) {}
  }

  function jsonRes(status, body) {
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        status: status,
        headers: { 'Content-Type': 'application/json' }
      })
    );
  }

  function errRes(status, detail) {
    return jsonRes(status, { detail: detail });
  }

  function codeErrRes(status, code, message) {
    return jsonRes(status, { detail: { success: false, data: { code: code }, message: message } });
  }

  function paginate(list, page, pageSize) {
    var total = list.length;
    var p = Math.max(1, Number(page) || 1);
    var ps = Math.max(1, Number(pageSize) || 10);
    var totalPages = Math.max(1, Math.ceil(total / ps));
    var items = list.slice((p - 1) * ps, p * ps);
    return { items: items, total: total, page: p, page_size: ps, total_pages: totalPages, pages: totalPages };
  }

  function enrichRole(db, role) {
    var cat = db.categories.find(function (c) { return c.id === role.category_id; }) || null;
    var reqSkills = (role.required_skills || []).map(function (rs) {
      var sk = db.skills.find(function (s) { return s.id === rs.skill_id; });
      return {
        skill_id: rs.skill_id,
        skill_name: sk ? sk.name : ('Skill #' + rs.skill_id),
        required_level: rs.required_level,
        weight: rs.weight || 1.0,
        is_required: rs.is_required !== false,
        skill: sk || null
      };
    });
    return Object.assign({}, role, {
      category: cat,
      category_name: cat ? cat.name : null,
      required_skills: reqSkills
    });
  }

  function enrichResource(db, res) {
    var sk = db.skills.find(function (s) { return s.id === res.skill_id; }) || null;
    var relatedRoles = db.roles
      .filter(function (r) {
        return r.is_active && (r.required_skills || []).some(function (rs) { return rs.skill_id === res.skill_id; });
      })
      .map(function (r) { return { id: r.id, name: r.name, level: r.level }; });
    return Object.assign({}, res, {
      skill: sk ? { id: sk.id, name: sk.name } : null,
      skill_name: sk ? sk.name : null,
      related_roles: relatedRoles
    });
  }

  function enrichPlan(db, plan) {
    var analysis = db.analyses.find(function (a) { return a.id === plan.analysis_id; }) || null;
    var role = analysis ? db.roles.find(function (r) { return r.id === analysis.career_role_id; }) : null;
    var items = (plan.items || []).map(function (it) {
      var sk = db.skills.find(function (s) { return s.id === it.skill_id; }) || null;
      var res = db.resources.find(function (r) { return r.id === it.resource_id; }) || null;
      return Object.assign({}, it, {
        skill_name: sk ? sk.name : ('Skill #' + it.skill_id),
        resource_title: res ? res.title : null,
        resource_url: res ? res.url : null,
        resource_provider: res ? res.provider : null,
        resource_type: res ? res.resource_type : null
      });
    });
    return Object.assign({}, plan, {
      career_role_name: role ? role.name : null,
      items: items
    });
  }

  function calcReadiness(items) {
    if (!items || !items.length) return 0;
    var tw = 0;
    var ws = 0;
    items.forEach(function (it) {
      var cur = Math.max(0, it.current_level || 0);
      var req = Math.max(1, it.required_level || 1);
      var w = Math.max(0.1, it.weight || 1.0);
      ws += w * Math.min(cur / req, 1.0);
      tw += w;
    });
    return tw > 0 ? Math.round((ws / tw) * 1000) / 10 : 0;
  }

  function getAuthUser(db, headers) {
    var auth = '';
    if (headers && typeof headers.get === 'function') auth = headers.get('Authorization') || '';
    else if (headers && headers.Authorization) auth = headers.Authorization;
    if (auth.indexOf('Bearer ') !== 0) return null;
    var token = auth.slice(7).trim();
    var userId = db.sessions[token];
    if (!userId) return null;
    return db.users.find(function (u) { return u.id === userId; }) || null;
  }

  async function readRequestContext(input, init) {
    var isReq = typeof Request !== 'undefined' && input instanceof Request;
    var reqUrl = typeof input === 'string' ? input : (input && input.url) || '';
    var method = ((init && init.method) || (isReq && input.method) || 'GET').toUpperCase();
    var headers = new Headers((init && init.headers) || (isReq && input.headers) || {});
    var body = {};

    if (init && init.body) {
      if (typeof FormData !== 'undefined' && init.body instanceof FormData) {
        body = init.body;
      } else if (typeof init.body === 'string') {
        try { body = JSON.parse(init.body); } catch (_) { body = {}; }
      }
    } else if (isReq && method !== 'GET' && method !== 'HEAD') {
      var ct = (headers.get('content-type') || '').toLowerCase();
      if (ct.indexOf('multipart/form-data') !== -1 && typeof input.formData === 'function') {
        try { body = await input.formData(); } catch (_) { body = {}; }
      } else if (typeof input.text === 'function') {
        try {
          var rawText = await input.text();
          body = rawText ? JSON.parse(rawText) : {};
        } catch (_) {
          body = {};
        }
      }
    }

    return { reqUrl: reqUrl, method: method, headers: headers, body: body };
  }

  async function handleApi(input, init) {
    var ctx = await readRequestContext(input, init);
    var url = new URL(ctx.reqUrl, window.location.href);
    var path = url.pathname;
    var method = ctx.method;
    var db = loadDb();
    var body = ctx.body;
    var headers = ctx.headers;
    var currentUser = getAuthUser(db, headers);

    function requireAuthUser() {
      if (!currentUser) return errRes(401, 'Could not validate credentials');
      if (!currentUser.is_active) return errRes(403, 'Account is inactive');
      return null;
    }

    function requireAdminUser() {
      var authErr = requireAuthUser();
      if (authErr) return authErr;
      if (currentUser.role !== 'admin') return errRes(403, 'Administrator access required');
      return null;
    }

    // ── AUTH ─────────────────────────────────────────────────
    if (path === '/api/v1/auth/register' && method === 'POST') {
      var email = String(body.email || '').trim().toLowerCase();
      var password = String(body.password || '');
      if (!email || password.length < 8) return errRes(422, 'Dữ liệu đăng ký không hợp lệ.');
      if (db.users.some(function (u) { return u.email === email; })) {
        return errRes(400, 'Email already registered');
      }
      var newUser = {
        id: db.nextIds.user++,
        email: email,
        password: password,
        role: 'student',
        is_active: true,
        created_at: nowIso(0),
        updated_at: nowIso(0)
      };
      db.users.push(newUser);
      saveDb(db);
      return jsonRes(201, {
        success: true,
        data: { user: { id: newUser.id, email: newUser.email, role: newUser.role, is_active: true, created_at: newUser.created_at } },
        message: 'Registration successful'
      });
    }

    if (path === '/api/v1/auth/login' && method === 'POST') {
      var loginEmail = String(body.email || '').trim().toLowerCase();
      var loginPwd = String(body.password || '');
      var u = db.users.find(function (x) { return x.email === loginEmail; });
      if (!u || u.password !== loginPwd) return errRes(401, 'Incorrect email or password');
      if (!u.is_active) return errRes(403, 'Account is inactive');
      var at = 'demo_access_' + u.id + '_' + Date.now();
      var rt = 'demo_refresh_' + u.id + '_' + Date.now();
      db.sessions[at] = u.id;
      db.refreshTokens[rt] = u.id;
      saveDb(db);
      return jsonRes(200, {
        success: true,
        data: { access_token: at, refresh_token: rt, token_type: 'bearer' },
        message: 'Login successful'
      });
    }

    if (path === '/api/v1/auth/refresh' && method === 'POST') {
      var reqRt = body.refresh_token || '';
      var uid = db.refreshTokens[reqRt];
      if (!uid) return errRes(401, 'Refresh token is invalid or expired');
      var rUser = db.users.find(function (x) { return x.id === uid; });
      if (!rUser || !rUser.is_active) return errRes(401, 'Refresh token is invalid or expired');
      delete db.refreshTokens[reqRt];
      var newAt = 'demo_access_' + uid + '_' + Date.now();
      var newRt = 'demo_refresh_' + uid + '_' + Date.now();
      db.sessions[newAt] = uid;
      db.refreshTokens[newRt] = uid;
      saveDb(db);
      return jsonRes(200, {
        success: true,
        data: { access_token: newAt, refresh_token: newRt, token_type: 'bearer' },
        message: 'Token refreshed'
      });
    }

    if (path === '/api/v1/auth/logout' && method === 'POST') {
      if (body.refresh_token) delete db.refreshTokens[body.refresh_token];
      saveDb(db);
      return jsonRes(200, { success: true, data: { revoked: true }, message: 'Logged out' });
    }

    if (path === '/api/v1/auth/me' && method === 'GET') {
      var meErr = requireAuthUser();
      if (meErr) return meErr;
      return jsonRes(200, {
        success: true,
        data: { id: currentUser.id, email: currentUser.email, role: currentUser.role, is_active: currentUser.is_active },
        message: 'Authenticated user retrieved'
      });
    }

    // ── PUBLIC CATALOG & CAREERS ──────────────────────────────
    if (path === '/api/v1/catalog/categories' && method === 'GET') {
      return jsonRes(200, { success: true, data: db.categories, message: 'Categories retrieved' });
    }
    if ((path === '/api/v1/catalog/roles' || path === '/api/v1/careers') && method === 'GET') {
      var activeRoles = db.roles.filter(function (r) { return r.is_active; }).map(function (r) { return enrichRole(db, r); });
      return jsonRes(200, { success: true, data: activeRoles, message: 'Roles retrieved' });
    }
    var careerMatch = path.match(/^\/api\/v1\/(?:catalog\/roles|careers)\/(\d+)(\/skills)?$/);
    if (careerMatch && method === 'GET') {
      var rId = Number(careerMatch[1]);
      var foundRole = db.roles.find(function (r) { return r.id === rId; });
      if (!foundRole) return errRes(404, 'Career role not found');
      var enriched = enrichRole(db, foundRole);
      return jsonRes(200, { success: true, data: careerMatch[2] ? enriched.required_skills : enriched, message: 'Role retrieved' });
    }
    if (path === '/api/v1/catalog/skills' && method === 'GET') {
      return jsonRes(200, { success: true, data: db.skills.filter(function (s) { return s.is_active; }), message: 'Skills retrieved' });
    }
    if (path === '/api/v1/catalog/resources' && method === 'GET') {
      var approvedRes = db.resources
        .filter(function (r) { return r.is_active && r.approval_status === 'approved'; })
        .map(function (r) { return enrichResource(db, r); });
      return jsonRes(200, { success: true, data: approvedRes, message: 'Resources retrieved' });
    }

    // ── PROFILE ──────────────────────────────────────────────
    if (path === '/api/v1/profile/me') {
      var pErr = requireAuthUser();
      if (pErr) return pErr;
      if (method === 'GET') {
        var prof = db.profiles[currentUser.id];
        if (!prof) return errRes(404, 'Profile not found');
        return jsonRes(200, { success: true, data: Object.assign({}, prof, { email: currentUser.email }), message: 'Lay ho so thanh cong' });
      }
      if (method === 'PUT') {
        var existingP = db.profiles[currentUser.id] || { id: Object.keys(db.profiles).length + 1, user_id: currentUser.id };
        var updatedP = Object.assign({}, existingP, {
          email: currentUser.email,
          full_name: body.full_name,
          major: body.major || null,
          university: body.university || null,
          strengths: body.strengths || [],
          self_assessed_skills: body.self_assessed_skills || [],
          career_goal: body.career_goal || null,
          target_role_id: body.target_role_id || null,
          bio: body.bio || null,
          updated_at: nowIso(0)
        });
        db.profiles[currentUser.id] = updatedP;
        saveDb(db);
        return jsonRes(200, { success: true, data: updatedP, message: 'Cap nhat ho so thanh cong' });
      }
    }

    // ── CVs ──────────────────────────────────────────────────
    if (path === '/api/v1/cvs' && method === 'GET') {
      var cErr = requireAuthUser();
      if (cErr) return cErr;
      var incInactive = url.searchParams.get('include_inactive') === 'true';
      var userCvs = db.cvs.filter(function (c) {
        return c.user_id === currentUser.id && (incInactive || c.is_active);
      });
      return jsonRes(200, { success: true, data: { cvs: userCvs }, message: 'Lay danh sach CV thanh cong' });
    }

    if (path === '/api/v1/cvs' && method === 'POST') {
      var cuErr = requireAuthUser();
      if (cuErr) return cuErr;
      var file = body instanceof FormData ? body.get('file') : null;
      var fname = (file && file.name) || 'Uploaded_CV.pdf';
      var fsize = (file && file.size) || 102400;
      if (!fname.toLowerCase().endsWith('.pdf')) return errRes(422, 'Chỉ hỗ trợ tệp định dạng PDF (.pdf).');
      var sampleExtract = 'Hồ sơ ứng viên từ ' + fname + '. Kỹ năng: Python, SQL, Git, REST APIs, JavaScript, HTML and CSS. Đã thực hiện các dự án phần mềm thực tế.';
      var newCv = {
        id: db.nextIds.cv++,
        user_id: currentUser.id,
        file_name: fname,
        file_size: fsize,
        extracted_text: sampleExtract,
        has_text: true,
        is_active: true,
        analysis_count: 0,
        created_at: nowIso(0)
      };
      db.cvs.unshift(newCv);
      saveDb(db);
      return jsonRes(201, { success: true, data: { cv: newCv, has_text: true, warning: null }, message: 'Upload CV thanh cong' });
    }

    var cvItemMatch = path.match(/^\/api\/v1\/cvs\/(\d+)$/);
    if (cvItemMatch) {
      var ciErr = requireAuthUser();
      if (ciErr) return ciErr;
      var cvId = Number(cvItemMatch[1]);
      var cvObj = db.cvs.find(function (c) { return c.id === cvId && c.user_id === currentUser.id; });
      if (!cvObj) return errRes(404, 'CV not found');
      if (method === 'GET') {
        return jsonRes(200, { success: true, data: { cv: cvObj, warning: null }, message: 'Lay chi tiet CV thanh cong' });
      }
      if (method === 'DELETE') {
        var used = db.analyses.some(function (a) { return a.cv_id === cvId; });
        if (used) {
          cvObj.is_active = false;
          saveDb(db);
          return jsonRes(200, {
            success: true,
            data: { cv_id: cvId, deleted: true, soft_deleted: true },
            message: 'CV da gan voi bao cao phan tich lich su nen da duoc xoa mem (an trang thai hoat dong).'
          });
        }
        db.cvs = db.cvs.filter(function (c) { return c.id !== cvId; });
        saveDb(db);
        return jsonRes(200, { success: true, data: { cv_id: cvId, deleted: true, soft_deleted: false }, message: 'Da xoa CV thanh cong.' });
      }
    }

    // ── ANALYSES ─────────────────────────────────────────────
    if (path === '/api/v1/analyses' && method === 'POST') {
      var aErr = requireAuthUser();
      if (aErr) return aErr;
      if (!body.ai_consent || body.ai_consent.accepted !== true) {
        return codeErrRes(403, 'AI_CONSENT_REQUIRED', 'Nguoi dung chua dong y cho phep su dung du lieu cho AI.');
      }
      var targetRole = db.roles.find(function (r) { return r.id === Number(body.career_role_id); }) || db.roles[0];
      var profData = db.profiles[currentUser.id];
      var chosenCv = body.cv_id ? db.cvs.find(function (c) { return c.id === Number(body.cv_id) && c.user_id === currentUser.id; }) : null;
      var sourceText = chosenCv ? chosenCv.extracted_text : (profData ? (profData.bio || profData.career_goal || profData.full_name) : 'Hồ sơ sinh viên');
      var selfLevels = {};
      if (profData && Array.isArray(profData.self_assessed_skills)) {
        profData.self_assessed_skills.forEach(function (s) { selfLevels[String(s.skill_name || '').toLowerCase()] = Number(s.level || 0); });
      }

      var enrichedTgt = enrichRole(db, targetRole);
      var skillGaps = enrichedTgt.required_skills.map(function (rs) {
        var nameLower = rs.skill_name.toLowerCase();
        var base = selfLevels[nameLower] !== undefined ? selfLevels[nameLower] : (chosenCv && sourceText.toLowerCase().indexOf(nameLower) !== -1 ? Math.max(2, rs.required_level - 1) : 1);
        var cur = Math.min(5, Math.max(0, base));
        var req = rs.required_level;
        return {
          skill_id: rs.skill_id,
          skill_name: rs.skill_name,
          current_level: cur,
          required_level: req,
          weight: rs.weight,
          gap_score: Math.max(0, req - cur),
          has_evidence: cur > 0,
          evidence: cur > 0 ? ('Ghi nhận từ ' + (chosenCv ? chosenCv.file_name : 'Hồ sơ cá nhân') + ': ' + rs.skill_name) : null,
          recommendation: cur >= req ? 'Đã đạt mức yêu cầu.' : ('Cần luyện tập thêm ' + rs.skill_name + ' qua dự án thực hành.')
        };
      });

      var score = Math.round(calcReadiness(skillGaps));
      var gapsNames = skillGaps.filter(function (s) { return s.gap_score > 0; }).map(function (s) { return s.skill_name; });
      var newAnalysis = {
        id: db.nextIds.analysis++,
        user_id: currentUser.id,
        cv_id: chosenCv ? chosenCv.id : null,
        career_role_id: targetRole.id,
        source_type: chosenCv ? 'cv' : 'profile',
        status: 'completed',
        readiness_score: score,
        summary: 'Điểm sẵn sàng nghề nghiệp: ' + score + '/100. ' + (gapsNames.length ? 'Kỹ năng cần cải thiện: ' + gapsNames.join(', ') + '.' : 'Các kỹ năng đã đạt chuẩn.'),
        created_at: nowIso(0),
        completed_at: nowIso(0),
        skills: skillGaps
      };
      if (chosenCv) chosenCv.analysis_count = (chosenCv.analysis_count || 0) + 1;
      db.analyses.push(newAnalysis);
      saveDb(db);
      return jsonRes(202, {
        success: true,
        data: { id: newAnalysis.id, status: 'completed', created_at: newAnalysis.created_at },
        message: 'Yêu cầu phân tích đã được tiếp nhận'
      });
    }

    if (path === '/api/v1/analyses' && method === 'GET') {
      var alErr = requireAuthUser();
      if (alErr) return alErr;
      var list = db.analyses
        .filter(function (a) { return a.user_id === currentUser.id; })
        .sort(function (a, b) { return b.id - a.id; })
        .map(function (a) {
          var r = db.roles.find(function (x) { return x.id === a.career_role_id; });
          return Object.assign({}, a, { career_role_name: r ? r.name : 'Vị trí mục tiêu' });
        });
      return jsonRes(200, {
        success: true,
        data: paginate(list, url.searchParams.get('page'), url.searchParams.get('page_size')),
        message: 'Analysis history retrieved'
      });
    }

    var anMatch = path.match(/^\/api\/v1\/analyses\/(\d+)(\/status|\/skills)?$/);
    if (anMatch && method === 'GET') {
      var adErr = requireAuthUser();
      if (adErr) return adErr;
      var aid = Number(anMatch[1]);
      var foundA = db.analyses.find(function (a) { return a.id === aid && a.user_id === currentUser.id; });
      if (!foundA) return errRes(404, 'Khong tim thay bao cao phan tich.');
      if (anMatch[2] === '/status') {
        return jsonRes(200, { success: true, data: { id: foundA.id, status: foundA.status }, message: 'Status retrieved' });
      }
      if (anMatch[2] === '/skills') {
        return jsonRes(200, { success: true, data: foundA.skills || [], message: 'Skills retrieved' });
      }
      var aRole = db.roles.find(function (x) { return x.id === foundA.career_role_id; });
      return jsonRes(200, {
        success: true,
        data: Object.assign({}, foundA, { career_role_name: aRole ? aRole.name : 'Vị trí mục tiêu' }),
        message: 'Analysis report retrieved'
      });
    }

    // ── LEARNING PLANS ───────────────────────────────────────
    if (path === '/api/v1/learning-plans' && method === 'GET') {
      var lpErr = requireAuthUser();
      if (lpErr) return lpErr;
      var incArch = url.searchParams.get('include_archived') !== 'false';
      var plans = db.learningPlans.filter(function (p) {
        return p.user_id === currentUser.id && (incArch || p.status !== 'archived');
      }).map(function (p) { return enrichPlan(db, p); });
      return jsonRes(200, { success: true, data: plans, message: 'Plans retrieved' });
    }

    if (path === '/api/v1/learning-plans' && method === 'POST') {
      var lpcErr = requireAuthUser();
      if (lpcErr) return lpcErr;
      var srcAn = db.analyses.find(function (a) { return a.id === Number(body.analysis_id) && a.user_id === currentUser.id; });
      if (!srcAn) return errRes(404, 'Khong tim thay bao cao phan tich.');
      db.learningPlans.forEach(function (p) { if (p.user_id === currentUser.id && p.status === 'active') p.status = 'archived'; });
      var rObj = db.roles.find(function (r) { return r.id === srcAn.career_role_id; });
      var newPlanId = db.nextIds.plan++;
      var newItems = (srcAn.skills || []).slice(0, 4).map(function (sk, idx) {
        var res = db.resources.find(function (r) { return r.skill_id === sk.skill_id && r.approval_status === 'approved'; }) || db.resources[0];
        return {
          id: db.nextIds.planItem++,
          plan_id: newPlanId,
          skill_id: sk.skill_id,
          resource_id: res ? res.id : null,
          week_number: idx + 1,
          task_description: 'Hoàn thiện kỹ năng ' + sk.skill_name + ': ' + (sk.recommendation || 'Thực hành bài tập trọng tâm'),
          estimated_hours: 4,
          is_completed: false,
          completed_at: null
        };
      });
      var createdPlan = {
        id: newPlanId,
        user_id: currentUser.id,
        analysis_id: srcAn.id,
        title: 'Lộ trình 30 ngày cho ' + (rObj ? rObj.name : 'Mục tiêu mới'),
        status: 'active',
        start_date: todayIso(0),
        end_date: todayIso(29),
        created_at: nowIso(0),
        items: newItems
      };
      db.learningPlans.push(createdPlan);
      saveDb(db);
      return jsonRes(201, { success: true, data: enrichPlan(db, createdPlan), message: 'Tạo lộ trình học tập cá nhân hóa 30 ngày thành công' });
    }

    var lpDetailMatch = path.match(/^\/api\/v1\/learning-plans\/(\d+)$/);
    if (lpDetailMatch && method === 'GET') {
      var lpdErr = requireAuthUser();
      if (lpdErr) return lpdErr;
      var pid = Number(lpDetailMatch[1]);
      var foundP = db.learningPlans.find(function (p) { return p.id === pid && p.user_id === currentUser.id; });
      if (!foundP) return errRes(404, 'Plan not found');
      return jsonRes(200, { success: true, data: enrichPlan(db, foundP), message: 'Plan detail retrieved' });
    }

    var lpStatusMatch = path.match(/^\/api\/v1\/learning-plans\/(\d+)\/status$/);
    if (lpStatusMatch && method === 'PATCH') {
      var lpsErr = requireAuthUser();
      if (lpsErr) return lpsErr;
      var spid = Number(lpStatusMatch[1]);
      var sPlan = db.learningPlans.find(function (p) { return p.id === spid && p.user_id === currentUser.id; });
      if (!sPlan) return errRes(404, 'Plan not found');
      sPlan.status = body.status || 'archived';
      saveDb(db);
      return jsonRes(200, { success: true, data: enrichPlan(db, sPlan), message: 'Plan status updated' });
    }

    var lpItemMatch = path.match(/^\/api\/v1\/learning-plans\/(\d+)\/items\/(\d+)$/);
    if (lpItemMatch && method === 'PATCH') {
      var lpiErr = requireAuthUser();
      if (lpiErr) return lpiErr;
      var ipid = Number(lpItemMatch[1]);
      var itemId = Number(lpItemMatch[2]);
      var iPlan = db.learningPlans.find(function (p) { return p.id === ipid && p.user_id === currentUser.id; });
      if (!iPlan) return errRes(404, 'Plan not found');
      var item = (iPlan.items || []).find(function (it) { return it.id === itemId; });
      if (!item) return errRes(404, 'Plan item not found');
      item.is_completed = Boolean(body.is_completed);
      item.completed_at = item.is_completed ? nowIso(0) : null;
      saveDb(db);
      var enrichedItem = enrichPlan(db, iPlan).items.find(function (it) { return it.id === itemId; });
      return jsonRes(200, { success: true, data: enrichedItem, message: 'Cập nhật trạng thái nhiệm vụ học tập thành công' });
    }

    // ── INTERVIEWS ───────────────────────────────────────────
    if (path === '/api/v1/interviews' && method === 'POST') {
      var ivErr = requireAuthUser();
      if (ivErr) return ivErr;
      if (!body.ai_consent || body.ai_consent.accepted !== true) {
        return codeErrRes(403, 'AI_CONSENT_REQUIRED', 'Bạn cần đồng ý điều khoản AI trước khi bắt đầu.');
      }
      var ivRole = db.roles.find(function (r) { return r.id === Number(body.career_role_id); }) || db.roles[0];
      db.interviews.forEach(function (s) {
        if (s.user_id === currentUser.id && (s.status === 'ready' || s.status === 'in_progress')) {
          s.status = 'abandoned';
        }
      });
      var newSid = db.nextIds.interview++;
      var rSkills = enrichRole(db, ivRole).required_skills;
      var qs = [0, 1, 2].map(function (idx) {
        var sk = rSkills[idx % Math.max(1, rSkills.length)];
        var skName = sk ? sk.skill_name : ivRole.name;
        return {
          id: db.nextIds.question++,
          session_id: newSid,
          question_order: idx + 1,
          question_text: 'Câu ' + (idx + 1) + ' (' + ivRole.name + '): Trình bày kinh nghiệm và cách bạn xử lý tình huống thực tế liên quan đến ' + skName + '?',
          competency: skName,
          evaluation_criteria: ['Đúng trọng tâm kỹ thuật', 'Ví dụ thực tế rõ ràng', 'Tư duy xử lý vấn đề'],
          answer: null
        };
      });
      var newSession = {
        id: newSid,
        user_id: currentUser.id,
        career_role_id: ivRole.id,
        status: 'ready',
        total_score: null,
        created_at: nowIso(0),
        updated_at: nowIso(0),
        completed_at: null,
        questions: qs
      };
      db.interviews.unshift(newSession);
      saveDb(db);
      return jsonRes(201, {
        success: true,
        data: Object.assign({}, newSession, { career_role: { id: ivRole.id, name: ivRole.name, level: ivRole.level } }),
        message: 'Tạo phiên phỏng vấn thành công'
      });
    }

    if (path === '/api/v1/interviews' && method === 'GET') {
      var ivlErr = requireAuthUser();
      if (ivlErr) return ivlErr;
      var mySessions = db.interviews.filter(function (s) { return s.user_id === currentUser.id; }).map(function (s) {
        var r = db.roles.find(function (x) { return x.id === s.career_role_id; });
        return Object.assign({}, s, {
          career_role: r ? { id: r.id, name: r.name, level: r.level } : null,
          career_role_name: r ? r.name : 'Chưa xác định',
          question_count: (s.questions || []).length,
          answered_count: (s.questions || []).filter(function (q) { return q.answer !== null; }).length
        });
      });
      return jsonRes(200, {
        success: true,
        data: paginate(mySessions, url.searchParams.get('page'), url.searchParams.get('page_size')),
        message: 'Interview sessions retrieved'
      });
    }

    var ivMatch = path.match(/^\/api\/v1\/interviews\/(\d+)(\/questions|\/answers|\/complete)?$/);
    if (ivMatch) {
      var ivdErr = requireAuthUser();
      if (ivdErr) return ivdErr;
      var sid = Number(ivMatch[1]);
      var sess = db.interviews.find(function (s) { return s.id === sid && s.user_id === currentUser.id; });
      if (!sess) return errRes(404, 'Không tìm thấy phiên phỏng vấn.');
      var sRole = db.roles.find(function (x) { return x.id === sess.career_role_id; });

      if (!ivMatch[2] && method === 'GET') {
        return jsonRes(200, {
          success: true,
          data: Object.assign({}, sess, { career_role: sRole ? { id: sRole.id, name: sRole.name, level: sRole.level } : null }),
          message: 'Session retrieved'
        });
      }
      if (ivMatch[2] === '/questions' && method === 'GET') {
        return jsonRes(200, { success: true, data: sess.questions || [], message: 'Questions retrieved' });
      }
      if (ivMatch[2] === '/answers' && method === 'POST') {
        var q = (sess.questions || []).find(function (item) { return item.id === Number(body.question_id); });
        if (!q) return errRes(404, 'Không tìm thấy câu hỏi.');
        if (q.answer) return errRes(409, 'Câu hỏi này đã được trả lời.');
        var ansText = String(body.answer_text || '').trim();
        var wordScore = Math.min(94, Math.max(72, 70 + Math.floor(ansText.length / 8)));
        q.answer = {
          id: db.nextIds.answer++,
          question_id: q.id,
          answer_text: ansText,
          score: wordScore,
          feedback: ansText.length >= 60 ? 'Câu trả lời chi tiết, mạch lạc và bám sát tiêu chí đánh giá.' : 'Câu trả lời đúng hướng; nên bổ sung thêm ví dụ thực tế để đạt điểm tối đa.',
          created_at: nowIso(0)
        };
        sess.status = 'in_progress';
        sess.updated_at = nowIso(0);
        saveDb(db);
        return jsonRes(201, {
          success: true,
          data: {
            answer: q.answer,
            session_status: sess.status,
            question_count: sess.questions.length,
            answered_count: sess.questions.filter(function (x) { return x.answer !== null; }).length
          },
          message: 'Gửi câu trả lời và chấm điểm thành công.'
        });
      }
      if (ivMatch[2] === '/complete' && method === 'POST') {
        var missing = (sess.questions || []).some(function (x) { return !x.answer; });
        if (missing) return errRes(409, 'Vui lòng trả lời đầy đủ tất cả câu hỏi trước khi hoàn thành.');
        var total = sess.questions.reduce(function (acc, x) { return acc + Number(x.answer.score); }, 0);
        sess.total_score = Math.round((total / sess.questions.length) * 100) / 100;
        sess.status = 'completed';
        sess.completed_at = nowIso(0);
        sess.updated_at = nowIso(0);
        saveDb(db);
        return jsonRes(200, {
          success: true,
          data: {
            id: sess.id,
            status: sess.status,
            total_score: sess.total_score,
            completed_at: sess.completed_at,
            question_count: sess.questions.length,
            answered_count: sess.questions.length
          },
          message: 'Hoàn thành phiên phỏng vấn thành công'
        });
      }
    }

    // ── DASHBOARD ────────────────────────────────────────────
    if (path.indexOf('/api/v1/dashboard/') === 0 && method === 'GET') {
      var dErr = requireAuthUser();
      if (dErr) return dErr;
      var myAnalyses = db.analyses.filter(function (a) { return a.user_id === currentUser.id && a.status === 'completed'; });
      var latestA = myAnalyses.length ? myAnalyses[myAnalyses.length - 1] : null;
      var myProf = db.profiles[currentUser.id];
      var tRole = latestA
        ? db.roles.find(function (r) { return r.id === latestA.career_role_id; })
        : (myProf && myProf.target_role_id ? db.roles.find(function (r) { return r.id === myProf.target_role_id; }) : null);
      var myPlans = db.learningPlans.filter(function (p) { return p.user_id === currentUser.id; });
      var actPlan = myPlans.find(function (p) { return p.status === 'active'; }) || myPlans[myPlans.length - 1] || null;
      var planBrief = null;
      if (actPlan) {
        var pItems = actPlan.items || [];
        var comp = pItems.filter(function (it) { return it.is_completed; }).length;
        planBrief = {
          id: actPlan.id,
          title: actPlan.title,
          target_role: tRole ? tRole.name : null,
          start_date: actPlan.start_date,
          end_date: actPlan.end_date,
          days_left: 23,
          total_tasks: pItems.length,
          completed_tasks: comp,
          progress_percent: pItems.length ? Math.round((comp / pItems.length) * 1000) / 10 : 0
        };
      }

      if (path === '/api/v1/dashboard/summary') {
        var matched = latestA ? latestA.skills.filter(function (s) { return s.current_level >= s.required_level; }).length : 0;
        var gaps = latestA ? latestA.skills.filter(function (s) { return s.current_level < s.required_level; }).length : 0;
        return jsonRes(200, {
          success: true,
          data: {
            readiness_score: latestA ? latestA.readiness_score : null,
            target_role_id: tRole ? tRole.id : null,
            target_role: tRole ? tRole.name : null,
            target_role_level: tRole ? tRole.level : null,
            total_analyses: myAnalyses.length,
            total_interviews: db.interviews.filter(function (i) { return i.user_id === currentUser.id; }).length,
            total_skills_evaluated: latestA ? latestA.skills.length : 0,
            skills_matched_count: matched,
            skills_gap_count: gaps,
            active_plan: planBrief,
            last_analyzed_at: latestA ? latestA.completed_at : null
          }
        });
      }

      if (path === '/api/v1/dashboard/skill-radar') {
        return jsonRes(200, {
          success: true,
          data: {
            role_id: tRole ? tRole.id : null,
            role_name: tRole ? tRole.name : null,
            role_level: tRole ? tRole.level : null,
            overall_readiness: latestA ? latestA.readiness_score : 0,
            skills: latestA ? latestA.skills : []
          }
        });
      }

      if (path === '/api/v1/dashboard/learning-progress') {
        var weeks = [1, 2, 3, 4].map(function (w) {
          var wItems = actPlan ? (actPlan.items || []).filter(function (it) { return it.week_number === w; }) : [];
          var wComp = wItems.filter(function (it) { return it.is_completed; }).length;
          return {
            week_number: w,
            total_tasks: wItems.length,
            completed_tasks: wComp,
            progress_percent: wItems.length ? Math.round((wComp / wItems.length) * 1000) / 10 : 0
          };
        });
        return jsonRes(200, {
          success: true,
          data: { has_active_plan: Boolean(actPlan && actPlan.status === 'active'), plan: planBrief, weekly_breakdown: weeks }
        });
      }

      if (path === '/api/v1/dashboard/readiness-history') {
        var pts = myAnalyses.map(function (a) {
          var r = db.roles.find(function (x) { return x.id === a.career_role_id; });
          return {
            analysis_id: a.id,
            score: a.readiness_score,
            analyzed_at: a.completed_at || a.created_at,
            career_role_name: r ? r.name : 'Vị trí mục tiêu',
            skills: (a.skills || []).map(function (s) { return { skill_id: s.skill_id, skill_name: s.skill_name, current_level: s.current_level }; })
          };
        });
        var sc = pts.map(function (p) { return p.score; });
        var trend = sc.length >= 2 ? (sc[sc.length - 1] > sc[0] ? 'improving' : (sc[sc.length - 1] < sc[0] ? 'declining' : 'stable')) : null;
        return jsonRes(200, {
          success: true,
          data: {
            points: pts,
            stats: {
              report_count: sc.length,
              latest_score: sc.length ? sc[sc.length - 1] : null,
              previous_score: sc.length >= 2 ? sc[sc.length - 2] : null,
              change_since_first: sc.length ? sc[sc.length - 1] - sc[0] : null,
              latest_change: sc.length >= 2 ? sc[sc.length - 1] - sc[sc.length - 2] : null,
              highest_score: sc.length ? Math.max.apply(null, sc) : null,
              lowest_score: sc.length ? Math.min.apply(null, sc) : null,
              trend: trend
            }
          }
        });
      }

      if (path === '/api/v1/dashboard/interview-history') {
        var ivList = db.interviews.filter(function (i) { return i.user_id === currentUser.id; }).map(function (s) {
          var r = db.roles.find(function (x) { return x.id === s.career_role_id; });
          return {
            id: s.id,
            career_role_id: s.career_role_id,
            career_role_name: r ? r.name : 'Chưa xác định',
            status: s.status,
            created_at: s.created_at,
            question_count: (s.questions || []).length,
            answered_count: (s.questions || []).filter(function (q) { return q.answer !== null; }).length,
            total_score: s.total_score,
            completed_at: s.completed_at
          };
        });
        return jsonRes(200, { success: true, data: paginate(ivList, url.searchParams.get('page'), url.searchParams.get('page_size')) });
      }
    }

    // ── ADMIN ────────────────────────────────────────────────
    if (path.indexOf('/api/v1/admin/') === 0) {
      var admErr = requireAdminUser();
      if (admErr) return admErr;

      if (path === '/api/v1/admin/stats' && method === 'GET') {
        var activeU = db.users.filter(function (u) { return u.is_active; }).length;
        return jsonRes(200, {
          success: true,
          data: {
            total_users: db.users.length,
            total_active_users: activeU,
            total_locked_users: db.users.length - activeU,
            total_analyses: db.analyses.length,
            total_interviews: db.interviews.length,
            total_categories: db.categories.length,
            total_roles: db.roles.length,
            total_skills: db.skills.length,
            total_resources: db.resources.length,
            total_pending_resources: db.resources.filter(function (r) { return r.approval_status === 'pending'; }).length
          }
        });
      }

      if (path === '/api/v1/admin/users' && method === 'GET') {
        var uSearch = (url.searchParams.get('search') || '').trim().toLowerCase();
        var uRole = url.searchParams.get('role') || '';
        var uAct = url.searchParams.get('is_active');
        var uList = db.users.map(function (u) {
          var p = db.profiles[u.id];
          return { id: u.id, email: u.email, full_name: p ? p.full_name : null, role: u.role, is_active: u.is_active, created_at: u.created_at, updated_at: u.updated_at };
        }).filter(function (u) {
          if (uSearch && (u.email.toLowerCase().indexOf(uSearch) === -1 && String(u.full_name || '').toLowerCase().indexOf(uSearch) === -1)) return false;
          if (uRole && u.role !== uRole) return false;
          if (uAct !== null && uAct !== '' && String(u.is_active) !== uAct) return false;
          return true;
        });
        return jsonRes(200, { success: true, data: paginate(uList, url.searchParams.get('page'), url.searchParams.get('page_size')) });
      }

      var userDetMatch = path.match(/^\/api\/v1\/admin\/users\/(\d+)$/);
      if (userDetMatch && method === 'GET') {
        var uidDet = Number(userDetMatch[1]);
        var targetU = db.users.find(function (u) { return u.id === uidDet; });
        if (!targetU) return errRes(404, 'User not found');
        var tp = db.profiles[uidDet] || null;
        var tRoleObj = tp && tp.target_role_id ? db.roles.find(function (r) { return r.id === tp.target_role_id; }) : null;
        return jsonRes(200, {
          success: true,
          data: {
            id: targetU.id, email: targetU.email, full_name: tp ? tp.full_name : null,
            role: targetU.role, is_active: targetU.is_active, created_at: targetU.created_at, updated_at: targetU.updated_at,
            profile: tp ? Object.assign({}, tp, { target_role_name: tRoleObj ? tRoleObj.name : null }) : null,
            total_analyses: db.analyses.filter(function (a) { return a.user_id === uidDet; }).length,
            total_interviews: db.interviews.filter(function (i) { return i.user_id === uidDet; }).length
          }
        });
      }

      var userStatMatch = path.match(/^\/api\/v1\/admin\/users\/(\d+)\/status$/);
      if (userStatMatch && method === 'PUT') {
        var uidStat = Number(userStatMatch[1]);
        var uStat = db.users.find(function (u) { return u.id === uidStat; });
        if (!uStat) return errRes(404, 'User not found');
        if (uStat.id === currentUser.id && !body.is_active) return errRes(400, 'You cannot lock your own account');
        uStat.is_active = Boolean(body.is_active);
        uStat.updated_at = nowIso(0);
        saveDb(db);
        return jsonRes(200, { success: true, data: { id: uStat.id, email: uStat.email, role: uStat.role, is_active: uStat.is_active } });
      }

      // Admin Categories CRUD
      if (path === '/api/v1/admin/career-categories' && method === 'GET') {
        var cSearch = (url.searchParams.get('search') || '').trim().toLowerCase();
        var cats = db.categories.map(function (c) {
          return Object.assign({}, c, { role_count: db.roles.filter(function (r) { return r.category_id === c.id; }).length });
        }).filter(function (c) {
          return !cSearch || c.name.toLowerCase().indexOf(cSearch) !== -1 || c.slug.toLowerCase().indexOf(cSearch) !== -1;
        });
        return jsonRes(200, { success: true, data: paginate(cats, url.searchParams.get('page'), url.searchParams.get('page_size')) });
      }
      if (path === '/api/v1/admin/career-categories' && method === 'POST') {
        var newCat = { id: db.nextIds.cat++, name: body.name, slug: body.slug, description: body.description || null, created_at: nowIso(0) };
        db.categories.push(newCat);
        saveDb(db);
        return jsonRes(201, { success: true, data: newCat });
      }
      var catIdMatch = path.match(/^\/api\/v1\/admin\/career-categories\/(\d+)$/);
      if (catIdMatch) {
        var cid = Number(catIdMatch[1]);
        var catObj = db.categories.find(function (c) { return c.id === cid; });
        if (!catObj) return errRes(404, 'Category not found');
        if (method === 'GET') return jsonRes(200, { success: true, data: Object.assign({}, catObj, { roles: db.roles.filter(function (r) { return r.category_id === cid; }) }) });
        if (method === 'PUT') {
          Object.assign(catObj, { name: body.name, slug: body.slug, description: body.description || null });
          saveDb(db);
          return jsonRes(200, { success: true, data: catObj });
        }
        if (method === 'DELETE') {
          db.categories = db.categories.filter(function (c) { return c.id !== cid; });
          saveDb(db);
          return jsonRes(200, { success: true, data: { deleted: true } });
        }
      }

      // Admin Roles CRUD
      if (path === '/api/v1/admin/career-roles' && method === 'GET') {
        var rSearch = (url.searchParams.get('search') || '').trim().toLowerCase();
        var rCat = url.searchParams.get('category_id');
        var rLvl = url.searchParams.get('level');
        var rAct = url.searchParams.get('is_active');
        var rList = db.roles.map(function (r) { return enrichRole(db, r); }).filter(function (r) {
          if (rSearch && r.name.toLowerCase().indexOf(rSearch) === -1 && r.slug.toLowerCase().indexOf(rSearch) === -1) return false;
          if (rCat && String(r.category_id) !== String(rCat)) return false;
          if (rLvl && r.level !== rLvl) return false;
          if (rAct !== null && rAct !== '' && String(r.is_active) !== rAct) return false;
          return true;
        });
        return jsonRes(200, { success: true, data: paginate(rList, url.searchParams.get('page'), url.searchParams.get('page_size')) });
      }
      if (path === '/api/v1/admin/career-roles' && method === 'POST') {
        var nr = {
          id: db.nextIds.role++,
          category_id: body.category_id || null,
          name: body.name,
          slug: body.slug,
          level: body.level || 'Junior',
          description: body.description || null,
          is_active: body.is_active !== false,
          required_skills: body.required_skills || [],
          created_at: nowIso(0)
        };
        db.roles.push(nr);
        saveDb(db);
        return jsonRes(201, { success: true, data: enrichRole(db, nr) });
      }
      var roleIdMatch = path.match(/^\/api\/v1\/admin\/career-roles\/(\d+)(\/status)?$/);
      if (roleIdMatch) {
        var rid = Number(roleIdMatch[1]);
        var roObj = db.roles.find(function (r) { return r.id === rid; });
        if (!roObj) return errRes(404, 'Role not found');
        if (roleIdMatch[2] === '/status' && method === 'PATCH') {
          roObj.is_active = Boolean(body.is_active);
          saveDb(db);
          return jsonRes(200, { success: true, data: enrichRole(db, roObj) });
        }
        if (method === 'GET') return jsonRes(200, { success: true, data: enrichRole(db, roObj) });
        if (method === 'PUT') {
          Object.assign(roObj, {
            category_id: body.category_id || null,
            name: body.name,
            slug: body.slug,
            level: body.level || roObj.level,
            description: body.description || null,
            is_active: body.is_active !== false,
            required_skills: body.required_skills || []
          });
          saveDb(db);
          return jsonRes(200, { success: true, data: enrichRole(db, roObj) });
        }
        if (method === 'DELETE') {
          db.roles = db.roles.filter(function (r) { return r.id !== rid; });
          saveDb(db);
          return jsonRes(200, { success: true, data: { deleted: true } });
        }
      }

      // Admin Skills CRUD
      if (path === '/api/v1/admin/skills' && method === 'GET') {
        var sSearch = (url.searchParams.get('search') || '').trim().toLowerCase();
        var sAct = url.searchParams.get('is_active');
        var skList = db.skills.filter(function (s) {
          if (sSearch && s.name.toLowerCase().indexOf(sSearch) === -1) return false;
          if (sAct !== null && sAct !== '' && String(s.is_active) !== sAct) return false;
          return true;
        });
        return jsonRes(200, { success: true, data: paginate(skList, url.searchParams.get('page'), url.searchParams.get('page_size')) });
      }
      if (path === '/api/v1/admin/skills' && method === 'POST') {
        var nsk = { id: db.nextIds.skill++, name: body.name, description: body.description || null, is_active: true, created_at: nowIso(0) };
        db.skills.push(nsk);
        saveDb(db);
        return jsonRes(201, { success: true, data: nsk });
      }
      var skIdMatch = path.match(/^\/api\/v1\/admin\/skills\/(\d+)(\/status)?$/);
      if (skIdMatch) {
        var skid = Number(skIdMatch[1]);
        var skObj = db.skills.find(function (s) { return s.id === skid; });
        if (!skObj) return errRes(404, 'Skill not found');
        if (skIdMatch[2] === '/status' && method === 'PATCH') {
          skObj.is_active = Boolean(body.is_active);
          saveDb(db);
          return jsonRes(200, { success: true, data: skObj });
        }
        if (method === 'PUT') {
          Object.assign(skObj, { name: body.name, description: body.description || null });
          saveDb(db);
          return jsonRes(200, { success: true, data: skObj });
        }
        if (method === 'DELETE') {
          db.skills = db.skills.filter(function (s) { return s.id !== skid; });
          saveDb(db);
          return jsonRes(200, { success: true, data: { deleted: true } });
        }
      }

      // Admin Resources CRUD
      if (path === '/api/v1/admin/resources' && method === 'GET') {
        var reSearch = (url.searchParams.get('search') || '').trim().toLowerCase();
        var reType = url.searchParams.get('resource_type');
        var reApp = url.searchParams.get('approval_status');
        var reAct = url.searchParams.get('is_active');
        var resList = db.resources.map(function (r) { return enrichResource(db, r); }).filter(function (r) {
          if (reSearch && r.title.toLowerCase().indexOf(reSearch) === -1 && r.provider.toLowerCase().indexOf(reSearch) === -1) return false;
          if (reType && r.resource_type !== reType) return false;
          if (reApp && r.approval_status !== reApp) return false;
          if (reAct !== null && reAct !== '' && String(r.is_active) !== reAct) return false;
          return true;
        });
        return jsonRes(200, { success: true, data: paginate(resList, url.searchParams.get('page'), url.searchParams.get('page_size')) });
      }
      if (path === '/api/v1/admin/resources' && method === 'POST') {
        var nres = {
          id: db.nextIds.resource++,
          slug: body.slug,
          skill_id: body.skill_id || null,
          title: body.title,
          provider: body.provider,
          url: body.url,
          resource_type: body.resource_type || 'course',
          description: body.description || null,
          language: body.language || 'en',
          is_free: body.is_free !== false,
          is_active: body.is_active !== false,
          approval_status: 'pending',
          created_at: nowIso(0)
        };
        db.resources.push(nres);
        saveDb(db);
        return jsonRes(201, { success: true, data: enrichResource(db, nres) });
      }
      var resIdMatch = path.match(/^\/api\/v1\/admin\/resources\/(\d+)(\/status|\/approval)?$/);
      if (resIdMatch) {
        var reid = Number(resIdMatch[1]);
        var reObj = db.resources.find(function (r) { return r.id === reid; });
        if (!reObj) return errRes(404, 'Resource not found');
        if (resIdMatch[2] === '/status' && method === 'PATCH') {
          reObj.is_active = Boolean(body.is_active);
          saveDb(db);
          return jsonRes(200, { success: true, data: enrichResource(db, reObj) });
        }
        if (resIdMatch[2] === '/approval' && method === 'PATCH') {
          reObj.approval_status = body.approval_status || 'approved';
          saveDb(db);
          return jsonRes(200, { success: true, data: enrichResource(db, reObj) });
        }
        if (method === 'GET') return jsonRes(200, { success: true, data: enrichResource(db, reObj) });
        if (method === 'PUT') {
          Object.assign(reObj, {
            slug: body.slug, title: body.title, provider: body.provider, url: body.url,
            skill_id: body.skill_id || null, resource_type: body.resource_type,
            description: body.description || null, language: body.language || 'en',
            is_free: body.is_free !== false, is_active: body.is_active !== false,
            approval_status: 'pending'
          });
          saveDb(db);
          return jsonRes(200, { success: true, data: enrichResource(db, reObj) });
        }
        if (method === 'DELETE') {
          db.resources = db.resources.filter(function (r) { return r.id !== reid; });
          saveDb(db);
          return jsonRes(200, { success: true, data: { deleted: true } });
        }
      }
    }

    return errRes(404, 'Endpoint not found in static demo');
  }

  window.fetch = function (input, init) {
    var reqUrl = typeof input === 'string' ? input : (input && input.url) || '';
    if (reqUrl.indexOf('/api/v1/') !== -1) {
      return handleApi(input, init);
    }
    return nativeFetch(input, init);
  };
})();
