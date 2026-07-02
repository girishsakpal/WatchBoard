
(function () {
  const searchInput = document.getElementById('title-search');
  if (!searchInput) return; // not present on the edit form

  const statusEl = document.getElementById('search-status');
  const resultsEl = document.getElementById('search-results');
  let debounceTimer = null;

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.trim();
    clearTimeout(debounceTimer);
    if (!query) {
      resultsEl.hidden = true;
      resultsEl.innerHTML = '';
      statusEl.textContent = '';
      return;
    }
    statusEl.textContent = 'Searching…';
    debounceTimer = setTimeout(() => runSearch(query), 400);
  });

  async function runSearch(query) {
    try {
      const res = await fetch('/api/titles/search?q=' + encodeURIComponent(query));
      const data = await res.json();
      if (!res.ok) {
        statusEl.textContent = data.error || 'Search failed.';
        resultsEl.hidden = true;
        return;
      }
      renderResults(data.results || []);
      statusEl.textContent = '';
    } catch (err) {
      statusEl.textContent = 'Could not reach the title database right now.';
      resultsEl.hidden = true;
    }
  }

  function renderResults(results) {
    resultsEl.innerHTML = '';
    if (results.length === 0) {
      resultsEl.hidden = true;
      return;
    }
    results.forEach((r) => {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.type = 'button';

      const img = r.poster_url
        ? Object.assign(document.createElement('img'), { src: r.poster_url, alt: '' })
        : Object.assign(document.createElement('span'), { className: 'form-search__no-poster' });

      const info = document.createElement('span');
      const title = document.createElement('strong');
      title.textContent = r.title;
      const meta = document.createElement('span');
      meta.className = 'form-search__meta';
      meta.textContent = (r.media_type === 'tv' ? 'Series' : 'Film') + (r.year ? ' · ' + r.year : '');
      info.appendChild(title);
      info.appendChild(meta);

      btn.appendChild(img);
      btn.appendChild(info);
      btn.addEventListener('click', () => applyResult(r));

      li.appendChild(btn);
      resultsEl.appendChild(li);
    });
    resultsEl.hidden = false;
  }

  function applyResult(result) {
    document.getElementById('field-title').value = result.title || '';
    document.getElementById('field-year').value = result.year || '';
    document.getElementById('field-poster_url').value = result.poster_url || '';
    document.getElementById('field-overview').value = result.overview || '';
    document.getElementById('field-tmdb_id').value = result.tmdb_id || '';

    const mediaTypeSelect = document.getElementById('field-media_type');
    if (mediaTypeSelect.value !== 'anime') {
      mediaTypeSelect.value = result.media_type === 'tv' ? 'tv' : 'movie';
    }

    resultsEl.hidden = true;
    resultsEl.innerHTML = '';
    searchInput.value = '';
    statusEl.textContent = '';
  }
})();

(function () {
  const input = document.getElementById('field-poster_url');
  const preview = document.getElementById('poster-preview');
  const previewImg = document.getElementById('poster-preview-img');
  const previewStatus = document.getElementById('poster-preview-status');
  if (!input || !preview) return;

  let debounceTimer = null;

  function checkPoster() {
    const url = input.value.trim();
    if (!url) {
      preview.hidden = true;
      return;
    }
    preview.hidden = false;
    previewStatus.textContent = 'Loading preview…';
    previewStatus.classList.remove('poster-preview__status--error');
    previewImg.style.display = 'none';
    previewImg.src = url;
  }

  previewImg.addEventListener('load', () => {
    previewImg.style.display = 'block';
    previewStatus.textContent = '';
  });
  previewImg.addEventListener('error', () => {
    previewImg.style.display = 'none';
    previewStatus.textContent = "Couldn't load an image from that link, check it points straight to a .jpg/.png/.webp file, not a webpage.";
    previewStatus.classList.add('poster-preview__status--error');
  });

  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(checkPoster, 400);
  });

  // Show a preview immediately when editing an entry that already has one.
  if (input.value.trim()) checkPoster();
})();
