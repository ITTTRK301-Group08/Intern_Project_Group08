/**
 * Quản lý phiên đăng nhập dùng chung cho các trang La Bàn.
 * - Trang khai báo data-require-auth="true" sẽ chuyển về /login nếu chưa có token.
 * - Hiển thị tài khoản đang đăng nhập và nút "Đăng nhập"/"Đăng xuất" trên nav chung.
 * - Chuẩn hóa thông điệp phản hồi từ backend sang tiếng Việt thân thiện, tránh lộ chi tiết kỹ thuật.
 */
(function () {
  'use strict';

  if (window.LaBanApp) return;

  var TOKEN_KEY = 'acm_access_token';
  var requiresAuth = document.documentElement.getAttribute('data-require-auth') === 'true';

  var isDirectMode = window.location.protocol === 'file:' ||
                     window.location.pathname.indexOf('/app/static/') !== -1 ||
                     window.location.pathname.endsWith('.html') ||
                     !window.location.host;

  function readToken() {
    try {
      var stored = localStorage.getItem(TOKEN_KEY) || '';
      if (!stored && isDirectMode) {
        stored = 'demo_student_token';
        try { localStorage.setItem(TOKEN_KEY, stored); } catch (_) {}
      }
      return stored;
    } catch (_) {
      return isDirectMode ? 'demo_student_token' : '';
    }
  }

  function clearToken() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch (_) {
      /* bỏ qua khi trình duyệt chặn storage */
    }
  }

  function loginUrl() {
    if (isDirectMode) return './login.html';
    var next = window.location.pathname + window.location.search;
    return '/login?next=' + encodeURIComponent(next);
  }

  function redirectToLogin() {
    clearToken();
    window.location.replace(loginUrl());
  }

  var MESSAGE_MAP = {
    'Email already registered': 'Email này đã được đăng ký. Vui lòng đăng nhập hoặc dùng email khác.',
    'Incorrect email or password': 'Email hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.',
    'Account is inactive': 'Tài khoản của bạn hiện đang tạm khóa. Vui lòng liên hệ quản trị viên.',
    'Token has expired': 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
    'Could not validate credentials': 'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.',
    'Not authenticated': 'Bạn cần đăng nhập để thực hiện thao tác này.',
    'Profile not found': 'Chưa có hồ sơ cá nhân.',
    'CV not found': 'Không tìm thấy CV yêu cầu.',
    'CV not found or already deleted': 'CV này đã bị xóa hoặc không còn khả dụng.',
    'You do not have permission to access this CV': 'Bạn không có quyền truy cập CV này.',
    'You do not have permission to delete this CV': 'Bạn không có quyền xóa CV này.',
    'Only PDF files are allowed': 'Chỉ hỗ trợ tải lên tệp định dạng PDF.',
    'File is empty': 'Tệp tải lên đang bị trống.',
    'File size exceeds 5MB limit': 'Dung lượng tệp vượt quá giới hạn tối đa 5 MB.',
    'Invalid file MIME type': 'Định dạng tệp không phải PDF hợp lệ.',
    'Invalid PDF file content': 'Nội dung tệp không phải PDF hợp lệ (có thể tệp bị đổi đuôi hoặc hỏng).',
    'Encrypted PDF is not supported': 'Hệ thống chưa hỗ trợ tệp PDF có đặt mật khẩu bảo vệ. Vui lòng gỡ mật khẩu rồi tải lại.',
    'Unable to read or extract text from PDF': 'Không thể đọc nội dung tệp PDF này. Vui lòng kiểm tra lại tệp trước khi tải lên.',
    'Request validation failed': 'Thông tin nhập chưa hợp lệ. Vui lòng kiểm tra lại các trường bắt buộc.',
    'Internal server error': 'Hệ thống đang bận xử lý. Vui lòng thử lại sau ít phút.',
    'Career role not found': 'Không tìm thấy vị trí nghề nghiệp đã chọn.',
    'Khong tim thay CV hoac CV khong kha dung.': 'CV đã chọn không tồn tại hoặc không còn khả dụng.',
    'Ban khong co quyen su dung CV nay.': 'Bạn không có quyền sử dụng CV này.',
    'Da xac nhan consent hop le, nhung pipeline phan tich AI (M4) chua duoc trien khai trong Task 4.':
      'Đã xác nhận đồng ý sử dụng dữ liệu. Tính năng phân tích tự động đang được hoàn thiện.',
    'Lay ho so thanh cong': 'Đã tải hồ sơ cá nhân.',
    'Cap nhat ho so thanh cong': 'Đã lưu cập nhật hồ sơ thành công.',
    'Upload CV thanh cong': 'Đã tải CV lên thành công.',
    'Lay danh sach CV thanh cong': 'Đã cập nhật danh sách CV.',
    'Lay chi tiet CV thanh cong': 'Đã tải chi tiết CV.',
    'Da xoa CV thanh cong.': 'Đã xóa CV thành công.',
    'CV da gan voi bao cao phan tich lich su nen da duoc xoa mem (an trang thai hoat dong).':
      'CV đã gắn với báo cáo phân tích trước đó nên được chuyển sang trạng thái lưu trữ để bảo toàn lịch sử.',
    'Nguoi dung chua dong y cho phep su dung du lieu cho AI.':
      'Bạn cần xác nhận đồng ý sử dụng dữ liệu trước khi bắt đầu phân tích.',
    'Phien ban muc dich consent khong hop le hoac khong duoc ho tro.':
      'Thông tin xác nhận chưa hợp lệ. Vui lòng tải lại trang và thử lại.'
  };

  function translateText(raw) {
    if (!raw || typeof raw !== 'string') return '';
    var trimmed = raw.trim();
    if (Object.prototype.hasOwnProperty.call(MESSAGE_MAP, trimmed)) {
      return MESSAGE_MAP[trimmed];
    }
    var lower = trimmed.toLowerCase();
    if (lower.indexOf('khong trich xuat duoc') >= 0) {
      return 'CV đã được tải lên nhưng chưa đọc được văn bản (có thể là tệp PDF dạng ảnh quét). Bạn có thể xem hướng dẫn bên dưới.';
    }
    if (lower.indexOf('full_name') >= 0 && lower.indexOf('required') >= 0) {
      return 'Vui lòng nhập họ và tên của bạn.';
    }
    if (lower.indexOf('5mb') >= 0) {
      return 'Dung lượng tệp vượt quá 5 MB.';
    }
    return trimmed;
  }

  function extractApiError(body, fallback) {
    if (!body || typeof body !== 'object') return fallback || 'Yêu cầu chưa thể thực hiện. Vui lòng thử lại.';
    var detail = body.detail;
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      if (typeof detail.message === 'string') return translateText(detail.message);
    }
    if (Array.isArray(detail) && detail.length) {
      var msgs = detail.map(function (item) {
        if (!item) return '';
        var loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
        if (loc.indexOf('full_name') >= 0) return 'Họ và tên không được để trống.';
        if (loc.indexOf('skill_name') >= 0) return 'Tên kỹ năng không được để trống.';
        if (loc.indexOf('strength') >= 0) return 'Nội dung điểm mạnh không được để trống.';
        if (loc.indexOf('level') >= 0) return 'Mức đánh giá kỹ năng phải nằm trong khoảng 0 đến 5.';
        if (typeof item.msg === 'string') return translateText(item.msg);
        return '';
      }).filter(Boolean);
      if (msgs.length) return msgs.join(' ');
    }
    if (typeof detail === 'string') return translateText(detail);
    if (typeof body.message === 'string' && body.message) return translateText(body.message);
    return fallback || 'Yêu cầu chưa thể thực hiện. Vui lòng thử lại.';
  }

  function formatBytes(bytes) {
    var size = Number(bytes || 0);
    if (size < 1024) return size + ' B';
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
    return (size / (1024 * 1024)).toFixed(2) + ' MB';
  }

  function formatDate(iso) {
    if (!iso) return '-';
    var dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return String(iso);
    return dt.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  window.LaBanApp = {
    TOKEN_KEY: TOKEN_KEY,
    getToken: readToken,
    clearToken: clearToken,
    redirectToLogin: redirectToLogin,
    translateText: translateText,
    extractApiError: extractApiError,
    formatBytes: formatBytes,
    formatDate: formatDate
  };

  var token = readToken();
  if (requiresAuth && !token) {
    window.location.replace(loginUrl());
    return;
  }

  function renderGuestNav(nav) {
    Array.prototype.slice.call(nav.querySelectorAll('[data-auth-slot="true"]')).forEach(function (el) {
      el.remove();
    });

    var divider = document.createElement('span');
    divider.className = 'nav-divider';
    divider.setAttribute('aria-hidden', 'true');
    divider.setAttribute('data-auth-slot', 'true');

    var registerLink = document.createElement('a');
    registerLink.href = isDirectMode ? './register.html' : '/register';
    registerLink.textContent = 'Đăng ký';
    registerLink.setAttribute('data-auth-slot', 'true');

    var loginLink = document.createElement('a');
    loginLink.href = isDirectMode ? './login.html' : loginUrl();
    loginLink.className = 'nav-cta';
    loginLink.textContent = 'Đăng nhập';
    loginLink.setAttribute('data-auth-slot', 'true');

    nav.append(divider, registerLink, loginLink);
  }

  function renderSignedInNav(nav) {
    Array.prototype.slice.call(nav.querySelectorAll('[data-auth-slot="true"]')).forEach(function (el) {
      el.remove();
    });

    var divider = document.createElement('span');
    divider.className = 'nav-divider';
    divider.setAttribute('aria-hidden', 'true');
    divider.setAttribute('data-auth-slot', 'true');

    var userPill = document.createElement('span');
    userPill.className = 'nav-user';
    userPill.id = 'navUserEmail';
    userPill.hidden = false;
    userPill.textContent = 'sinhvien@example.com';
    userPill.title = 'Tài khoản của bạn';
    userPill.setAttribute('data-auth-slot', 'true');

    var logoutBtn = document.createElement('button');
    logoutBtn.type = 'button';
    logoutBtn.className = 'nav-action';
    logoutBtn.textContent = 'Đăng xuất';
    logoutBtn.setAttribute('data-auth-slot', 'true');
    logoutBtn.addEventListener('click', function () {
      clearToken();
      window.location.assign(isDirectMode ? './login.html' : '/login');
    });

    nav.append(divider, userPill, logoutBtn);
    return userPill;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var nav = document.querySelector('.site-nav');
    if (nav) {
      var userPill = null;
      if (token) {
        userPill = renderSignedInNav(nav);
      } else {
        renderGuestNav(nav);
      }

      if (token && token !== 'demo_student_token') {
        fetch('/api/v1/auth/me', { headers: { Authorization: 'Bearer ' + token } })
          .then(function (res) {
            if (res.status === 401) {
              clearToken();
              if (requiresAuth) {
                window.location.replace(loginUrl());
              } else {
                renderGuestNav(nav);
              }
              return null;
            }
            if (!res.ok) return null;
            return res.json().catch(function () { return null; });
          })
          .then(function (body) {
            if (userPill && body && body.data && body.data.email) {
              userPill.textContent = body.data.email;
              userPill.title = body.data.email;
              userPill.hidden = false;
            }
          })
          .catch(function () {
            /* Giữ nguyên trạng thái hiện tại. */
          });
      }
    }

    if (isDirectMode) {
      var ROUTE_TO_FILE = {
        '/': './explore.html',
        '/explore': './explore.html',
        '/profile': './profile.html',
        '/cv': './cv.html',
        '/analysis': './analysis.html',
        '/login': './login.html',
        '/register': './register.html'
      };
      var links = document.querySelectorAll('a[href]');
      Array.prototype.forEach.call(links, function (a) {
        var href = a.getAttribute('href');
        if (ROUTE_TO_FILE[href]) {
          a.setAttribute('href', ROUTE_TO_FILE[href]);
        } else if (href && href.indexOf('/login?next=') === 0) {
          a.setAttribute('href', './login.html');
        }
      });
    }
  });
})();
