/**
 * Xử lý biểu mẫu đăng nhập (UI-01) và đăng ký tài khoản.
 * Chỉ gọi API công khai /api/v1/auth/register và /api/v1/auth/login;
 * access token được lưu ở localStorage với khóa dùng chung acm_access_token.
 */
(function () {
  'use strict';

  if (window.__LaBanAuthLoaded__) return;
  window.__LaBanAuthLoaded__ = true;

  var TOKEN_KEY = 'acm_access_token';
  var isDirectMode = window.location.protocol === 'file:' ||
                     window.location.pathname.indexOf('/app/static/') !== -1 ||
                     window.location.pathname.endsWith('.html') ||
                     !window.location.host;
  var $ = function (id) { return document.getElementById(id); };

  var ERROR_MAP = {
    'Email already registered': 'Email này đã được đăng ký. Vui lòng đăng nhập hoặc dùng email khác.',
    'Incorrect email or password': 'Email hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.',
    'Account is inactive': 'Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.',
    'Request validation failed': 'Thông tin chưa hợp lệ. Vui lòng kiểm tra lại email và mật khẩu.'
  };

  function setStatus(el, message, type) {
    el.textContent = message || '';
    el.className = 'status' + (type ? ' ' + type : '');
  }

  function clearFieldErrors(form) {
    Array.prototype.slice.call(form.querySelectorAll('input')).forEach(function (input) {
      input.removeAttribute('aria-invalid');
    });
  }

  function markFieldError(input) {
    if (input) {
      input.setAttribute('aria-invalid', 'true');
      input.focus();
    }
  }

  /** Chỉ chấp nhận đường dẫn nội bộ để tránh chuyển hướng ra ngoài (open redirect). */
  function readSafeNext() {
    var raw = '';
    try {
      raw = new URLSearchParams(window.location.search).get('next') || '';
    } catch (_) {
      raw = '';
    }
    if (raw.charAt(0) === '/' && raw.charAt(1) !== '/' && raw.charAt(1) !== '\\') {
      return raw;
    }
    return '';
  }

  function nextTarget(fallback) {
    var target = readSafeNext() || fallback;
    if (isDirectMode) {
      if (target === '/explore' || target === '/') return './explore.html';
      if (target === '/profile') return './profile.html';
      if (target === '/cv') return './cv.html';
      if (target === '/analysis') return './analysis.html';
      if (target === '/login') return './login.html';
      if (target === '/register') return './register.html';
    }
    return target;
  }

  function syncSwitchLinks() {
    var next = readSafeNext();
    if (!next) return;
    var query = '?next=' + encodeURIComponent(next);
    if ($('switchToRegisterLink')) $('switchToRegisterLink').href = '/register' + query;
    if ($('switchToLoginLink')) $('switchToLoginLink').href = '/login' + query;
  }

  function describeError(res, body) {
    if (res.status === 422) {
      var details = (body && Array.isArray(body.detail)) ? body.detail : [];
      var hasField = function (field) {
        return details.some(function (item) {
          return Array.isArray(item.loc) && item.loc.indexOf(field) >= 0;
        });
      };
      if (hasField('email')) return 'Email chưa đúng định dạng. Vui lòng kiểm tra lại.';
      if (hasField('password')) return 'Mật khẩu phải có từ 8 đến 72 ký tự.';
      return 'Thông tin chưa hợp lệ. Vui lòng kiểm tra lại.';
    }
    if (res.status === 429) {
      return 'Bạn đã thử quá nhiều lần. Vui lòng chờ một lát rồi thử lại.';
    }
    if (res.status >= 500) {
      return 'Máy chủ đang gặp sự cố. Vui lòng thử lại sau.';
    }
    var message = '';
    if (body && typeof body.message === 'string') message = body.message;
    else if (body && typeof body.detail === 'string') message = body.detail;
    else if (body && body.detail && typeof body.detail.message === 'string') message = body.detail.message;
    if (Object.prototype.hasOwnProperty.call(ERROR_MAP, message)) {
      return ERROR_MAP[message];
    }
    return message || 'Yêu cầu thất bại. Vui lòng thử lại.';
  }

  function postJson(path, payload) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        return { res: res, body: body };
      });
    });
  }

  function readToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch (_) { return null; }
  }

  function saveToken(token) {
    try { localStorage.setItem(TOKEN_KEY, token); } catch (_) { /* trình duyệt chặn lưu trữ */ }
  }

  function setBusy(button, busy, busyLabel, idleLabel) {
    button.disabled = busy;
    button.textContent = busy ? busyLabel : idleLabel;
  }

  function bindPasswordToggles() {
    Array.prototype.forEach.call(document.querySelectorAll('.password-toggle'), function (button) {
      var input = $(button.getAttribute('data-target'));
      if (!input) return;
      button.addEventListener('click', function () {
        var isVisible = input.type === 'text';
        input.type = isVisible ? 'password' : 'text';
        button.textContent = isVisible ? 'Hiện' : 'Ẩn';
        button.setAttribute('aria-pressed', String(!isVisible));
      });
    });
  }

  function bindInputReset(form, statusEl) {
    Array.prototype.forEach.call(form.querySelectorAll('input'), function (input) {
      input.addEventListener('input', function () {
        input.removeAttribute('aria-invalid');
        if (statusEl.classList.contains('error')) {
          setStatus(statusEl, '');
        }
      });
    });
  }

  /** Nếu trình duyệt đã có token còn hiệu lực thì chuyển thẳng vào ứng dụng. */
  function redirectIfSignedIn(fallback) {
    var token = readToken();
    if (!token) return;
    fetch('/api/v1/auth/me', { headers: { Authorization: 'Bearer ' + token } })
      .then(function (res) {
        if (res.ok) {
          window.location.replace(nextTarget(fallback));
          return;
        }
        if (res.status === 401) {
          try { localStorage.removeItem(TOKEN_KEY); } catch (_) { /* bỏ qua */ }
        }
      })
      .catch(function () { /* Mất mạng: giữ người dùng ở lại biểu mẫu. */ });
  }

  function initLogin() {
    var form = $('loginForm');
    var statusEl = $('status');
    var submit = $('submitBtn');
    var demoBtn = $('quickDemoBtn');
    bindInputReset(form, statusEl);

    if (demoBtn) {
      demoBtn.addEventListener('click', function () {
        saveToken('demo_student_token');
        setStatus(statusEl, 'Đã kích hoạt tài khoản mẫu. Đang chuyển vào hệ thống...', 'ok');
        setTimeout(function () {
          window.location.assign(nextTarget('/explore'));
        }, 300);
      });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      setStatus(statusEl, '');
      clearFieldErrors(form);

      var emailInput = $('email');
      var passwordInput = $('password');
      var email = emailInput.value.trim();
      var password = passwordInput.value;

      if (!emailInput.checkValidity() || !email) {
        setStatus(statusEl, 'Vui lòng nhập địa chỉ email hợp lệ.', 'error');
        markFieldError(emailInput);
        return;
      }
      if (!password) {
        setStatus(statusEl, 'Vui lòng nhập mật khẩu.', 'error');
        markFieldError(passwordInput);
        return;
      }

      setBusy(submit, true, 'Đang đăng nhập...', 'Đăng nhập');
      postJson('/api/v1/auth/login', { email: email, password: password })
        .then(function (result) {
          if (!result.res.ok) {
            setStatus(statusEl, describeError(result.res, result.body), 'error');
            return;
          }
          var token = result.body && result.body.data && result.body.data.access_token;
          if (!token) {
            setStatus(statusEl, 'Không nhận được phiên đăng nhập. Vui lòng thử lại.', 'error');
            return;
          }
          saveToken(token);
          setStatus(statusEl, 'Đăng nhập thành công. Đang chuyển trang...', 'ok');
          window.location.assign(nextTarget('/explore'));
        })
        .catch(function () {
          if (isDirectMode) {
            saveToken('demo_student_token');
            setStatus(statusEl, 'Chế độ xem trước (Offline): Tự động đăng nhập tài khoản mẫu...', 'ok');
            setTimeout(function () {
              window.location.assign(nextTarget('/explore'));
            }, 600);
            return;
          }
          setStatus(statusEl, 'Không thể kết nối máy chủ. Vui lòng kiểm tra mạng rồi thử lại.', 'error');
        })
        .then(function () {
          setBusy(submit, false, '', 'Đăng nhập');
        });
    });
  }

  function initRegister() {
    var form = $('registerForm');
    var statusEl = $('status');
    var submit = $('submitBtn');
    bindInputReset(form, statusEl);

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      setStatus(statusEl, '');
      clearFieldErrors(form);

      var emailInput = $('email');
      var passwordInput = $('password');
      var confirmInput = $('confirmPassword');
      var email = emailInput.value.trim();
      var password = passwordInput.value;
      var confirm = confirmInput.value;

      if (!emailInput.checkValidity() || !email) {
        setStatus(statusEl, 'Vui lòng nhập địa chỉ email hợp lệ.', 'error');
        markFieldError(emailInput);
        return;
      }
      if (password.length < 8) {
        setStatus(statusEl, 'Mật khẩu phải có ít nhất 8 ký tự.', 'error');
        markFieldError(passwordInput);
        return;
      }
      if (password.length > 72) {
        setStatus(statusEl, 'Mật khẩu không được vượt quá 72 ký tự.', 'error');
        markFieldError(passwordInput);
        return;
      }
      if (password !== confirm) {
        setStatus(statusEl, 'Mật khẩu nhập lại không khớp. Vui lòng kiểm tra lại.', 'error');
        markFieldError(confirmInput);
        return;
      }

      setBusy(submit, true, 'Đang tạo tài khoản...', 'Tạo tài khoản');
      postJson('/api/v1/auth/register', { email: email, password: password })
        .then(function (registered) {
          if (!registered.res.ok) {
            setStatus(statusEl, describeError(registered.res, registered.body), 'error');
            return null;
          }
          setStatus(statusEl, 'Đăng ký thành công. Đang đăng nhập...', 'ok');
          return postJson('/api/v1/auth/login', { email: email, password: password });
        })
        .then(function (login) {
          if (!login) return;
          if (!login.res.ok) {
            setStatus(statusEl, describeError(login.res, login.body) + ' Bạn có thể đăng nhập lại bằng biểu mẫu đăng nhập.', 'error');
            return;
          }
          var token = login.body && login.body.data && login.body.data.access_token;
          if (!token) {
            setStatus(statusEl, 'Chưa khởi tạo được phiên đăng nhập. Vui lòng đăng nhập lại.', 'error');
            return;
          }
          saveToken(token);
          window.location.assign(nextTarget('/profile'));
        })
        .catch(function () {
          setStatus(statusEl, 'Không thể kết nối máy chủ. Vui lòng kiểm tra mạng rồi thử lại.', 'error');
        })
        .then(function () {
          setBusy(submit, false, '', 'Tạo tài khoản');
        });
    });
  }

  bindPasswordToggles();
  syncSwitchLinks();

  if ($('loginForm')) {
    initLogin();
    redirectIfSignedIn('/explore');
  } else if ($('registerForm')) {
    initRegister();
    redirectIfSignedIn('/profile');
  }
})();
