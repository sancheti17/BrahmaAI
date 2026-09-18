
const video = document.getElementById('video');
const empty = document.getElementById('empty');
const mainYoutube = document.getElementById('mainYoutube');
const layer = document.getElementById('youtubeLayer');
const frame = document.getElementById('youtubeFrame');
const adMessage = document.getElementById('adMessage');
let currentWeather = null;
let adMappings = {};
let mainMode = 'html5';
let mainYoutubePlayer = null;
let youtubeApiPromise = null;

const categories = {
  sunny: { weather:'Sunny / bright', product:'Sunscreen', icon:'☀️' },
  rain: { weather:'Rain or drizzle', product:'Umbrella', icon:'🌧️' },
  thunderstorm: { weather:'Thunderstorm', product:'Raincoat', icon:'⛈️' },
  partly_cloudy: { weather:'Partly cloudy', product:'Sunglasses', icon:'🌤️' },
  overcast: { weather:'Overcast', product:'Moisturizer', icon:'☁️' },
  fog: { weather:'Fog', product:'Headlights', icon:'🌫️' },
  very_hot: { weather:'Very hot (≥34°C, dry)', product:'Air conditioner', icon:'🔥' },
  cool: { weather:'Cool (≤18°C)', product:'Hot coffee', icon:'☕' }
};

function setStatus(id, text, kind='') {
  const el = document.getElementById(id);
  el.className = `status ${kind}`.trim();
  el.textContent = text;
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '00:00';
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return h ? `${h}:${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}` : `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
}

function updateTime() {
  let current = video.currentTime;
  let duration = video.duration;
  if (mainMode === 'youtube' && mainYoutubePlayer && typeof mainYoutubePlayer.getCurrentTime === 'function') {
    current = mainYoutubePlayer.getCurrentTime();
    duration = mainYoutubePlayer.getDuration();
  }
  document.getElementById('time').textContent = `${formatTime(current)} / ${formatTime(duration)}`;
}

function youtubeId(value) {
  const text = (value || '').trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(text)) return text;
  try {
    const url = new URL(text);
    const host = url.hostname.replace(/^www\./, '');
    if (host === 'youtu.be') return url.pathname.split('/').filter(Boolean)[0] || null;
    if (host.endsWith('youtube.com')) {
      if (url.searchParams.get('v')) return url.searchParams.get('v');
      const parts = url.pathname.split('/').filter(Boolean);
      const marker = parts.findIndex(p => ['embed','shorts','live'].includes(p));
      if (marker >= 0 && parts[marker + 1]) return parts[marker + 1];
    }
  } catch (_) {}
  return null;
}

function buildMappingEditor(defaults) {
  const saved = JSON.parse(localStorage.getItem('weatherAdMappings') || '{}');
  const nonEmptySaved = Object.fromEntries(Object.entries(saved).filter(([, value]) => String(value || '').trim()));
  adMappings = { ...defaults, ...nonEmptySaved };
  const container = document.getElementById('mapping');
  container.innerHTML = '';
  Object.entries(categories).forEach(([key, meta]) => {
    const row = document.createElement('div');
    row.className = 'map-row';
    row.innerHTML = `<label for="ad-${key}">${meta.icon} ${meta.weather}<small>${meta.product}</small></label><input id="ad-${key}" data-key="${key}" type="text" spellcheck="false" placeholder="YouTube URL or video ID">`;
    row.querySelector('input').value = adMappings[key] || '';
    container.appendChild(row);
  });
}

function saveMappings() {
  const next = {};
  let invalid = 0;
  document.querySelectorAll('#mapping input').forEach(input => {
    const value = input.value.trim();
    next[input.dataset.key] = value;
    input.style.borderColor = value && !youtubeId(value) ? 'var(--danger)' : '';
    if (value && !youtubeId(value)) invalid++;
  });
  if (invalid) return setStatus('mappingStatus', `${invalid} mapping(s) are not valid YouTube URLs or 11-character IDs.`, 'error');
  adMappings = next;
  localStorage.setItem('weatherAdMappings', JSON.stringify(next));
  setStatus('mappingStatus', 'YouTube mappings saved in this browser.', 'ok');
}

function ensureYouTubeApi() {
  if (window.YT && window.YT.Player) return Promise.resolve();
  if (youtubeApiPromise) return youtubeApiPromise;
  youtubeApiPromise = new Promise((resolve, reject) => {
    window.onYouTubeIframeAPIReady = resolve;
    const script = document.createElement('script');
    script.src = 'https://www.youtube.com/iframe_api';
    script.onerror = () => reject(new Error('Could not load the YouTube player API.'));
    document.head.appendChild(script);
  });
  return youtubeApiPromise;
}

function isYouTubeUrl(value) {
  try {
    const host = new URL(value).hostname.replace(/^www\./, '');
    return host === 'youtu.be' || host === 'youtube.com' || host.endsWith('.youtube.com');
  } catch (_) {
    return false;
  }
}

function showHtml5Video(source) {
  if (mainYoutubePlayer && typeof mainYoutubePlayer.destroy === 'function') mainYoutubePlayer.destroy();
  mainYoutubePlayer = null;
  mainYoutube.innerHTML = '<div id="mainYoutubePlayer"></div>';
  mainYoutube.hidden = true;
  mainMode = 'html5';
  video.src = source;
  video.hidden = false;
  empty.hidden = true;
  video.load();
  updateTime();
}

async function showMainYouTube(videoId) {
  await ensureYouTubeApi();
  video.pause();
  video.removeAttribute('src');
  video.load();
  video.hidden = true;
  empty.hidden = true;
  mainYoutube.hidden = false;
  mainMode = 'youtube';
  if (mainYoutubePlayer && typeof mainYoutubePlayer.destroy === 'function') mainYoutubePlayer.destroy();
  mainYoutube.innerHTML = '<div id="mainYoutubePlayer"></div>';
  await new Promise((resolve, reject) => {
    mainYoutubePlayer = new YT.Player('mainYoutubePlayer', {
      videoId,
      playerVars: { controls: 0, rel: 0, playsinline: 1, modestbranding: 1 },
      events: {
        onReady: resolve,
        onError: event => reject(new Error(`YouTube could not load this video (error ${event.data}).`)),
        onStateChange: event => {
          if (event.data === YT.PlayerState.ENDED) playWeatherAd();
          updateTime();
        }
      }
    });
  });
  updateTime();
}

async function loadConfig() {
  const response = await fetch('/config');
  const config = await response.json();
  buildMappingEditor(config.youtube_ads || {});
  if (config.video_source) {
    document.getElementById('videoPath').value = config.video_source;
    await loadVideo();
  }
}

async function loadVideo() {
  stopYouTube();
  const source = document.getElementById('videoPath').value.trim();
  if (!source) return setStatus('videoStatus', 'Enter a video URL or full local path first.', 'error');
  setStatus('videoStatus', 'Loading video…');
  try {
    if (/^https?:\/\//i.test(source)) {
      if (isYouTubeUrl(source)) {
        const id = youtubeId(source);
        if (!id) throw new Error('This is not a valid YouTube video URL.');
        await showMainYouTube(id);
        setStatus('videoStatus', `Loaded YouTube video: ${id}`, 'ok');
      } else {
        showHtml5Video(source);
        setStatus('videoStatus', 'Loaded direct video URL. The host must allow browser playback and byte-range requests.', 'ok');
      }
      return;
    }

    const response = await fetch(`/set-video?path=${encodeURIComponent(source)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not load video.');
    showHtml5Video(`/video?version=${Date.now()}`);
    setStatus('videoStatus', `Loaded local file: ${data.path}\n${(data.size / 1048576).toFixed(1)} MB`, 'ok');
  } catch (error) {
    setStatus('videoStatus', error.message, 'error');
  }
}

async function checkWeather() {
  setStatus('weatherStatus', 'Checking Bengaluru weather…');
  try {
    const response = await fetch(`/weather?ts=${Date.now()}`, { cache:'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Weather request failed.');
    currentWeather = data;
    const meta = categories[data.category];
    document.getElementById('weatherIcon').textContent = meta.icon;
    document.getElementById('weatherTitle').textContent = `${data.temperature_c.toFixed(1)}°C · ${meta.weather}`;
    document.getElementById('weatherDetail').textContent = `Post-credit product: ${meta.product}`;
    setStatus('weatherStatus', `${data.description}; precipitation ${data.precipitation_mm} mm. Checked ${data.time}.`, 'ok');
    return data;
  } catch (error) {
    setStatus('weatherStatus', error.message, 'error');
    throw error;
  }
}

function stopYouTube() {
  frame.src = 'about:blank';
  layer.classList.remove('show');
  adMessage.hidden = true;
}

async function playWeatherAd() {
  try {
    const weather = await checkWeather();
    const meta = categories[weather.category];
    const configured = adMappings[weather.category] || '';
    const id = youtubeId(configured);
    layer.classList.add('show');
    if (!id) {
      frame.src = 'about:blank';
      adMessage.hidden = false;
      document.getElementById('adIcon').textContent = meta.icon;
      document.getElementById('adTitle').textContent = `${meta.product} ad selected`;
      document.getElementById('adText').textContent = `Bengaluru is ${meta.weather.toLowerCase()}, but no valid YouTube video is configured for this category. Paste its URL in YouTube ad mapping.`;
      return;
    }
    adMessage.hidden = true;
    frame.src = `https://www.youtube.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0&playsinline=1`;
  } catch (_) {
    layer.classList.add('show');
    frame.src = 'about:blank';
    adMessage.hidden = false;
    document.getElementById('adIcon').textContent = '⚠️';
    document.getElementById('adTitle').textContent = 'Weather unavailable';
    document.getElementById('adText').textContent = 'The YouTube ad was not selected because current Bengaluru weather could not be retrieved.';
  }
}

function playMainVideo() {
  stopYouTube();
  if (mainMode === 'youtube' && mainYoutubePlayer) mainYoutubePlayer.playVideo();
  else video.play().catch(err => setStatus('videoStatus', err.message, 'error'));
}

function pauseMainVideo() {
  if (mainMode === 'youtube' && mainYoutubePlayer) mainYoutubePlayer.pauseVideo();
  else video.pause();
}

function seekMainVideo(delta) {
  if (mainMode === 'youtube' && mainYoutubePlayer) {
    const target = Math.max(0, Math.min(mainYoutubePlayer.getDuration() || Infinity, mainYoutubePlayer.getCurrentTime() + delta));
    mainYoutubePlayer.seekTo(target, true);
  } else {
    video.currentTime = Math.max(0, Math.min(video.duration || Infinity, video.currentTime + delta));
  }
  updateTime();
}

function restartMainVideo() {
  stopYouTube();
  if (mainMode === 'youtube' && mainYoutubePlayer) {
    mainYoutubePlayer.seekTo(0, true);
    mainYoutubePlayer.playVideo();
  } else {
    video.currentTime = 0;
    video.play().catch(() => {});
  }
}

document.getElementById('loadVideo').addEventListener('click', loadVideo);
document.getElementById('videoPath').addEventListener('keydown', e => { if (e.key === 'Enter') loadVideo(); });
document.getElementById('checkWeather').addEventListener('click', () => checkWeather().catch(() => {}));
document.getElementById('saveAds').addEventListener('click', saveMappings);
document.getElementById('returnVideo').addEventListener('click', stopYouTube);
document.getElementById('togglePanel').addEventListener('click', event => {
  const layout = document.getElementById('layout');
  const hidden = layout.classList.toggle('panel-hidden');
  event.currentTarget.textContent = hidden ? 'Show settings' : 'Hide settings';
  event.currentTarget.setAttribute('aria-expanded', String(!hidden));
});

document.getElementById('play').addEventListener('click', playMainVideo);
document.getElementById('pause').addEventListener('click', pauseMainVideo);
document.getElementById('back').addEventListener('click', () => seekMainVideo(-10));
document.getElementById('forward').addEventListener('click', () => seekMainVideo(10));
document.getElementById('restart').addEventListener('click', restartMainVideo);
document.getElementById('speed').addEventListener('change', e => {
  const rate = Number(e.target.value);
  video.playbackRate = rate;
  if (mainMode === 'youtube' && mainYoutubePlayer) mainYoutubePlayer.setPlaybackRate(rate);
});
video.addEventListener('timeupdate', updateTime);
video.addEventListener('loadedmetadata', updateTime);
video.addEventListener('ended', playWeatherAd);
video.addEventListener('error', () => setStatus('videoStatus', 'The browser could not play this source. Use a YouTube URL or a direct MP4/H.264 or WebM URL.', 'error'));
setInterval(updateTime, 500);

setInterval(() => {
  document.getElementById('clock').textContent = new Intl.DateTimeFormat('en-IN', { dateStyle:'medium', timeStyle:'medium', timeZone:'Asia/Kolkata' }).format(new Date());
}, 1000);

loadConfig().then(() => checkWeather().catch(() => {})).catch(error => setStatus('videoStatus', error.message, 'error'));
