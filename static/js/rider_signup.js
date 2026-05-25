// Client-side PSGC usage
const PSGC_BASE = 'https://psgc.gitlab.io/api';
const regionSelect = document.getElementById('region');
const provinceSelect = document.getElementById('province');
const citySelect = document.getElementById('city');
const barangaySelect = document.getElementById('barangay');

function setOptions(selectEl, items, defaultText = 'Select...') {
    selectEl.innerHTML = `<option value="">${defaultText}</option>`;
    items.forEach(item => {
        const option = document.createElement('option');
        option.value = item.code || item.id || item.value;
        option.text = item.name || item.title || item.label;
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
    if (!regionSelect) return;
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

if (regionSelect) {
    regionSelect.addEventListener('change', async function(){
        const regionCode = this.value;
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
}

if (provinceSelect) {
    provinceSelect.addEventListener('change', async function(){
        const provinceCode = this.value;
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
}

if (citySelect) {
    citySelect.addEventListener('change', async function(){
        const cityCode = this.value;
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
}

// File preview handlers
document.addEventListener('DOMContentLoaded', function(){
    const fileBtn = document.getElementById('btnDriverLicense');
    const fileInput = document.getElementById('driverlicense');
    const nameDisplay = document.getElementById('fileNameDisplay');

    if(fileBtn && fileInput) {
        fileBtn.addEventListener('click', function() {
            fileInput.click();
        });

        fileInput.addEventListener('change', function() {
            if (fileInput.files && fileInput.files[0]) {
                nameDisplay.textContent = fileInput.files[0].name;
            } else {
                nameDisplay.textContent = 'No file chosen';
            }
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
            if (step === 1 && input.id === 'confirmriderpass') {
                const pass = document.getElementById('riderpass').value;
                if (input.value !== pass) {
                    valid = false;
                    input.style.borderColor = '#ef4444';
                    alert('Passwords do not match');
                }
            }
        }
    });

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

function submitForm() {
    if (validateStep(3)) {
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
            return Array.from(inputs).every(i => i.value.trim());
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

// Expose functions to global scope
window.nextStep = nextStep;
window.prevStep = prevStep;
window.submitForm = submitForm;
