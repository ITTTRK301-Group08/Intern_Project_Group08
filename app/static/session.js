/**
 * Quản lý phiên đăng nhập dùng chung cho các trang nội bộ.
 * - Trang khai báo data-require-auth="true" sẽ chuyển về /login nếu chưa có token.
 * - Tự thêm mục "Đăng nhập"/"Đăng xuất" vào nav chung.
 * - Token hết hạn (401) sẽ bị xóa và chuyển về trang đăng nhập.
 */
(function () {
  'use strict';

  var TOKEN_KEY = 'acm_access_token';
  var REFRESH_TOKEN_KEY = 'acm_refresh_token';
  var requiresAuth = document.documentElement.getAttribute('data-require-auth') === 'true';
  var originalFetch = window.fetch.bind(window);
  var refreshInFlight = null;
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

  function readStoredToken(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }

  function saveTokens(data) {
    try {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      return true;
    } catch (_) {
      clearTokens();
      return false;
    }
  }

  function clearTokens() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    } catch (_) { /* trình duyệt chặn lưu trữ */ }
  }

  function refreshAccessToken() {
    if (refreshInFlight) return refreshInFlight;
    var refreshToken = readStoredToken(REFRESH_TOKEN_KEY);
    if (!refreshToken) return Promise.resolve(null);

    refreshInFlight = originalFetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    }).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok || !body.data ||
            !body.data.access_token || !body.data.refresh_token) {
          throw new Error('Refresh token rejected');
        }
        if (!saveTokens(body.data)) throw new Error('Browser storage unavailable');
        return body.data.access_token;
      });
    }).catch(function (error) {
      clearTokens();
      console.error('Session refresh failed:', error);
      return null;
    }).then(function (accessToken) {
      refreshInFlight = null;
      return accessToken;
    });
    return refreshInFlight;
  }

  function retryWithToken(request, accessToken) {
    var headers = new Headers(request.headers);
    headers.set('Authorization', 'Bearer ' + accessToken);
    return originalFetch(new Request(request, { headers: headers }));
  }

  window.fetch = function (input, init) {
    var request = new Request(input, init);
    var authorization = request.headers.get('Authorization') || '';
    var requestUrl = new URL(request.url, window.location.href);
    var refreshable = requestUrl.origin === window.location.origin &&
      requestUrl.pathname.indexOf('/api/v1/') === 0 &&
      !/^\/api\/v1\/auth\/(login|register|refresh|logout)$/.test(requestUrl.pathname) &&
      authorization.indexOf('Bearer ') === 0;

    return originalFetch(request.clone()).then(function (response) {
      if (!refreshable || response.status !== 401) return response;

      var latestToken = readStoredToken(TOKEN_KEY);
      var sentToken = authorization.substring(7);
      if (latestToken && latestToken !== sentToken) {
        return retryWithToken(request, latestToken);
      }

      return refreshAccessToken().then(function (accessToken) {
        if (!accessToken) {
          if (requiresAuth) window.location.replace(loginUrl());
          return response;
        }
        return retryWithToken(request, accessToken);
      });
    });
  };

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
        var refreshToken = readStoredToken(REFRESH_TOKEN_KEY);
        logout.disabled = true;
        var revoke = refreshToken
          ? window.fetch('/api/v1/auth/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
          }).then(function (response) {
            if (!response.ok) throw new Error('Logout request failed');
          })
          : Promise.resolve();
        revoke.catch(function (error) {
          console.error('Session revocation failed:', error);
          window.alert('Không thể xác nhận thu hồi phiên với máy chủ. Phiên đăng nhập trên trình duyệt đã được xóa.');
        }).then(function () {
          clearTokens();
          window.location.assign('/login');
        });
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
          clearTokens();
          window.location.replace(loginUrl());
        }
      })
      .catch(function () { /* Mất mạng: giữ nguyên trang. */ });
  }
})();
