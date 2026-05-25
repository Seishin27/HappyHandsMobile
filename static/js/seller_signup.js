// Client-side PSGC usage (keeps everything inside this HTML file)
        const PSGC_BASE = 'https://psgc.gitlab.io/api';
        const regionSelect = document.getElementById('region');
        const provinceSelect = document.getElementById('province');
        const citySelect = document.getElementById('city');
        const barangaySelect = document.getElementById('barangay');

        function setOptions(selectEl, items, defaultText = 'Select...') {
            selectEl.innerHTML = `<option value="">${defaultText}</option>`;
            items.forEach(item => {
                const option = document.createElement('option');
                // Store the human-readable name as the value so the backend
                // receives names (matching what user_saved_addresses stores).
                option.value = item.name || item.title || item.label;
                option.text = item.name || item.title || item.label;
                // Keep the PSGC code as a data attribute for cascading lookups
                option.dataset.code = item.code || item.id || item.value;
                selectEl.appendChild(option);
            });
            selectEl.disabled = false;
        }

        function setLoading(selectEl, text) {
            selectEl.innerHTML = `<option value="">${text}</option>`;
            selectEl.disabled = true;
        }

        async function fetchJson(url) {
            const res = await fetch(url, {cache: 'no-store'});
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        }

        // Load regions
        (async function loadRegions(){
            try {
                setLoading(regionSelect, 'Loading regions...');
                const data = await fetchJson(`${PSGC_BASE}/regions/`);
                if (Array.isArray(data)) setOptions(regionSelect, data, 'Select region');
                else setLoading(regionSelect, 'No regions found');
            } catch (err) {
                console.error('Regions error', err);
                setLoading(regionSelect, 'Failed to load regions');
            }
        })();

        regionSelect.addEventListener('change', async function(){
            const selectedOption = this.options[this.selectedIndex];
            const regionCode = selectedOption ? (selectedOption.dataset.code || '') : '';
            setLoading(provinceSelect, 'Loading provinces...');
            citySelect.innerHTML = '<option value="">Select province first</option>'; citySelect.disabled = true;
            barangaySelect.innerHTML = '<option value="">Select city first</option>'; barangaySelect.disabled = true;

            if (!regionCode) {
                provinceSelect.innerHTML = '<option value="">Select region first</option>';
                provinceSelect.disabled = true;
                return;
            }
            try {
                const data = await fetchJson(`${PSGC_BASE}/regions/${encodeURIComponent(regionCode)}/provinces/`);
                if (Array.isArray(data)) setOptions(provinceSelect, data, 'Select province');
                else {
                    provinceSelect.innerHTML = '<option value="">No provinces found</option>';
                    provinceSelect.disabled = true;
                }
            } catch (err) {
                console.error('Provinces error', err);
                provinceSelect.innerHTML = '<option value="">Failed to load provinces</option>';
                provinceSelect.disabled = true;
            }
        });

        provinceSelect.addEventListener('change', async function(){
            const selectedOption = this.options[this.selectedIndex];
            const provinceCode = selectedOption ? (selectedOption.dataset.code || '') : '';
            setLoading(citySelect, 'Loading cities...');
            barangaySelect.innerHTML = '<option value="">Select city first</option>'; barangaySelect.disabled = true;

            if (!provinceCode) {
                citySelect.innerHTML = '<option value="">Select province first</option>';
                citySelect.disabled = true;
                return;
            }
            try {
                const data = await fetchJson(`${PSGC_BASE}/provinces/${encodeURIComponent(provinceCode)}/cities-municipalities/`);
                if (Array.isArray(data)) setOptions(citySelect, data, 'Select city');
                else {
                    citySelect.innerHTML = '<option value="">No cities found</option>';
                    citySelect.disabled = true;
                }
            } catch (err) {
                console.error('Cities error', err);
                citySelect.innerHTML = '<option value="">Failed to load cities</option>';
                citySelect.disabled = true;
            }
        });

        citySelect.addEventListener('change', async function(){
            const selectedOption = this.options[this.selectedIndex];
            const cityCode = selectedOption ? (selectedOption.dataset.code || '') : '';
            setLoading(barangaySelect, 'Loading barangays...');

            if (!cityCode) {
                barangaySelect.innerHTML = '<option value="">Select city first</option>';
                barangaySelect.disabled = true;
                return;
            }
            try {
                const data = await fetchJson(`${PSGC_BASE}/cities-municipalities/${encodeURIComponent(cityCode)}/barangays/`);
                if (Array.isArray(data)) setOptions(barangaySelect, data, 'Select barangay');
                else {
                    barangaySelect.innerHTML = '<option value="">No barangays found</option>';
                    barangaySelect.disabled = true;
                }
            } catch (err) {
                console.error('Barangays error', err);
                barangaySelect.innerHTML = '<option value="">Failed to load barangays</option>';
                barangaySelect.disabled = true;
            }
        });

        // File preview handlers for store logo and business permit
        document.addEventListener('DOMContentLoaded', function(){
            const logoInput = document.getElementById('storelogo');
            const logoPreview = document.getElementById('storelogo-preview');
            const permitInput = document.getElementById('businesspermit');
            const permitPreview = document.getElementById('permit-preview');
            const storeDesc = document.getElementById('storedesc');
            const contactNumberInput = document.getElementById('contactnumber');
            const passwordToggles = document.querySelectorAll('.password-toggle');
            const nextButtons = document.querySelectorAll('[data-next-step]');
            const backButtons = document.querySelectorAll('[data-prev-step]');
            const submitButtons = document.querySelectorAll('[data-submit-step]');
            const alertCloses = document.querySelectorAll('.alert-close');

            function updatePreview(inputEl, previewEl){
                if (!inputEl || !previewEl) return;
                const file = inputEl.files && inputEl.files[0];
                const img = previewEl.querySelector('img');
                const meta = previewEl.querySelector('.file-meta');
                if (!file) {
                    if (img) img.style.display = 'none';
                    if (meta) meta.textContent = 'No file chosen';
                    return;
                }
                const isImage = file.type.startsWith('image/');
                if (isImage) {
                    const reader = new FileReader();
                    reader.onload = function(e){
                        if (img) { img.src = e.target.result; img.style.display = ''; }
                    };
                    reader.readAsDataURL(file);
                    if (meta) meta.textContent = file.name;
                } else {
                    if (img) img.style.display = 'none';
                    if (meta) meta.textContent = file.name;
                }
            }

            if (logoInput) {
                logoInput.addEventListener('change', ()=> updatePreview(logoInput, logoPreview));
            }
            if (permitInput) {
                permitInput.addEventListener('change', ()=> updatePreview(permitInput, permitPreview));
            }

            // store description char count
            if (storeDesc) {
                const countEl = document.getElementById('storedesc-count');
                function updateCount(){
                    const len = storeDesc.value.length;
                    if (countEl) countEl.textContent = `${len} / 300`;
                }
                storeDesc.addEventListener('input', updateCount);
                updateCount();
            }

            if (contactNumberInput) {
                contactNumberInput.addEventListener('input', () => {
                    contactNumberInput.value = contactNumberInput.value.replace(/[^0-9]/g, '');
                });
            }

            if (passwordToggles.length) {
                passwordToggles.forEach(btn => {
                    btn.addEventListener('click', () => {
                        const targetId = btn.dataset.passwordTarget;
                        if (targetId) {
                            togglePassword(targetId, btn);
                        }
                    });
                });
            }

            if (nextButtons.length) {
                nextButtons.forEach(btn => {
                    btn.addEventListener('click', () => {
                        const step = Number(btn.dataset.nextStep);
                        if (step) {
                            nextStep(step);
                        }
                    });
                });
            }

            if (backButtons.length) {
                backButtons.forEach(btn => {
                    btn.addEventListener('click', () => {
                        const step = Number(btn.dataset.prevStep);
                        if (step) {
                            prevStep(step);
                        }
                    });
                });
            }

            if (submitButtons.length) {
                submitButtons.forEach(btn => {
                    btn.addEventListener('click', () => submitForm());
                });
            }

            if (alertCloses.length) {
                alertCloses.forEach(btn => {
                    btn.addEventListener('click', () => {
                        const alert = btn.closest('.signup-alert');
                        if (alert) {
                            alert.style.display = 'none';
                        }
                    });
                });
            }
        });

        // Multi-step form logic
        let currentStep = 1;
        const totalSteps = 3;

        function showStep(step) {
            // Hide all steps
            document.querySelectorAll('.form-step').forEach(el => el.classList.remove('active'));
            // Show current step
            document.getElementById(`step-${step}`).classList.add('active');
            
            // Update indicators
            document.querySelectorAll('.step').forEach((el, idx) => {
                const stepNum = idx + 1;
                el.classList.remove('active', 'completed');
                if (stepNum === step) {
                    el.classList.add('active');
                } else if (stepNum < step) {
                    el.classList.add('completed');
                }
            });
            
            currentStep = step;
            window.scrollTo(0, 0);
        }

        function validateStep(step) {
            const stepEl = document.getElementById(`step-${step}`);
            const inputs = stepEl.querySelectorAll('input[required], select[required], textarea[required]');
            let valid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    valid = false;
                    input.style.borderColor = '#ef4444';
                } else {
                    input.style.borderColor = '';
                    // Check password match on step 1
                    if (step === 1 && input.id === 'confirmpassword') {
                        const pass = document.getElementById('password').value;
                        if (input.value !== pass) {
                            valid = false;
                            input.style.borderColor = '#ef4444';
                            alert('Passwords do not match');
                        }
                    }
                }
            });

            // Custom validation for categories on step 2
            if (step === 2) {
                const categoryError = document.getElementById('category-error');
                const checkedCategories = document.querySelectorAll('input[name="seller_category_ids"]:checked');
                
                if (checkedCategories.length === 0) {
                    valid = false;
                    if (categoryError) categoryError.style.display = 'block';
                } else {
                    if (categoryError) categoryError.style.display = 'none';
                }
            }

            if (!valid) {
                alert('Please fill in all required fields correctly.');
            }
            return valid;
        }

        function nextStep(step) {
            if (validateStep(step)) {
                if (step < totalSteps) {
                    showStep(step + 1);
                }
            }
        }

        function prevStep(step) {
            if (step > 1) {
                showStep(step - 1);
            }
        }
        
        // Expose functions to global scope for onclick handlers
        window.nextStep = nextStep;
        window.prevStep = prevStep;

        function submitForm() {
            if (validateStep(3)) {
                // Validate previous steps to be safe
                // We can just submit if we trust the flow, but let's be safe.
                // However, validateStep alerts on failure, so it might be noisy if we check all.
                // Let's assume if they got to step 3, 1 and 2 are fine, unless they hacked the DOM.
                // But to be robust:
                
                // Check step 1
                const step1Valid = (() => {
                    const stepEl = document.getElementById('step-1');
                    const inputs = stepEl.querySelectorAll('input[required], select[required], textarea[required]');
                    return Array.from(inputs).every(i => i.value.trim());
                })();

                // Check step 2
                const step2Valid = (() => {
                    const stepEl = document.getElementById('step-2');
                    const inputs = stepEl.querySelectorAll('input[required], select[required], textarea[required]');
                    const basicValid = Array.from(inputs).every(i => i.value.trim());
                    
                    const checkedCategories = document.querySelectorAll('input[name="seller_category_ids"]:checked');
                    const categoryValid = checkedCategories.length > 0;
                    
                    return basicValid && categoryValid;
                })();

                if (step1Valid && step2Valid) {
                    document.getElementById('multiStepForm').submit();
                } else {
                    alert('Please ensure all steps are completed correctly.');
                    if (!step1Valid) showStep(1);
                    else if (!step2Valid) showStep(2);
                }
            }
        }
        window.submitForm = submitForm;

        function togglePassword(inputId, btn) {
            const input = document.getElementById(inputId);
            if (!input) return;

            const eyeOpen = btn.querySelector('.eye-open');
            const eyeClosed = btn.querySelector('.eye-closed');

            if (input.type === 'password') {
                input.type = 'text';
                if (eyeOpen) eyeOpen.style.display = 'none';
                if (eyeClosed) eyeClosed.style.display = 'block';
            } else {
                input.type = 'password';
                if (eyeOpen) eyeOpen.style.display = 'block';
                if (eyeClosed) eyeClosed.style.display = 'none';
            }
        }
