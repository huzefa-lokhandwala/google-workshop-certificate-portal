document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const form = document.getElementById('certificateForm');
  const fullNameInput = document.getElementById('fullName');
  const emailInput = document.getElementById('emailAddress');
  const verifyBtn = document.getElementById('verifyBtn');
  const generateBtn = document.getElementById('generateBtn');
  const statusBanner = document.getElementById('statusBanner');
  const statusMessage = document.getElementById('statusMessage');
  const successPanel = document.getElementById('successPanel');
  const downloadLink = document.getElementById('downloadLink');
  const resetBtn = document.getElementById('resetBtn');

  let isEmailVerified = false;
  let verifiedEmailAddress = '';
  let generatedPdfBlobUrl = null;

  // Email format validator
  function isValidEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email.trim());
  }

  // Show status banner with specific type
  function showStatus(message, type = 'info') {
    statusBanner.className = `status-banner ${type}`;
    statusMessage.textContent = message;
    statusBanner.classList.remove('hidden');
  }

  function hideStatus() {
    statusBanner.className = 'status-banner hidden';
    statusMessage.textContent = '';
  }

  // Reset verification state when email input changes
  emailInput.addEventListener('input', () => {
    if (isEmailVerified && emailInput.value.trim().toLowerCase() !== verifiedEmailAddress) {
      isEmailVerified = false;
      generateBtn.disabled = true;
      hideStatus();
    }
  });

  // Verify Email Action (Using clean relative URL)
  verifyBtn.addEventListener('click', async () => {
    const email = emailInput.value.trim().toLowerCase();

    if (!email) {
      showStatus('Please enter your email address.', 'warning');
      emailInput.focus();
      return;
    }

    if (!isValidEmail(email)) {
      showStatus('Please enter a valid email address.', 'warning');
      emailInput.focus();
      return;
    }

    // Set loading state
    verifyBtn.disabled = true;
    verifyBtn.classList.add('loading');
    hideStatus();

    try {
      const response = await fetch('/api/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email }),
      });

      if (response.status === 429) {
        showStatus('Too many verification attempts. Please wait a minute before trying again.', 'warning');
        return;
      }

      const data = await response.json();

      if (response.ok && data.eligible) {
        isEmailVerified = true;
        verifiedEmailAddress = email;
        generateBtn.disabled = false;
        showStatus('✓ Email eligibility verified', 'success');

        if (!fullNameInput.value.trim()) {
          fullNameInput.focus();
        }
      } else {
        isEmailVerified = false;
        generateBtn.disabled = true;
        showStatus(data.message || 'This email address is not eligible for a certificate.', 'error');
      }
    } catch (err) {
      showStatus('Unable to verify email at this moment. Please check your connection and try again.', 'error');
    } finally {
      verifyBtn.disabled = false;
      verifyBtn.classList.remove('loading');
    }
  });

  // Generate Certificate Submit Action (Using clean relative URL)
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = fullNameInput.value.trim();
    const email = emailInput.value.trim().toLowerCase();

    if (!name || name.length < 2) {
      showStatus('Please enter your full name (minimum 2 characters).', 'warning');
      fullNameInput.focus();
      return;
    }

    if (!email || !isValidEmail(email)) {
      showStatus('Please enter a valid email address.', 'warning');
      emailInput.focus();
      return;
    }

    // Set generating loading state
    generateBtn.disabled = true;
    generateBtn.classList.add('loading');
    verifyBtn.disabled = true;
    hideStatus();

    try {
      const response = await fetch('/api/certificates/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: name, email: email }),
      });

      if (!response.ok) {
        let errorMessage = 'Something went wrong while generating your certificate. Please try again.';
        try {
          const errData = await response.json();
          if (errData && errData.detail) {
            errorMessage = Array.isArray(errData.detail)
              ? errData.detail.map(d => d.msg || d).join(', ')
              : errData.detail;
          }
        } catch (_) {}

        if (response.status === 409) {
          showStatus(errorMessage, 'warning');
        } else if (response.status === 403) {
          showStatus('This email address is not eligible for a certificate.', 'error');
        } else if (response.status === 429) {
          showStatus('Too many requests. Please wait a moment before trying again.', 'warning');
        } else {
          showStatus(errorMessage, 'error');
        }
        return;
      }

      // Successful PDF generation
      const blob = await response.blob();
      
      // Cleanup previous blob URL if any
      if (generatedPdfBlobUrl) {
        URL.revokeObjectURL(generatedPdfBlobUrl);
      }
      generatedPdfBlobUrl = URL.createObjectURL(blob);

      // Determine download filename from Content-Disposition header if available
      let filename = `Certificate_${name.replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '_')}.pdf`;
      const disposition = response.headers.get('Content-Disposition');
      if (disposition && disposition.includes('filename=')) {
        const match = disposition.match(/filename="?([^";]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      // Configure download anchor
      downloadLink.href = generatedPdfBlobUrl;
      downloadLink.download = filename;

      // Trigger automatic download
      const tempLink = document.createElement('a');
      tempLink.href = generatedPdfBlobUrl;
      tempLink.download = filename;
      document.body.appendChild(tempLink);
      tempLink.click();
      document.body.removeChild(tempLink);

      // Switch to success view
      form.classList.add('hidden');
      successPanel.classList.remove('hidden');

    } catch (err) {
      showStatus('Something went wrong while generating your certificate. Please try again.', 'error');
    } finally {
      generateBtn.classList.remove('loading');
      if (isEmailVerified) {
        generateBtn.disabled = false;
      }
      verifyBtn.disabled = false;
    }
  });

  // Reset / Generate Another Action
  resetBtn.addEventListener('click', () => {
    form.reset();
    isEmailVerified = false;
    verifiedEmailAddress = '';
    generateBtn.disabled = true;
    hideStatus();
    successPanel.classList.add('hidden');
    form.classList.remove('hidden');
    fullNameInput.focus();
  });
});
