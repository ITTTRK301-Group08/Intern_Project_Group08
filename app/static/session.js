/**
 * Quản lý phiên đăng nhập dùng chung cho các trang nội bộ.
 * - Trang khai báo data-require-auth="true" sẽ chuyển về /login nếu chưa có token.
 * - Tự thêm mục "Đăng nhập"/"Đăng xuất" vào nav chung.
 * - Token hết hạn (401) sẽ bị xóa và chuyển về trang đăng nhập.
 */
(function () {
  'use strict';

  var TOKEN_KEY = 'acm_access_token';
  var requiresAuth = document.documentElement.getAttribute('data-require-auth') === 'true';
  var token = null;

  try {
    token = localStorage.getItem(TOKEN_KEY);
  } catch (_) {
    token = null;
  }

  function loginUrl() {
    var next = window.location.pathname + window.location.search;
    return '/login?next=' + encodeURIComponent(next);
  }

  if (requiresAuth && !token) {
    window.location.replace(loginUrl());
    return;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var nav = document.querySelector('.site-nav');
    if (!nav) return;

    if (token) {
      var logout = document.createElement('button');
      logout.type = 'button';
      logout.className = 'nav-action';
      logout.textContent = 'Đăng xuất';
      logout.addEventListener('click', function () {
        try { localStorage.removeItem(TOKEN_KEY); } catch (_) { /* bỏ qua */ }
        window.location.assign('/login');
      });
      nav.appendChild(logout);
    } else {
      var login = document.createElement('a');
      login.href = loginUrl();
      login.textContent = 'Đăng nhập';
      nav.appendChild(login);
    }
  });

  // Kiểm tra token còn hiệu lực để tránh hiển thị lỗi 401 rải rác trên trang.
  if (requiresAuth && token) {
    fetch('/api/v1/auth/me', { headers: { Authorization: 'Bearer ' + token } })
      .then(function (res) {
        if (res.status === 401) {
          try { localStorage.removeItem(TOKEN_KEY); } catch (_) { /* bỏ qua */ }
          window.location.replace(loginUrl());
        }
      })
      .catch(function () { /* Mất mạng: giữ nguyên trang. */ });
  }
})();
