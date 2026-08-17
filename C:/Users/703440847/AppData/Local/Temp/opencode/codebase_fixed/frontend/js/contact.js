// SECURITY FIX [SEC-001]: Read reCAPTCHA site key from a server-rendered <meta> tag
// instead of hardcoding a placeholder. The key is injected at deploy time via envsubst.
// FIX [CQ-004]: Replaced all var declarations with const/let (ES6+).
const SITE_KEY = document.querySelector('meta[name="recaptcha-key"]')?.content || '';
if (!SITE_KEY) {
  console.warn('reCAPTCHA site key not configured. CAPTCHA will not function.');
}

document.addEventListener('DOMContentLoaded', function () {
  const form       = document.getElementById('contactForm');
  const submitBtn  = document.getElementById('submitBtn');
  const successMsg = document.getElementById('successMsg');
  const errorMsg   = document.getElementById('errorMsg');
  const textarea   = document.getElementById('message');
  const charCount  = document.getElementById('char-count');

  if (textarea && charCount) {
    textarea.addEventListener('input', function () {
      charCount.textContent = textarea.value.length + ' / 2000';
    });
  }

  if (!form) return;

  function showError(field, msg) {
    const el    = document.getElementById('error-' + field);
    const input = document.getElementById(field);
    if (el) el.textContent = msg;
    if (input) input.classList.add('invalid');
  }

  function clearError(field) {
    const el    = document.getElementById('error-' + field);
    const input = document.getElementById(field);
    if (el) el.textContent = '';
    if (input) input.classList.remove('invalid');
  }

  function validateForm() {
    let valid = true;
    ['full_name', 'email', 'phone', 'subject', 'message'].forEach(function (f) { clearError(f); });

    const name    = document.getElementById('full_name').value.trim();
    const email   = document.getElementById('email').value.trim();
    const phone   = document.getElementById('phone').value.trim();
    const subject = document.getElementById('subject').value.trim();
    const message = document.getElementById('message').value.trim();

    if (!name || name.length < 2)                                { showError('full_name', 'Full name is required (min 2 chars).'); valid = false; }
    if (!/^[a-zA-Z\s'\-]+$/.test(name))                         { showError('full_name', 'Name contains invalid characters.'); valid = false; }
    if (!email)                                                   { showError('email', 'Email address is required.'); valid = false; }
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))         { showError('email', 'Please enter a valid email address.'); valid = false; }
    if (phone && !/^[\+\d\s()\-]{7,20}$/.test(phone))           { showError('phone', 'Please enter a valid phone number.'); valid = false; }
    if (!subject || subject.length < 3)                          { showError('subject', 'Subject is required (min 3 chars).'); valid = false; }
    if (!message || message.length < 10)                         { showError('message', 'Message is required (min 10 chars).'); valid = false; }
    if (message.length > 2000)                                   { showError('message', 'Message must not exceed 2000 characters.'); valid = false; }
    return valid;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    successMsg.classList.add('hidden');
    errorMsg.classList.add('hidden');
    if (!validateForm()) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';

    function doSubmit(captchaToken) {
      const payload = {
        full_name:     document.getElementById('full_name').value.trim(),
        email:         document.getElementById('email').value.trim(),
        phone:         document.getElementById('phone').value.trim() || null,
        subject:       document.getElementById('subject').value.trim(),
        message:       document.getElementById('message').value.trim(),
        captcha_token: captchaToken,
      };

      fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then(function (resp) { return resp.json().then(function (data) { return { ok: resp.ok, data: data }; }); })
        .then(function (result) {
          if (result.ok && result.data.success) {
            form.reset();
            if (charCount) charCount.textContent = '0 / 2000';
            successMsg.classList.remove('hidden');
          } else {
            const msg = result.data.error || 'An error occurred. Please try again.';
            errorMsg.textContent = msg;
            errorMsg.classList.remove('hidden');
          }
        })
        .catch(function () {
          errorMsg.textContent = 'A network error occurred. Please check your connection.';
          errorMsg.classList.remove('hidden');
        })
        .finally(function () {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Send Message';
        });
    }

    if (typeof grecaptcha !== 'undefined' && SITE_KEY) {
      grecaptcha.ready(function () {
        grecaptcha.execute(SITE_KEY, { action: 'contact' }).then(doSubmit);
      });
    } else {
      doSubmit('');
    }
  });
});
