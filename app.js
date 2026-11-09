(() => {
  const STORAGE_KEY = 'samsungProductResearch.v1';
  const emptyData = { profiles: [], mappings: [] };
  let data = loadData();
  const $ = (selector) => document.querySelector(selector);
  const esc = (value = '') => String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
  const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  function loadData() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (parsed && Array.isArray(parsed.profiles) && Array.isArray(parsed.mappings)) return parsed;
    } catch (error) { console.warn('Could not read saved research data.', error); }
    return structuredClone(emptyData);
  }

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    $('#save-status').textContent = 'Saved on this device';
    render();
  }

  function toast(message) {
    const element = $('#toast');
    element.textContent = message;
    element.classList.add('show');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => element.classList.remove('show'), 2400);
  }

  function downloadFile(filename, contents, type) {
    const url = URL.createObjectURL(new Blob([contents], { type }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function setEmpty(container, icon, title, detail) {
    container.innerHTML = `<div class="empty-state"><span class="empty-icon">${icon}</span><b>${title}</b><span>${detail}</span></div>`;
  }

  function renderProfiles() {
    const list = $('#profile-list');
    const select = $('#profile-select');
    if (!data.profiles.length) setEmpty(list, '◎', 'Your profile evidence will appear here.', 'Start with one clearly defined customer segment.');
    else list.innerHTML = data.profiles.map((profile) => `<article class="data-card"><button class="delete-item" data-delete-profile="${esc(profile.id)}" aria-label="Delete ${esc(profile.name)}">Delete ×</button><div class="card-topline"><span class="pill">CUSTOMER PROFILE</span></div><h4>${esc(profile.name)}</h4>${profile.source ? `<p><b>SOURCE</b> · ${esc(profile.source)}</p>` : ''}<p><b>USE CASE</b><br>${esc(profile.useCase)}</p><p><b>PAIN POINT</b><br>${esc(profile.painPoint)}</p><p><b>WILLINGNESS TO PAY</b><br>${esc(profile.willingness)}</p>${profile.confidence ? `<p><b>EVIDENCE / CONFIDENCE</b><br>${esc(profile.confidence)}</p>` : ''}${profile.needs ? `<p><b>ADDITIONAL FACTORS</b><br>${esc(profile.needs)}</p>` : ''}</article>`).join('');
    $('#profile-subtitle').textContent = `${data.profiles.length} ${data.profiles.length === 1 ? 'profile' : 'profiles'}`;
    select.innerHTML = '<option value="">Select a saved profile (optional)</option>' + data.profiles.map((profile) => `<option value="${esc(profile.id)}">${esc(profile.name)}</option>`).join('');
  }

  function renderMappings() {
    const list = $('#trend-list');
    if (!data.mappings.length) setEmpty(list, '↗', 'No trend claims have been entered.', 'Add a dated source and an exact product specification to begin.');
    else list.innerHTML = data.mappings.map((mapping) => {
      const profile = data.profiles.find((item) => item.id === mapping.profileId);
      const reviewClass = mapping.review === 'Approved for page' ? 'review-approved' : 'review-pill';
      return `<article class="data-card trend-card"><button class="delete-item" data-delete-mapping="${esc(mapping.id)}" aria-label="Delete mapping">Delete ×</button><div class="card-topline"><span class="pill">${esc(mapping.category)}</span><span class="card-date">${esc(mapping.date)}</span></div><h4>${esc(mapping.trend)}</h4><p><b>TREND SOURCE</b> · ${esc(mapping.source)}</p><p><b>EVIDENCE</b><br>${esc(mapping.evidence)}</p><p><b>PRODUCT SPEC</b> · ${esc(mapping.spec)}<br><b>SPEC SOURCE</b> · ${esc(mapping.specSource)}</p><p><b>CUSTOMER BENEFIT</b><br>${esc(mapping.benefit)}${profile ? `<br><b>PROFILE</b> · ${esc(profile.name)}` : ''}</p><div class="hook-box"><span>MARKETING HOOK · REVIEW REQUIRED</span><p>${esc(mapping.hook)}</p></div><div class="card-topline" style="margin:12px 0 0"><span class="pill ${reviewClass}">${esc(mapping.review)}</span></div></article>`;
    }).join('');
    $('#trend-subtitle').textContent = `${data.mappings.length} ${data.mappings.length === 1 ? 'mapping' : 'mappings'}`;
  }

  function render() {
    renderProfiles();
    renderMappings();
    $('#profile-count').textContent = data.profiles.length;
    $('#trend-count').textContent = data.mappings.length;
    $('#mapping-count').textContent = data.mappings.length;
    $('#hook-count').textContent = data.mappings.filter((mapping) => mapping.hook.trim()).length;
  }

  $('#customer-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const fields = Object.fromEntries(new FormData(event.currentTarget).entries());
    data.profiles.unshift({ id: makeId(), ...fields });
    event.currentTarget.reset();
    persist();
    toast('Customer profile saved.');
  });

  $('#trend-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const fields = Object.fromEntries(new FormData(event.currentTarget).entries());
    const hook = fields.hook.trim() || `${fields.trend} matters to customers who ${fields.benefit.replace(/[.\s]+$/, '')}. ${fields.spec}.`;
    data.mappings.unshift({ id: makeId(), ...fields, hook });
    event.currentTarget.reset();
    persist();
    toast('Trend mapping saved as a draft.');
  });

  document.addEventListener('click', (event) => {
    const profileId = event.target.dataset.deleteProfile;
    const mappingId = event.target.dataset.deleteMapping;
    if (profileId) {
      data.profiles = data.profiles.filter((item) => item.id !== profileId);
      data.mappings = data.mappings.map((item) => item.profileId === profileId ? { ...item, profileId: '' } : item);
      persist(); toast('Customer profile deleted.');
    }
    if (mappingId) {
      data.mappings = data.mappings.filter((item) => item.id !== mappingId);
      persist(); toast('Trend mapping deleted.');
    }
    const scrollTarget = event.target.dataset.scroll;
    if (scrollTarget) document.getElementById(scrollTarget).scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  $('#export-button').addEventListener('click', () => {
    downloadFile('product-audience-trend-research.json', JSON.stringify({ exportedAt: new Date().toISOString(), ...data }, null, 2), 'application/json');
    toast('Research data exported.');
  });

  $('#export-csv-button').addEventListener('click', () => {
    const columns = ['record_type', 'id', 'name', 'source', 'use_case', 'pain_point', 'willingness_to_pay', 'confidence_or_evidence', 'additional_needs', 'trend', 'category', 'trend_source_url', 'published_or_observed_date', 'trend_evidence_summary', 'product_specification', 'specification_source', 'customer_benefit', 'related_profile', 'claim_review_status', 'marketing_hook_draft'];
    const rows = [
      ...data.profiles.map((profile) => ({ record_type: 'customer_profile', id: profile.id, name: profile.name, source: profile.source, use_case: profile.useCase, pain_point: profile.painPoint, willingness_to_pay: profile.willingness, confidence_or_evidence: profile.confidence, additional_needs: profile.needs })),
      ...data.mappings.map((mapping) => ({ record_type: 'trend_mapping', id: mapping.id, source: mapping.source, trend: mapping.trend, category: mapping.category, trend_source_url: mapping.source, published_or_observed_date: mapping.date, trend_evidence_summary: mapping.evidence, product_specification: mapping.spec, specification_source: mapping.specSource, customer_benefit: mapping.benefit, related_profile: data.profiles.find((profile) => profile.id === mapping.profileId)?.name || '', claim_review_status: mapping.review, marketing_hook_draft: mapping.hook }))
    ];
    const csvCell = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
    const csv = [columns.join(','), ...rows.map((row) => columns.map((column) => csvCell(row[column])).join(','))].join('\r\n');
    downloadFile('product-audience-trend-research.csv', `\ufeff${csv}`, 'text/csv;charset=utf-8');
    toast('Research CSV exported.');
  });

  $('#clear-button').addEventListener('click', () => {
    if (!data.profiles.length && !data.mappings.length) return toast('There is no saved data to clear.');
    if (!window.confirm('Delete all customer profiles and trend mappings saved in this browser? This cannot be undone.')) return;
    data = structuredClone(emptyData);
    persist();
    toast('All local research data cleared.');
  });

  render();
})();
