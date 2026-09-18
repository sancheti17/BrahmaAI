#!/usr/bin/env python3
"""
Weather-aware video player for Bengaluru.

Run:
    python weather_youtube_player.py

Optional: provide a local path, direct MP4/WebM URL, or YouTube URL:
    python weather_youtube_player.py "D:\\Brahma_AI\\movie.mp4"
    python weather_youtube_player.py "https://example.com/movie.mp4"
    python weather_youtube_player.py "https://www.youtube.com/watch?v=VIDEO_ID"

The app opens at http://127.0.0.1:8765 and only listens on this computer.
It supports local files, direct browser-playable video URLs, and YouTube URLs.
The supplied weather-based YouTube advertisements are configured by default;
browser edits to those mappings are saved in localStorage.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HOST = "127.0.0.1"
PORT = 8765
BENGALURU_LATITUDE = 12.9716
BENGALURU_LONGITUDE = 77.5946

# An 11-character YouTube video ID or a full YouTube URL is accepted.
DEFAULT_YOUTUBE_ADS = {
    "sunny": "https://www.youtube.com/watch?v=r1ir5gcue4M",          # Sunscreen
    "rain": "https://www.youtube.com/watch?v=l0TbsIz3PJI",           # Umbrella
    "thunderstorm": "https://www.youtube.com/watch?v=A25J5xT74sY",   # Raincoat
    "partly_cloudy": "https://www.youtube.com/watch?v=nrOX6ackB14",  # Sunglasses
    "overcast": "https://www.youtube.com/watch?v=h0n8ThYTulY",       # Moisturizer
    "fog": "https://www.youtube.com/watch?v=jlkS-tPqFPU",            # Headlights
    "very_hot": "https://www.youtube.com/watch?v=uCphB_FzX7c",       # Air conditioner
    "cool": "https://www.youtube.com/watch?v=Y-jNMHruAts",           # Hot coffee
}

VIDEO_PATH: Path | None = None
INITIAL_VIDEO_SOURCE = ""
VIDEO_LOCK = threading.Lock()

WEATHER_META = {
    "sunny": {"weather": "Sunny / bright", "product": "Sunscreen", "icon": "☀️"},
    "rain": {"weather": "Rain or drizzle", "product": "Umbrella", "icon": "🌧️"},
    "thunderstorm": {"weather": "Thunderstorm", "product": "Raincoat", "icon": "⛈️"},
    "partly_cloudy": {"weather": "Partly cloudy", "product": "Sunglasses", "icon": "🌤️"},
    "overcast": {"weather": "Overcast", "product": "Moisturizer", "icon": "☁️"},
    "fog": {"weather": "Fog", "product": "Headlights", "icon": "🌫️"},
    "very_hot": {"weather": "Very hot (≥34°C, dry)", "product": "Air conditioner", "icon": "🔥"},
    "cool": {"weather": "Cool (≤18°C)", "product": "Hot coffee", "icon": "☕"},
}

HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>Bengaluru Weather Post-Credit Player</title>
  <style>
    :root {
      --bg:#0d1218; --panel:#151d27; --panel2:#1b2633; --text:#f4f7fb;
      --muted:#9eacbd; --line:#2a394b; --accent:#55d6a9; --accent2:#ffd166;
      --danger:#ff7676; --shadow:0 22px 60px rgba(0,0,0,.35);
    }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--text); background:
      radial-gradient(circle at 15% 0%,#193343 0,transparent 34%),
      radial-gradient(circle at 100% 15%,#2a2238 0,transparent 30%),var(--bg);
      font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
    button,input,select { font:inherit; }
    button { cursor:pointer; }
    .app { max-width:1450px; margin:auto; padding:24px; }
    header { display:flex; justify-content:space-between; align-items:flex-end; gap:20px; margin-bottom:20px; }
    h1 { margin:0; font-size:clamp(25px,4vw,44px); letter-spacing:-1.5px; }
    header p { margin:6px 0 0; color:var(--muted); }
    .header-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; align-items:center; gap:9px; }
    .live { padding:8px 12px; border:1px solid var(--line); border-radius:99px; color:var(--accent); background:rgba(85,214,169,.08); white-space:nowrap; }
    .panel-toggle { min-height:38px; padding:8px 12px; border:1px solid var(--line); border-radius:99px; color:var(--text); background:var(--panel2); }
    .panel-toggle:hover { border-color:var(--accent); }
    .layout { display:grid; grid-template-columns:minmax(0,1.7fr) minmax(340px,.8fr); gap:20px; align-items:start; }
    .layout.panel-hidden { grid-template-columns:minmax(0,1fr); }
    .layout.panel-hidden .sidebar { display:none; }
    .card { background:rgba(21,29,39,.92); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow); }
    .viewer { padding:14px; }
    .stage { position:relative; aspect-ratio:16/9; background:#05080c; border-radius:12px; overflow:hidden; display:grid; place-items:center; }
    video { width:100%; height:100%; object-fit:contain; background:#000; }
    .main-youtube { position:absolute; inset:0; background:#000; }
    .main-youtube[hidden] { display:none; }
    .main-youtube iframe { width:100%; height:100%; border:0; }
    .empty { padding:40px; text-align:center; color:var(--muted); }
    .empty strong { display:block; color:var(--text); font-size:24px; margin-bottom:8px; }
    .youtube-layer { position:absolute; inset:0; display:none; background:#05080c; }
    .youtube-layer.show { display:block; }
    .youtube-layer iframe { width:100%; height:100%; border:0; }
    .ad-message { position:absolute; inset:0; display:grid; place-items:center; padding:30px; text-align:center; background:linear-gradient(135deg,#172431,#24384b); }
    .ad-message[hidden] { display:none; }
    .ad-message h2 { margin:8px 0; font-size:clamp(28px,5vw,55px); }
    .ad-message p { color:var(--muted); max-width:600px; }
    .toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; padding:14px 2px 2px; }
    .toolbar button,.toolbar select { border:1px solid var(--line); border-radius:9px; color:var(--text); background:var(--panel2); min-height:42px; padding:9px 13px; }
    .toolbar button:hover { border-color:var(--accent); }
    .toolbar .primary { color:#07130f; background:var(--accent); border-color:var(--accent); font-weight:750; }
    .time { margin-left:auto; color:var(--muted); font-variant-numeric:tabular-nums; }
    .sidebar { padding:20px; position:sticky; top:16px; max-height:calc(100vh - 32px); overflow:auto; }
    .sidebar h2 { margin:0 0 4px; }
    .sidebar > p { margin:0 0 18px; color:var(--muted); }
    .section { padding:17px 0; border-top:1px solid var(--line); }
    .section h3 { margin:0 0 10px; font-size:15px; }
    label { display:block; color:var(--muted); font-size:12px; margin:0 0 6px; }
    .row { display:grid; grid-template-columns:1fr auto; gap:8px; }
    input { width:100%; min-width:0; color:var(--text); background:#0f1720; border:1px solid var(--line); border-radius:9px; padding:11px 12px; outline:none; }
    input:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(85,214,169,.12); }
    .btn { min-height:42px; padding:9px 14px; border:1px solid var(--line); border-radius:9px; background:var(--panel2); color:var(--text); font-weight:700; }
    .btn.primary { background:var(--accent); color:#07130f; border-color:var(--accent); }
    .btn.full { width:100%; }
    .status { margin-top:10px; padding:11px 12px; border-left:3px solid var(--line); background:#101821; color:var(--muted); white-space:pre-wrap; }
    .status.ok { border-color:var(--accent); color:#c8ffec; }
    .status.error { border-color:var(--danger); color:#ffc5c5; }
    .weather-result { display:grid; grid-template-columns:auto 1fr; gap:12px; align-items:center; margin-top:10px; padding:13px; border:1px solid var(--line); border-radius:12px; background:#101821; }
    .weather-result .icon { font-size:34px; }
    .weather-result strong,.weather-result span { display:block; }
    .weather-result span { color:var(--muted); font-size:12px; }
    details summary { cursor:pointer; font-weight:750; }
    .mapping { display:grid; gap:10px; margin-top:13px; }
    .map-row { display:grid; grid-template-columns:125px 1fr; gap:9px; align-items:center; }
    .map-row label { margin:0; color:var(--text); }
    .map-row small { display:block; color:var(--muted); font-size:10px; }
    .hint { color:var(--muted); font-size:11px; margin:9px 0 0; }
    .badge { display:inline-block; border-radius:99px; padding:3px 8px; margin-left:5px; background:rgba(255,209,102,.13); color:var(--accent2); font-size:11px; }
    @media (max-width:980px) { .layout{grid-template-columns:1fr}.sidebar{position:static;max-height:none} }
    @media (max-width:560px) { .app{padding:10px}.stage{aspect-ratio:9/12}.map-row{grid-template-columns:1fr}.time{width:100%;margin-left:0}header{align-items:flex-start;flex-direction:column}.header-actions{justify-content:flex-start} }
  </style>
</head>
<body>
<main class="app">
  <header>
    <div><h1>Bengaluru Weather Cut</h1><p>Play a video URL or local file, then automatically switch to the matching YouTube post-credit ad.</p></div>
    <div class="header-actions">
      <div class="live" id="clock">Bengaluru weather</div>
      <button class="panel-toggle" id="togglePanel" type="button" aria-expanded="true">Hide settings</button>
    </div>
  </header>

  <div class="layout" id="layout">
    <section class="card viewer">
      <div class="stage">
        <div class="empty" id="empty"><strong>No video loaded</strong>Enter a video URL or full local path in the settings panel.</div>
        <video id="video" playsinline hidden></video>
        <div class="main-youtube" id="mainYoutube" hidden><div id="mainYoutubePlayer"></div></div>
        <div class="youtube-layer" id="youtubeLayer">
          <iframe id="youtubeFrame" title="Weather-selected YouTube advertisement"
            referrerpolicy="strict-origin-when-cross-origin"
            allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>
          <div class="ad-message" id="adMessage" hidden>
            <div><div style="font-size:46px" id="adIcon">☀️</div><h2 id="adTitle">Post-credit ad</h2><p id="adText"></p><button class="btn primary" id="returnVideo">Return to main video</button></div>
          </div>
        </div>
      </div>

      <div class="toolbar">
        <button class="primary" id="play">▶ Play</button>
        <button id="pause">⏸ Pause</button>
        <button id="back">↶ 10s</button>
        <button id="forward">10s ↷</button>
        <button id="restart">↺ Restart</button>
        <select id="speed" aria-label="Playback speed">
          <option value="0.5">0.5×</option><option value="1" selected>1×</option>
          <option value="1.25">1.25×</option><option value="1.5">1.5×</option><option value="2">2×</option>
        </select>
        <span class="time" id="time">00:00 / 00:00</span>
      </div>
    </section>

    <aside class="card sidebar">
      <h2>Player setup</h2>
      <p>Use a YouTube URL, a direct MP4/WebM URL, or a full local file path.</p>

      <section class="section">
        <h3>1. Main video source</h3>
        <label for="videoPath">YouTube/direct video URL or local path</label>
        <div class="row"><input id="videoPath" type="text" spellcheck="false" placeholder="https://… or D:\Brahma_AI\movie.mp4"><button class="btn primary" id="loadVideo">Load</button></div>
        <div class="status" id="videoStatus">Enter a URL or local path and click Load.</div>
      </section>

      <section class="section">
        <h3>2. Bengaluru current weather</h3>
        <button class="btn full" id="checkWeather">Check weather now</button>
        <div class="weather-result" id="weatherResult">
          <div class="icon" id="weatherIcon">…</div>
          <div><strong id="weatherTitle">Not checked</strong><span id="weatherDetail">The app checks again when the main video ends.</span></div>
        </div>
        <div class="status" id="weatherStatus">Waiting.</div>
      </section>

      <section class="section">
        <details open>
          <summary>3. YouTube ad mapping <span class="badge">saved locally</span></summary>
          <p class="hint">Paste a full YouTube URL or its 11-character video ID. Exact ad links are required; the app does not guess which brand's ad you want.</p>
          <div class="mapping" id="mapping"></div>
          <button class="btn full" id="saveAds" style="margin-top:12px">Save YouTube mappings</button>
          <div class="status" id="mappingStatus">Add the eight ad links, then save.</div>
        </details>
      </section>
    </aside>
  </div>
</main>

<script>
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
      host: 'https://www.youtube.com',
      playerVars: {
        controls: 0,
        rel: 0,
        playsinline: 1,
        origin: window.location.origin,
        widget_referrer: window.location.href
      },
      events: {
        onReady: resolve,
        onError: event => {
          const messages = {
            2: 'The YouTube video ID is invalid.',
            5: 'YouTube could not play this video in the HTML5 player.',
            100: 'This YouTube video was removed, made private, or cannot be found.',
            101: 'The video owner has disabled playback on embedded websites.',
            150: 'The video owner has disabled playback on embedded websites.',
            153: 'YouTube did not receive valid player origin/referrer information.'
          };
          reject(new Error(`${messages[event.data] || 'YouTube could not load this video.'} (error ${event.data})`));
        },
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
    const origin = encodeURIComponent(window.location.origin);
    const referrer = encodeURIComponent(window.location.href);
    frame.src = `https://www.youtube.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0&playsinline=1&origin=${origin}&widget_referrer=${referrer}`;
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
</script>
</body>
</html>
'''


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def describe_weather_code(code: int) -> str:
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return descriptions.get(code, f"Weather code {code}")


def classify_weather(current: dict[str, Any]) -> str:
    """Return one of the eight categories requested by the user.

    Priority is hazardous precipitation first, then fog, temperature extremes,
    and finally cloud cover. "Dry" means current precipitation, rain and
    showers all equal zero.
    """
    code = int(numeric(current.get("weather_code"), -1))
    temperature = numeric(current.get("temperature_2m"))
    precipitation = numeric(current.get("precipitation"))
    rain = numeric(current.get("rain"))
    showers = numeric(current.get("showers"))

    thunderstorm_codes = {95, 96, 99}
    rain_or_drizzle_codes = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
    fog_codes = {45, 48}
    dry = precipitation <= 0 and rain <= 0 and showers <= 0

    if code in thunderstorm_codes:
        return "thunderstorm"
    if code in rain_or_drizzle_codes or precipitation > 0 or rain > 0 or showers > 0:
        return "rain"
    if code in fog_codes:
        return "fog"
    if temperature >= 34 and dry:
        return "very_hot"
    if temperature <= 18:
        return "cool"
    if code in {1, 2}:
        return "partly_cloudy"
    if code == 3:
        return "overcast"
    return "sunny"


def get_bengaluru_weather() -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "latitude": BENGALURU_LATITUDE,
            "longitude": BENGALURU_LONGITUDE,
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,showers,weather_code",
            "timezone": "Asia/Kolkata",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "BengaluruWeatherCut/1.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))

    current = payload.get("current")
    if not isinstance(current, dict):
        raise RuntimeError("Weather service returned no current conditions.")

    category = classify_weather(current)
    meta = WEATHER_META[category]
    code = int(numeric(current.get("weather_code"), -1))
    return {
        "place": "Bengaluru, Karnataka, India",
        "time": current.get("time", "now"),
        "temperature_c": numeric(current.get("temperature_2m")),
        "humidity_percent": numeric(current.get("relative_humidity_2m")),
        "precipitation_mm": numeric(current.get("precipitation")),
        "rain_mm": numeric(current.get("rain")),
        "showers_mm": numeric(current.get("showers")),
        "weather_code": code,
        "description": describe_weather_code(code),
        "category": category,
        "weather_label": meta["weather"],
        "product": meta["product"],
    }


class AppHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self) -> None:
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        global VIDEO_PATH
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/":
            self.send_html()
            return

        if parsed.path == "/config":
            with VIDEO_LOCK:
                current_path = str(VIDEO_PATH) if VIDEO_PATH else ""
            self.send_json({"video_source": INITIAL_VIDEO_SOURCE or current_path, "youtube_ads": DEFAULT_YOUTUBE_ADS})
            return

        if parsed.path == "/set-video":
            query = urllib.parse.parse_qs(parsed.query)
            raw_path = query.get("path", [""])[0].strip().strip('"')
            if not raw_path:
                self.send_json({"error": "No video path was provided."}, 400)
                return

            candidate = Path(os.path.abspath(os.path.expanduser(raw_path)))
            if not candidate.is_file():
                self.send_json({"error": f"Video file not found: {candidate}"}, 404)
                return

            with VIDEO_LOCK:
                VIDEO_PATH = candidate
            self.send_json({"ok": True, "path": str(candidate), "size": candidate.stat().st_size})
            return

        if parsed.path == "/video":
            self.serve_video(send_body=True)
            return

        if parsed.path == "/weather":
            try:
                self.send_json(get_bengaluru_weather())
            except urllib.error.URLError as error:
                self.send_json({"error": f"Could not reach the weather service: {error.reason}"}, 502)
            except Exception as error:
                self.send_json({"error": str(error)}, 500)
            return

        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self.send_json({"error": "Not found."}, 404)

    def do_HEAD(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/video":
            self.serve_video(send_body=False)
            return
        self.send_response(404)
        self.end_headers()

    def serve_video(self, send_body: bool) -> None:
        with VIDEO_LOCK:
            path = VIDEO_PATH
        if not path or not path.is_file():
            self.send_json({"error": "No video has been loaded."}, 404)
            return

        size = path.stat().st_size
        start = 0
        end = size - 1
        status = 200
        range_header = self.headers.get("Range")

        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return

            first, last = match.groups()
            if first:
                start = int(first)
                end = int(last) if last else size - 1
            elif last:
                suffix_length = int(last)
                start = max(0, size - suffix_length)
                end = size - 1

            if start >= size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return

            end = min(end, size - 1)
            status = 206

        length = end - start + 1
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        if not send_body:
            return

        try:
            with path.open("rb") as source:
                source.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    global VIDEO_PATH, INITIAL_VIDEO_SOURCE

    if len(sys.argv) > 1:
        supplied_source = sys.argv[1].strip().strip('"')
        if supplied_source.lower().startswith(("http://", "https://")):
            INITIAL_VIDEO_SOURCE = supplied_source
        else:
            candidate = Path(os.path.abspath(os.path.expanduser(supplied_source)))
            if candidate.is_file():
                VIDEO_PATH = candidate
            else:
                print(f"Warning: video path does not exist: {candidate}")

    server = LocalServer((HOST, PORT), AppHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"Bengaluru Weather Cut is running at {url}")
    print("Press Ctrl+C to stop it.")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server…")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
