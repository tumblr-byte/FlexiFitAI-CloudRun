/* -----------------------
  script.js (updated)
  Requires a template-provided JSON config element:
  <script id="workout_config" type="application/json"> { ... } </script>
-------------------------*/

/* ================== load config injected by template ================== */
const __RAW_CONFIG = (function(){
  const el = document.getElementById("workout_config");
  if (!el) {
    console.error("Missing #workout_config element — please add JSON config in template.");
    return {};
  }
  try { return JSON.parse(el.textContent || "{}"); }
  catch (e) { console.error("Invalid JSON in #workout_config", e); return {}; }
})();

const URL_CLASSIFY = __RAW_CONFIG.URL_CLASSIFY || "";
const URL_MOTIVATE = __RAW_CONFIG.URL_MOTIVATE || "";
const URL_LOG = __RAW_CONFIG.URL_LOG || "";
const targetPose = __RAW_CONFIG.targetPose || "Standard_Tree";
const aiName = __RAW_CONFIG.aiName || "Gemini";
const personality = __RAW_CONFIG.personality || "Friendly";
const visitor_id = __RAW_CONFIG.visitor_id || null;
const coach_id = __RAW_CONFIG.coach_id || null;

/* ================= ANGLE MAP (kept from your original) ================= */
const ANGLE_MAP = {
  "Downdog": [
    { name: "left_leg", a: 23, b: 25, c: 27 },
    { name: "right_leg", a: 24, b: 26, c: 28 },
    { name: "back_torso", a: 11, b: 23, c: 25 }
  ],
  "Standard_Tree": [
    { name: "standing_leg", a: 24, b: 26, c: 28 },
    { name: "raised_leg", a: 23, b: 24, c: 26 },
    { name: "left_arm_up", a: 11, b: 13, c: 15 },
    { name: "right_arm_up", a: 12, b: 14, c: 16 }
  ],
  "Warrior2": [
    { name: "front_leg", a: 23, b: 25, c: 27 },
    { name: "back_leg", a: 24, b: 26, c: 28 },
    { name: "left_arm", a: 11, b: 13, c: 15 },
    { name: "right_arm", a: 12, b: 14, c: 16 }
  ],
  "Plank": [
    { name: "left_leg", a: 23, b: 25, c: 27 },
    { name: "right_leg", a: 24, b: 26, c: 28 },
    { name: "left_arm", a: 11, b: 13, c: 15 },
    { name: "right_arm", a: 12, b: 14, c: 16 },
    { name: "torso", a: 11, b: 23, c: 25 }
  ],
  "Modified_Tree": [
    { name: "standing_leg", a: 24, b: 26, c: 28 },
    { name: "left_arm_joint", a: 11, b: 13, c: 15 },
    { name: "right_arm_joint", a: 12, b: 14, c: 16 },
    { name: "shoulder_alignment", a: 11, b: 12, c: 24 }
  ]
};

/* ================= CONFIG (tweakable) ================= */
let totalRounds = (targetPose === "Modified_Tree") ? 2 : 1;
let holdDuration = 20;      // seconds per hold
let breakDuration = 3;      // seconds (only for Modified_Tree)
let halfwayAt = Math.floor(holdDuration / 2);

/* UI refs (safe-get) */
const canvas = document.getElementById("output_canvas");
const ctx = canvas ? canvas.getContext("2d") : null;
const progressEl = document.getElementById("progress");
const timeText = document.getElementById("timeText");
const roundStatus = document.getElementById("roundStatus");
const motivationDiv = document.getElementById("motivation");
const detectedText = document.getElementById("detectedText");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const inputVideoEl = document.getElementById("input_video");

/* guard for required elements */
if (!canvas || !ctx) {
  console.error("output_canvas is required in template.");
}

/* STATE */
let currentRound = 0;
let countdown = null;
let timeLeft = holdDuration;
let isTimerRunning = false;
let inBreak = false;
let misalignedCount = 0;
let lastDetected = "None";
let lastConfidence = 0.0;
let lastClassify = 0;
let classifyIntervalMs = 700; // ~1.4 FPS
let motivationHalfSpoken = false;
let cameraInstance = null;
let mpPose = null;
let recognition = null;

/* Misalignment debounce: only count if off-pose for > threshold */
let misalignedSince = null;
const MISALIGNED_THRESHOLD_MS = 1500;

/* ----------------- Helpers ----------------- */
function speakSystem(text) {
  if (!text) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.0; u.pitch = 1.0;
    window.speechSynthesis.speak(u);
  } catch (e) {
    console.warn("TTS error", e);
  }
  if (motivationDiv) motivationDiv.textContent = text;
}

async function fetchJson(url, payload) {
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {})
    });
    return await r.json();
  } catch (err) {
    console.error("Network error", err);
    return { error: err.toString() };
  }
}

/* Gemini via backend - fallback lines depend on personality */
async function geminiSpeak(status) {
  let fallback;
  const p = (typeof personality === "string") ? personality.toLowerCase() : "";
  if (status === "halfway") {
    fallback = (p === "genz") ? "You’re halfway there — slay!" :
               (p === "calm") ? "Nice steady work — keep holding." :
                                "Great job so far — keep going.";
  } else if (status === "complete") {
    fallback = (p === "genz") ? "Bro, you slayed that!" :
               (p === "calm") ? "Well done — you completed the round." :
                                "Nice work — great form!";
  } else { // help
    fallback = "Okay, got it — switching you to the modified version.";
  }

  // If URL_MOTIVATE missing, just fallback
  if (!URL_MOTIVATE) {
    speakSystem(`${aiName}: ${fallback}`);
    return fallback;
  }

  const resp = await fetchJson(URL_MOTIVATE, {
    ai_name: aiName, personality, pose: targetPose, status
  });

  const text = (resp && resp.text) ? resp.text : fallback;
  speakSystem(`${aiName}: ${text}`);
  return text;
}

/* Logging helper sends misaligned snapshot too */
async function logEvent(event, detected_pose = "", duration = 0.0, confidence = 0.0) {
  // If no backend log URL, skip silently
  if (!URL_LOG) return;

  try {
    await fetchJson(URL_LOG, {
      visitor_id: visitor_id || null,
      coach_id: coach_id || null,
      target_pose: targetPose,
      detected_pose,
      time_duration: duration,
      confidence,
      event,
      misaligned_count: misalignedCount
    });
  } catch (e) {
    console.warn("logEvent failed", e);
  }
}

/* ---------------- Timer / rounds ---------------- */
function updateProgressCircle() {
  const circumference = 2 * Math.PI * 86; // r = 86 (SVG circle)
  const fraction = Math.max(0, Math.min(1, timeLeft / holdDuration));
  const offset = circumference * (1 - fraction);
  if (progressEl) progressEl.style.strokeDashoffset = offset;
  if (timeText) timeText.textContent = `${timeLeft}s`;
  if (roundStatus) roundStatus.textContent = `Round ${currentRound} / ${totalRounds}`;
}

function startHoldCountdown() {
  if (isTimerRunning) return;
  isTimerRunning = true;
  motivationHalfSpoken = false;
  misalignedSince = null;
  speakSystem(`${aiName}: Hold the ${targetPose} pose for ${holdDuration} seconds.`);
  currentRound = currentRound || 1;
  timeLeft = holdDuration;
  updateProgressCircle();

  countdown = setInterval(async () => {
    timeLeft--;
    updateProgressCircle();

    // EXACT halfway trigger
    if (timeLeft === halfwayAt && !motivationHalfSpoken) {
      motivationHalfSpoken = true;
      await geminiSpeak("halfway");
    }

    if (timeLeft <= 0) {
      clearInterval(countdown);
      countdown = null;
      isTimerRunning = false;

      const msg = await geminiSpeak("complete");
      await logEvent("round_complete", targetPose, holdDuration, lastConfidence || 0);

      // Modified_Tree: handle break + second round
      if (targetPose === "Modified_Tree" && currentRound < totalRounds) {
        inBreak = true;
        speakSystem(`${aiName}: Round ${currentRound} complete. Take a ${breakDuration}-second break.`);
        let bLeft = breakDuration;
        timeText.textContent = `Break ${bLeft}s`;
        const bInt = setInterval(() => {
          bLeft--;
          timeText.textContent = `Break ${bLeft}s`;
          if (bLeft <= 0) {
            clearInterval(bInt);
            inBreak = false;
            currentRound += 1;
            timeLeft = holdDuration;
            updateProgressCircle();
            if (motivationDiv) motivationDiv.textContent = "Align to start next round.";
            // next round will start when pose is detected again
          }
        }, 1000);
      } else {
        // session finished
        await logEvent("session_finished", targetPose, holdDuration * totalRounds, lastConfidence || 0);
        showResultCard(msg);
      }
    }
  }, 1000);
}

/* ---------------- Drawing: skeleton + angles ---------------- */
function toPixels(lms, w, h) {
  return lms.map(p => ({ x: p.x * w, y: p.y * h, z: p.z }));
}

function calcAnglePx(a, b, c) {
  const abx = a.x - b.x, aby = a.y - b.y;
  const cbx = c.x - b.x, cby = c.y - b.y;
  const dot = abx * cbx + aby * cby;
  const abLen = Math.hypot(abx, aby);
  const cbLen = Math.hypot(cbx, cby);
  const cos = dot / (abLen * cbLen + 1e-9);
  const angle = Math.acos(Math.max(-1, Math.min(1, cos)));
  return angle * 180 / Math.PI;
}

function drawAngleLabel(ctx, pos, angle, label) {
  const text = `${label}: ${Math.round(angle)}°`;
  ctx.font = "13px Inter, Arial";
  ctx.lineWidth = 3;
  ctx.strokeStyle = "rgba(0,0,0,0.7)";
  ctx.strokeText(text, pos.x + 10, pos.y - 8);
  ctx.fillStyle = "#bff";
  ctx.fillText(text, pos.x + 10, pos.y - 8);
}

function drawSkeletonAndAngles(results) {
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (results.image) ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
  if (!results.poseLandmarks) return;

  const w = canvas.width, h = canvas.height;
  const lms = toPixels(results.poseLandmarks, w, h);

  const connections = [
    [11,13],[13,15],[12,14],[14,16],
    [11,12],[23,24],[23,25],[25,27],[24,26],[26,28]
  ];

  ctx.lineWidth = 3;
  ctx.strokeStyle = (lastDetected === targetPose) ? "rgba(0,255,140,0.95)" : "rgba(255,80,80,0.95)";
  connections.forEach(([a,b]) => {
    if (a < lms.length && b < lms.length) {
      ctx.beginPath();
      ctx.moveTo(lms[a].x, lms[a].y);
      ctx.lineTo(lms[b].x, lms[b].y);
      ctx.stroke();
    }
  });

  lms.forEach(p => {
    ctx.beginPath();
    ctx.fillStyle = (lastDetected === targetPose) ? "#00ff99" : "#ff6666";
    ctx.arc(p.x, p.y, 4, 0, Math.PI*2);
    ctx.fill();
  });

  const map = ANGLE_MAP[targetPose];
  if (map && map.length) {
    map.forEach(item => {
      const { name, a, b, c } = item;
      if (a < lms.length && b < lms.length && c < lms.length) {
        const A = { x: lms[a].x, y: lms[a].y };
        const B = { x: lms[b].x, y: lms[b].y };
        const C = { x: lms[c].x, y: lms[c].y };
        const angle = calcAnglePx(A, B, C);
        ctx.beginPath();
        ctx.moveTo(B.x, B.y);
        ctx.lineTo(A.x, A.y);
        ctx.moveTo(B.x, B.y);
        ctx.lineTo(C.x, C.y);
        ctx.stroke();
        drawAngleLabel(ctx, B, angle, name);
      }
    });
  }

  ctx.font = "16px Inter, Arial";
  ctx.fillStyle = "#fff";
  ctx.fillText(`Target: ${targetPose}  Detected: ${lastDetected} (${Math.round((lastConfidence||0)*100)}%)`, 10, 20);
  ctx.font = "13px Inter, Arial";
  ctx.fillText(`Misaligned: ${misalignedCount}`, 10, 40);
}

/* --------------- MediaPipe setup & classify --------------- */
function initMediaPipe() {
  if (mpPose) return;
  mpPose = new Pose({ locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5/${f}` });
  mpPose.setOptions({ modelComplexity: 1, smoothLandmarks: true, minDetectionConfidence: 0.6, minTrackingConfidence: 0.6 });

  mpPose.onResults(async (results) => {
    try { drawSkeletonAndAngles(results); } catch (e) { console.error("draw err", e); }

    const now = Date.now();
    if (now - lastClassify < classifyIntervalMs) return;
    lastClassify = now;

    if (!results.poseLandmarks) {
      lastDetected = "None";
      lastConfidence = 0;
      if (detectedText) detectedText.textContent = `Detected: None`;
      if (isTimerRunning && misalignedSince === null) misalignedSince = Date.now();
      return;
    }

    // we have landmarks -> call backend classifier
    const lmArr = results.poseLandmarks.map(p => [p.x, p.y, p.z]);
    const resp = await fetchJson(URL_CLASSIFY, { landmarks: lmArr });
    if (!resp || resp.error) {
      if (resp && resp.error) console.warn("classify error:", resp.error);
      return;
    }

    lastDetected = resp.predicted || "None";
    lastConfidence = resp.confidence || 0;
    if (detectedText) detectedText.textContent = `Detected: ${lastDetected} (${Math.round(lastConfidence*100)}%)`;

    // If matched and not running and not in break -> start
    if (lastDetected === targetPose && !isTimerRunning && !inBreak) {
      misalignedSince = null;
      startHoldCountdown();
    }

    // misalignment counting logic
    if (lastDetected !== targetPose && isTimerRunning) {
      if (misalignedSince === null) misalignedSince = Date.now();
      else {
        const elapsed = Date.now() - misalignedSince;
        if (elapsed >= MISALIGNED_THRESHOLD_MS) {
          misalignedCount++;
          misalignedSince = Date.now();
          await logEvent("misaligned", lastDetected, (holdDuration - timeLeft), lastConfidence || 0);
          if (detectedText) detectedText.textContent = `Detected: ${lastDetected} (${Math.round(lastConfidence*100)}%) ⚠️ Misaligned ${misalignedCount}`;
        }
      }
    } else {
      misalignedSince = null;
    }
  });
}

/* --------------- Voice (Standard_Tree) --------------- */
function initVoiceRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn("SpeechRecognition not available in this browser.");
    return;
  }

  recognition = new SR();
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onresult = async (ev) => {
    const last = ev.results[ev.results.length - 1][0].transcript.toLowerCase().trim();
    console.log("heard voice:", last);

    // greet pattern: "hey <aiName>"
    if ((aiName && last.includes("hey " + aiName.toLowerCase())) || (aiName && last.includes("hi " + aiName.toLowerCase()))) {
      const resp = await fetchJson(URL_MOTIVATE, { ai_name: aiName, personality, pose: targetPose, status: "help" });
      const text = (resp && resp.text) ? resp.text : `Hey ${aiName}, how can I help?`;
      speakSystem(`${aiName}: ${text}`);
    }

    if (last.includes("help") || last.includes("pose is hard") || last.includes("this is hard") || last.includes("i can't do this")) {
      const respText = "Okay, I got you! This pose seems hard — switching to Modified Tree version for you.";
      speakSystem(`${aiName}: ${respText}`);
      await logEvent("help_switched", lastDetected, 0, lastConfidence || 0);
      setTimeout(() => window.location.href = "/ex/workout/Modified_Tree/", 1200);
    }
  };

  recognition.onerror = (e) => console.warn("voice error", e);
  recognition.onend = () => {
    if (window._mp_camera) {
      try { recognition.start(); } catch (e) { /* ignore */ }
    }
  };

  try { recognition.start(); } catch (e) { console.warn("voice start failed", e); }
}

/* --------------- Start / Stop UI --------------- */
if (startBtn) startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  startBtn.style.opacity = "0.6";
  if (motivationDiv) motivationDiv.textContent = "Starting camera... please allow access.";
  speakSystem(`${aiName}: Starting your session. Please allow camera access.`);

  if (!mpPose) initMediaPipe();

  const video = inputVideoEl || document.createElement("video");
  if (inputVideoEl) inputVideoEl.style.display = "none";

  // instantiate MediaPipe Camera helper (this uses the video element, but we hide it)
  cameraInstance = new Camera(video, {
    onFrame: async () => { if (mpPose) await mpPose.send({ image: video }); },
    width: 720, height: 540
  });

  try {
    await cameraInstance.start();
    window._mp_camera = cameraInstance;
    if (motivationDiv) motivationDiv.textContent = "Camera ready. Align to start the round.";
    speakSystem(`${aiName}: Camera ready. Align to start the round.`);
    await logEvent("session_started");

    // voice only for Standard_Tree as requested
    if (targetPose === "Standard_Tree") initVoiceRecognition();
  } catch (err) {
    console.error("Camera start failed", err);
    speakSystem(`${aiName}: Camera permission denied or failed.`);
  } finally {
    startBtn.disabled = false;
    startBtn.style.opacity = "1";
    // show/hide start/stop buttons if present
    if (startBtn) startBtn.style.display = "none";
    if (stopBtn) stopBtn.style.display = "block";
  }
});

if (stopBtn) stopBtn.addEventListener("click", async () => {
  if (window._mp_camera) try { window._mp_camera.stop(); } catch (e) {}
  if (recognition) try { recognition.stop(); } catch (e) {}
  if (countdown) { clearInterval(countdown); countdown = null; }
  isTimerRunning = false;
  if (motivationDiv) motivationDiv.textContent = "Stopped.";
  await logEvent("session_stopped");
  if (stopBtn) stopBtn.style.display = "none";
  if (startBtn) startBtn.style.display = "block";
});

/* --------------- Result card --------------- */
function showResultCard(aiMessage) {
  if (window._mp_camera) try { window._mp_camera.stop(); } catch (e) {}
  const panel = document.querySelector(".panel");
  const totalTime = holdDuration * totalRounds;
  if (!panel) return;
  panel.innerHTML = `
    <div style="padding:18px;text-align:center;">
      <h2>✅ Session Complete</h2>
      <p><strong>Pose:</strong> ${targetPose}</p>
      <p><strong>time_taken:</strong> ${totalTime}s</p>
      <p><strong>Misaligned:</strong> ${misalignedCount} times</p>
      <p style="margin-top:12px;"><em>${aiName}:</em> "${aiMessage}"</p>
      <div style="display:flex;gap:8px;justify-content:center;margin-top:14px;">
        <button id="retryBtn" style="padding:8px 12px;border-radius:8px;border:none;background:#dbe271;cursor:pointer;">Try Again</button>
        <button id="closeBtn" style="padding:8px 12px;border-radius:8px;border:none;background:#ef4444;color:#fff;cursor:pointer;">Close</button>
      </div>
    </div>
  `;
  document.getElementById("retryBtn").addEventListener("click", () => location.reload());
  document.getElementById("closeBtn").addEventListener("click", () => location.reload());
}

/* --------------- Init UI --------------- */
updateProgressCircle();
if (motivationDiv) motivationDiv.textContent = `${aiName}: Press Start to begin.`;
if (detectedText) detectedText.textContent = `Detected: None`;
