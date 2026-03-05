// offscreen.js — MediaRecorder engine (adapted from v12 L294-556)
// Runs in an offscreen document to handle tab capture recording.
//
// Blob handling: blobs stay in this document's memory.
// On export, we create a blob URL via URL.createObjectURL() and
// send it to the service worker for chrome.downloads.download().
// (Service workers can't create blob URLs, but can download them
//  if they share the same extension origin.)

const BITRATE = 8_000_000; // 8Mbps (~30MB per 30s clip)

let mediaStream = null;
let activeRecorder = null;
let completedSegments = []; // { blob, startTime, duration }[]
let isRecording = false;

// Track blob URLs so we can revoke them after download
let activeBlobUrls = [];
let pendingBugExport = false;

// --- MIME detection ---
function getMimeType() {
  if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) return 'video/webm;codecs=vp8';
  if (MediaRecorder.isTypeSupported('video/webm')) return 'video/webm';
  if (MediaRecorder.isTypeSupported('video/mp4')) return 'video/mp4';
  return '';
}

const MIME = getMimeType();

// --- Recorder ---
// Uses rec.start() (no timeslice) for a single contiguous WebM stream.
// All chunks are concatenated on stop to produce a valid, playable file.
// The UI enforces a 30-second wait before enabling the bug button,
// so the exported video is always >= 30 seconds.
function createAndStartRecorder() {
  const chunks = [];
  const startTime = Date.now();

  const rec = new MediaRecorder(mediaStream, {
    mimeType: MIME,
    videoBitsPerSecond: BITRATE,
  });

  rec.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) chunks.push(e.data);
  };

  rec.onstop = () => {
    const blob = new Blob(chunks, { type: MIME });
    const duration = Math.round((Date.now() - startTime) / 1000);

    if (blob.size > 0) {
      completedSegments.push({ blob, startTime, duration });
      while (completedSegments.length > 2) completedSegments.shift();
    }

    if (pendingBugExport) {
      pendingBugExport = false;
      sendBugClip();
      if (isRecording && mediaStream?.active) createAndStartRecorder();
    }
  };

  rec.start();
  activeRecorder = rec;
}

// --- Message handling ---
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.target !== 'offscreen') return;

  switch (msg.type) {
    case 'start-recording':
      startRecording(msg.streamId, msg.segmentMs);
      break;

    case 'stop-recording':
      stopRecording();
      break;

    case 'get-bug-clip':
      exportBugClip();
      break;

    case 'revoke-blob-url':
      // Clean up blob URL after download completes
      if (msg.url) {
        URL.revokeObjectURL(msg.url);
        activeBlobUrls = activeBlobUrls.filter(u => u !== msg.url);
      }
      break;
  }
});

async function startRecording(streamId, segMs) {
  if (isRecording) return;

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId,
        },
      },
    });

    const track = mediaStream.getVideoTracks()[0];
    try { track.contentHint = 'detail'; } catch (e) {}

    track.addEventListener('ended', () => {
      stopRecording();
      chrome.runtime.sendMessage({ type: 'recording-error', error: 'Stream ended' });
    });

    completedSegments = [];
    isRecording = true;

    createAndStartRecorder();

    chrome.runtime.sendMessage({
      type: 'recording-status',
      status: 'recording',
    });

    const settings = track.getSettings();
    console.log(`Recording started: ${settings.width}x${settings.height}, ${MIME}, ${BITRATE / 1_000_000}Mbps`);
  } catch (err) {
    chrome.runtime.sendMessage({
      type: 'recording-error',
      error: err.message,
    });
  }
}

function stopRecording() {
  isRecording = false;

  if (activeRecorder?.state === 'recording') {
    activeRecorder.stop();
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop());
    mediaStream = null;
  }

  completedSegments = [];

  // Revoke any outstanding blob URLs
  activeBlobUrls.forEach(url => URL.revokeObjectURL(url));
  activeBlobUrls = [];

  chrome.runtime.sendMessage({
    type: 'recording-status',
    status: 'stopped',
  });
}

function exportBugClip() {
  // If actively recording, stop the recorder first to capture the latest data.
  // onstop handler will call sendBugClip() and resume recording.
  if (activeRecorder && activeRecorder.state === 'recording') {
    pendingBugExport = true;
    activeRecorder.stop();
    return;
  }

  // No active recorder — fall back to last completed segment
  sendBugClip();
}

function sendBugClip() {
  if (completedSegments.length === 0) {
    chrome.runtime.sendMessage({
      type: 'recording-error',
      error: 'No completed segments available',
    });
    return;
  }

  // Use the latest completed segment (includes data up to the moment bug was triggered)
  const seg = completedSegments[completedSegments.length - 1];

  const blobUrl = URL.createObjectURL(seg.blob);
  activeBlobUrls.push(blobUrl);

  chrome.runtime.sendMessage({
    type: 'bug-clip-ready',
    blobUrl,
    segmentStartTime: seg.startTime,
    duration: seg.duration,
    size: seg.blob.size,
  });
}
