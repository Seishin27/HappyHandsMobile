const PSGC_BASE = 'https://psgc.gitlab.io/api';

const regRegion = document.getElementById('reg-region');
const regProvince = document.getElementById('reg-province');
const regCity = document.getElementById('reg-city');
const regBarangay = document.getElementById('reg-barangay');

function setGeoOptions(selectEl, items, defaultText) {
    selectEl.innerHTML = `<option value="" disabled selected>${defaultText}</option>`;
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.name || item.title || item.label;
        opt.text  = item.name || item.title || item.label;
        opt.dataset.code = item.code || item.id || item.value;
        selectEl.appendChild(opt);
    });
    selectEl.disabled = false;
}

function setGeoLoading(selectEl, text) {
    selectEl.innerHTML = `<option value="">${text}</option>`;
    selectEl.disabled = true;
}

async function fetchGeoJson(url) {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// Load regions on page ready
(async function loadRegions() {
    try {
        setGeoLoading(regRegion, 'Loading regions...');
        const data = await fetchGeoJson(`${PSGC_BASE}/regions/`);
        if (Array.isArray(data)) setGeoOptions(regRegion, data, 'Select region');
        else setGeoLoading(regRegion, 'Failed to load regions');
    } catch (err) {
        console.error('PSGC regions error', err);
        setGeoLoading(regRegion, 'Failed to load regions');
    }
})();

regRegion.addEventListener('change', async function () {
    const code = this.options[this.selectedIndex]?.dataset?.code || '';
    setGeoLoading(regProvince, 'Loading provinces...');
    setGeoLoading(regCity, 'Select province first');
    setGeoLoading(regBarangay, 'Select city first');
    if (!code) { setGeoLoading(regProvince, 'Select region first'); return; }
    try {
        const data = await fetchGeoJson(`${PSGC_BASE}/regions/${encodeURIComponent(code)}/provinces/`);
        if (Array.isArray(data) && data.length) setGeoOptions(regProvince, data, 'Select province');
        else setGeoLoading(regProvince, 'No provinces found');
    } catch (err) {
        console.error('PSGC provinces error', err);
        setGeoLoading(regProvince, 'Failed to load provinces');
    }
});

regProvince.addEventListener('change', async function () {
    const code = this.options[this.selectedIndex]?.dataset?.code || '';
    setGeoLoading(regCity, 'Loading cities...');
    setGeoLoading(regBarangay, 'Select city first');
    if (!code) { setGeoLoading(regCity, 'Select province first'); return; }
    try {
        const data = await fetchGeoJson(`${PSGC_BASE}/provinces/${encodeURIComponent(code)}/cities-municipalities/`);
        if (Array.isArray(data) && data.length) setGeoOptions(regCity, data, 'Select city');
        else setGeoLoading(regCity, 'No cities found');
    } catch (err) {
        console.error('PSGC cities error', err);
        setGeoLoading(regCity, 'Failed to load cities');
    }
});

regCity.addEventListener('change', async function () {
    const code = this.options[this.selectedIndex]?.dataset?.code || '';
    setGeoLoading(regBarangay, 'Loading barangays...');
    if (!code) { setGeoLoading(regBarangay, 'Select city first'); return; }
    try {
        const data = await fetchGeoJson(`${PSGC_BASE}/cities-municipalities/${encodeURIComponent(code)}/barangays/`);
        if (Array.isArray(data) && data.length) setGeoOptions(regBarangay, data, 'Select barangay');
        else setGeoLoading(regBarangay, 'No barangays found');
    } catch (err) {
        console.error('PSGC barangays error', err);
        setGeoLoading(regBarangay, 'Failed to load barangays');
    }
});
