function showRegister() {
            document.getElementById('login-form').classList.remove('active');
            document.getElementById('register-form').classList.add('active');
        }
        function showLogin() {
            document.getElementById('register-form').classList.remove('active');
            document.getElementById('login-form').classList.add('active');
        }

        function togglePassword(inputId, toggleBtn) {
            const passwordInput = document.getElementById(inputId);
            const eyeOpen = toggleBtn.querySelector('.eye-open');
            const eyeClosed = toggleBtn.querySelector('.eye-closed');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeOpen.style.display = 'none';
                eyeClosed.style.display = 'block';
            } else {
                passwordInput.type = 'password';
                eyeOpen.style.display = 'block';
                eyeClosed.style.display = 'none';
            }
        }

        function validatePasswordMatch() {
            const password = document.getElementById('reg-password').value;
            const confirmPassword = document.getElementById('reg-confirm-password').value;
            const messageDiv = document.getElementById('password-match-message');
            
            if (confirmPassword === '') {
                messageDiv.textContent = '';
                messageDiv.className = 'password-message';
                return true;
            }
            
            if (password === confirmPassword) {
                messageDiv.textContent = '✓ Passwords match';
                messageDiv.className = 'password-message success';
                return true;
            } else {
                messageDiv.textContent = '✗ Passwords do not match';
                messageDiv.className = 'password-message error';
                return false;
            }
        }

        // Add event listeners when page loads
        document.addEventListener('DOMContentLoaded', function() {
            const confirmPasswordInput = document.getElementById('reg-confirm-password');
            const passwordInput = document.getElementById('reg-password');
            
            if (confirmPasswordInput && passwordInput) {
                confirmPasswordInput.addEventListener('input', validatePasswordMatch);
                passwordInput.addEventListener('input', validatePasswordMatch);
            }
        });