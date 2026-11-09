(() => {
  const products = window.PRODUCTS;
  const params = new URLSearchParams(location.search);
  const isDetail = document.body.dataset.page === 'detail';
  let current = products.find(product => product.id === params.get('product')) || products[0];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

  function buildModelPicker() {
    const picker = document.querySelector('#model-picker');
    picker.innerHTML = products.map(product => `<button class="model-option ${product.id === current.id ? 'is-active' : ''}" role="tab" aria-selected="${product.id === current.id}" data-model="${product.id}"><span class="model-option-type">${esc(product.tier.split(' · ')[0])}</span><b>${esc(product.name)}</b><span class="model-option-link">${isDetail ? 'View details' : 'Select model'} <span aria-hidden="true">→</span></span></button>`).join('');
    picker.querySelectorAll('[data-model]').forEach(button => button.addEventListener('click', () => {
      const product = products.find(item => item.id === button.dataset.model);
      if (isDetail) { location.search = `?product=${encodeURIComponent(product.id)}`; return; }
      current = product;
      buildModelPicker();
      renderProduct();
    }));
  }

  function renderProduct() {
    document.title = `${current.name} · Samsung Dotcom`;
    document.querySelector('#hero-tier').textContent = current.tier;
    document.querySelector('#hero-title').textContent = current.headline;
    document.querySelector('#hero-description').textContent = current.description;
    document.querySelector('#screen-model').textContent = current.name.replace('Galaxy ', '').toUpperCase();
    const modelNumber = products.findIndex(product => product.id === current.id) + 1;
    document.querySelector('#hero-number')?.replaceChildren(document.createTextNode(String(modelNumber).padStart(2, '0')));
    document.querySelector('#spec-display').textContent = current.display;
    document.querySelector('#spec-camera').textContent = current.camera;
    document.querySelector('#spec-battery').textContent = current.battery;
    document.querySelector('#spec-support').textContent = current.support;
    document.querySelector('#sticky-model').textContent = current.name;
    document.querySelector('#source-note').textContent = current.sources;
    const detailLink = document.querySelector('#detail-link');
    if (detailLink) detailLink.href = `project-detail.html?product=${encodeURIComponent(current.id)}`;
    buildFeatures();
    buildPersonas();
    buildFaqs();
    if (!isDetail) buildCompareSelectors();
  }

  function buildFeatures() {
    const grid = document.querySelector('#feature-grid');
    grid.innerHTML = current.trends.map((trend, index) => `<button class="feature-card ${index === 0 ? 'is-active' : ''}" id="feature-tab-${index}" role="tab" aria-selected="${index === 0}" data-trend="${index}"><span class="feature-index">0${index + 1} / 0${current.trends.length}</span><span class="feature-title">${esc(trend.title)}</span><span class="feature-label">${esc(trend.label)}</span><span class="feature-arrow" aria-hidden="true">↗</span></button>`).join('');
    grid.querySelectorAll('[data-trend]').forEach(button => button.addEventListener('click', () => showFeature(Number(button.dataset.trend))));
    showFeature(0);
  }

  function showFeature(index) {
    const trend = current.trends[index];
    document.querySelectorAll('[data-trend]').forEach(button => {
      const selected = Number(button.dataset.trend) === index;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-selected', String(selected));
    });
    document.querySelector('#feature-detail').innerHTML = `<div class="feature-detail-top"><span>${esc(trend.label)}</span><span>0${index + 1} / 0${current.trends.length}</span></div><h3>${esc(trend.title)}</h3><p class="signal-copy">${esc(trend.signal)}</p><div class="spec-highlight"><small>MAPPED PRODUCT DETAIL</small><p>${esc(trend.spec)}</p></div><div class="hook-highlight"><small>MARKETING HOOK · DRAFT</small><p>${esc(trend.hook)}</p></div>`;
  }

  function buildPersonas() {
    const tabs = document.querySelector('#persona-tabs');
    tabs.innerHTML = current.personas.map((persona, index) => `<button class="persona-tab ${index === 0 ? 'is-active' : ''}" id="persona-tab-${index}" role="tab" aria-selected="${index === 0}" data-persona="${index}">${esc(persona.name)}</button>`).join('');
    tabs.querySelectorAll('[data-persona]').forEach(button => button.addEventListener('click', () => showPersona(Number(button.dataset.persona))));
    showPersona(0);
  }

  function showPersona(index) {
    const persona = current.personas[index];
    document.querySelectorAll('[data-persona]').forEach(button => {
      const selected = Number(button.dataset.persona) === index;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-selected', String(selected));
    });
    document.querySelector('#persona-panel').innerHTML = `<div class="persona-copy"><p class="eyebrow">${esc(persona.name.toUpperCase())}</p><h3>${esc(persona.title)}</h3><p>${esc(persona.message)}</p><ul class="persona-specs">${persona.features.map(feature => `<li>${esc(feature)}</li>`).join('')}</ul></div><aside class="review-insight"><span class="insight-label">RESEARCH SIGNAL · PARAPHRASED</span><p>${esc(persona.insight)}</p><small>${esc(persona.attribution)}</small></aside>`;
  }

  function buildFaqs() {
    document.querySelector('#faq-list').innerHTML = current.faqs.map(faq => `<details class="faq-item"><summary>${esc(faq.q)}</summary><div class="faq-answer"><p>${esc(faq.a)}</p></div></details>`).join('');
  }

  function buildCompareSelectors() {
    const selector = document.querySelector('#compare-selectors');
    selector.innerHTML = products.map(product => `<label class="compare-choice"><input type="checkbox" value="${product.id}" checked><span><b>${esc(product.name)}</b><small>${esc(product.tier)}</small></span></label>`).join('');
    selector.querySelectorAll('input').forEach(input => input.addEventListener('change', buildCompareTable));
    buildCompareTable();
  }

  function buildCompareTable() {
    const selected = [...document.querySelectorAll('#compare-selectors input:checked')].map(input => products.find(product => product.id === input.value));
    const container = document.querySelector('#compare-table-wrap');
    if (!selected.length) { container.innerHTML = '<p class="compare-empty">Select a Galaxy model to see its details.</p>'; return; }
    const fields = [['Display', 'display'], ['Main camera', 'cameraSpec'], ['Battery', 'batterySpec'], ['Software support', 'supportSpec']];
    container.innerHTML = `<table class="compare-table"><thead><tr><th scope="col">SPECIFICATION</th>${selected.map(product => `<th scope="col">${esc(product.name)}</th>`).join('')}</tr></thead><tbody>${fields.map(([label, key]) => `<tr><th scope="row">${esc(label)}</th>${selected.map(product => `<td>${esc(product[key])}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }

  const menuToggle = document.querySelector('#menu-toggle');
  const nav = document.querySelector('#site-nav');
  menuToggle.addEventListener('click', () => {
    const isOpen = menuToggle.getAttribute('aria-expanded') === 'true';
    menuToggle.setAttribute('aria-expanded', String(!isOpen));
    menuToggle.setAttribute('aria-label', isOpen ? 'Open navigation' : 'Close navigation');
    nav.classList.toggle('is-open', !isOpen);
  });
  nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.setAttribute('aria-label', 'Open navigation');
    nav.classList.remove('is-open');
  }));

  buildModelPicker();
  renderProduct();
})();
