(function () {
  'use strict';

  if (window.__LaBanSessionLoaded__) return;
  window.__LaBanSessionLoaded__ = true;

  var TOKEN_KEY = 'acm_access_token';
  var REFRESH_TOKEN_KEY = 'acm_refresh_token';
  var requiresAuth = document.documentElement.getAttribute('data-require-auth') === 'true';
  var isDirectMode = window.location.protocol === 'file:' ||
    window.location.pathname.indexOf('/app/static/') !== -1 ||
    window.location.pathname.endsWith('.html') ||
    !window.location.host;
  var originalFetch = window.fetch.bind(window);
  var refreshInFlight = null;
  var token;

  function readStoredToken(key) {
    try { return localStorage.getItem(key) || ''; } catch (_) { return ''; }
  }

  function saveTokens(data) {
    try {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      return true;
    } catch (error) {
      clearTokens();
      console.error('Unable to persist session tokens:', error);
      return false;
    }
  }

  function clearTokens() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Unable to clear session tokens:', error);
    }
  }

  function loginUrl() {
    if (isDirectMode) return './login.html';
    var next = window.location.pathname + window.location.search;
    return '/login?next=' + encodeURIComponent(next);
  }

  function redirectToLogin() {
    clearTokens();
    window.location.replace(loginUrl());
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
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok || !body.data ||
            !body.data.access_token || !body.data.refresh_token) {
          if (response.status === 401 || response.status === 403) clearTokens();
          throw new Error('Refresh token rejected with status ' + response.status);
        }
        if (!saveTokens(body.data)) throw new Error('Unable to save refreshed tokens');
        return body.data.access_token;
      });
    }).catch(function (error) {
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

  var MESSAGE_MAP = {
    'Email already registered': 'Email này đã được đăng ký. Vui lòng đăng nhập hoặc dùng email khác.',
    'Incorrect email or password': 'Email hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.',
    'Account is inactive': 'Tài khoản của bạn hiện đang tạm khóa. Vui lòng liên hệ quản trị viên.',
    'Token has expired': 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
    'Could not validate credentials': 'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.',
    'Not authenticated': 'Bạn cần đăng nhập để thực hiện thao tác này.',
    'Profile not found': 'Chưa có hồ sơ cá nhân.',
    'CV not found': 'Không tìm thấy CV yêu cầu.',
    'Career role not found': 'Không tìm thấy vị trí nghề nghiệp đã chọn.',
    'Internal server error': 'Hệ thống đang bận xử lý. Vui lòng thử lại sau ít phút.'
  };

  function translateText(raw) {
    if (!raw || typeof raw !== 'string') return '';
    var text = raw.trim();
    return Object.prototype.hasOwnProperty.call(MESSAGE_MAP, text) ? MESSAGE_MAP[text] : text;
  }

  function extractApiError(body, fallback) {
    var detail = body && body.detail;
    if (detail && typeof detail === 'object' && !Array.isArray(detail) &&
        typeof detail.message === 'string') {
      return translateText(detail.message);
    }
    if (Array.isArray(detail)) {
      var messages = detail.map(function (item) {
        return item && typeof item.msg === 'string' ? translateText(item.msg) : '';
      }).filter(Boolean);
      if (messages.length) return messages.join(' ');
    }
    if (typeof detail === 'string') return translateText(detail);
    if (body && typeof body.message === 'string') return translateText(body.message);
    return fallback || 'Yêu cầu chưa thể thực hiện. Vui lòng thử lại.';
  }

  function formatBytes(bytes) {
    var size = Number(bytes || 0);
    if (size < 1024) return size + ' B';
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
    return (size / (1024 * 1024)).toFixed(2) + ' MB';
  }

  function formatDate(value) {
    if (!value) return '-';
    var date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('vi-VN');
  }

  window.LaBanApp = {
    TOKEN_KEY: TOKEN_KEY,
    getToken: function () { return readStoredToken(TOKEN_KEY); },
    clearToken: clearTokens,
    redirectToLogin: redirectToLogin,
    translateText: translateText,
    extractApiError: extractApiError,
    formatBytes: formatBytes,
    formatDate: formatDate
  };

  token = readStoredToken(TOKEN_KEY);
  if (requiresAuth && !token) {
    window.location.replace(loginUrl());
    return;
  }

  function renderGuestNav(nav) {
    var login = document.createElement('a');
    login.href = isDirectMode ? './login.html' : loginUrl();
    login.className = 'nav-cta';
    login.textContent = 'Đăng nhập';
    nav.appendChild(login);
  }

  function renderSignedInNav(nav, email) {
    var user = document.createElement('span');
    user.className = 'nav-user';
    user.textContent = email || 'Tài khoản';
    user.title = email || 'Tài khoản của bạn';
    var logout = document.createElement('button');
    logout.type = 'button';
    logout.className = 'nav-action';
    logout.textContent = 'Đăng xuất';
    logout.addEventListener('click', function () {
      var refreshToken = readStoredToken(REFRESH_TOKEN_KEY);
      logout.disabled = true;
      var revoke = refreshToken
        ? originalFetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        }).then(function (response) {
          if (!response.ok) throw new Error('Logout request failed with status ' + response.status);
        })
        : Promise.resolve();
      revoke.catch(function (error) {
        console.error('Session revocation failed:', error);
        window.alert('Không thể xác nhận thu hồi phiên với máy chủ. Phiên đăng nhập trên trình duyệt sẽ được xóa.');
      }).then(function () {
        clearTokens();
        window.location.assign(isDirectMode ? './login.html' : '/login');
      });
    });
    nav.append(user, logout);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var nav = document.querySelector('.site-nav');
    if (nav) {
      if (!token) {
        renderGuestNav(nav);
      } else {
        renderSignedInNav(nav, '');
        fetch('/api/v1/auth/me', { headers: { Authorization: 'Bearer ' + token } })
          .then(function (response) {
            if (response.status === 401 && requiresAuth) redirectToLogin();
            if (!response.ok) return null;
            return response.json().catch(function () { return null; });
          })
          .then(function (body) {
            var user = nav.querySelector('.nav-user');
            var email = body && body.data && body.data.email;
            if (user && email) {
              user.textContent = email;
              user.title = email;
            }
          })
          .catch(function (error) {
            console.error('Unable to load current session:', error);
          });
      }
    }
  });
})();
