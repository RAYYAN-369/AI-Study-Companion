// ============================================================
// AI Study Companion — front-end interactivity
// Calls the real FastAPI backend: POST /upload -> POST /study-plan ->
// render the actual response on result.html. No simulated pipeline.
// ============================================================

const STORAGE_KEY = "studyCompanion.lastRun";

/* ---------------------------------------------------------
   UPLOAD PAGE
--------------------------------------------------------- */
(function initUploadPage() {
  const form = document.getElementById("uploadForm");
  if (!form) return;

  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const fileCard = document.getElementById("fileCard");
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  const removeFile = document.getElementById("removeFile");
  const topicInput = document.getElementById("topicInput");
  const charCount = document.getElementById("charCount");
  const submitBtn = document.getElementById("submitBtn");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const loadingHeadline = document.getElementById("loadingHeadline");

  const MAX_BYTES = APP_CONFIG.MAX_FILE_BYTES;
  const ALLOWED = APP_CONFIG.ALLOWED_EXTENSIONS;
  let currentFile = null;

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function updateSubmitState() {
    const hasFile = !!currentFile;
    const hasTopic = topicInput.value.trim().length > 0;
    submitBtn.disabled = !(hasFile && hasTopic);
  }

  function acceptFile(file) {
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      window.location.href =
        "error.html?reason=type&name=" + encodeURIComponent(file.name);
      return;
    }
    if (file.size > MAX_BYTES) {
      window.location.href =
        "error.html?reason=size&name=" + encodeURIComponent(file.name);
      return;
    }
    currentFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatSize(file.size);
    fileCard.hidden = false;
    updateSubmitState();
  }

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener("change", (e) => {
    if (e.target.files[0]) acceptFile(e.target.files[0]);
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
    })
  );
  dropZone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) acceptFile(file);
  });

  removeFile.addEventListener("click", () => {
    currentFile = null;
    fileInput.value = "";
    fileCard.hidden = true;
    updateSubmitState();
  });

  topicInput.addEventListener("input", () => {
    charCount.textContent = topicInput.value.length;
    updateSubmitState();
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (submitBtn.disabled) return;
    runPipeline();
  });

  function setStep(index, headline) {
    const steps = loadingOverlay.querySelectorAll(".loading-steps li");
    steps.forEach((li, idx) => {
      li.classList.toggle("done", idx < index);
      li.classList.toggle("active", idx === index);
    });
    loadingHeadline.textContent = headline;
  }

  function goToError(reason, message) {
    loadingOverlay.hidden = true;
    const url =
      "error.html?reason=" +
      encodeURIComponent(reason) +
      "&message=" +
      encodeURIComponent(message || "");
    window.location.href = url;
  }

  async function runPipeline() {
    loadingOverlay.hidden = false;
    const topic = topicInput.value.trim();

    // Step 1-3: upload -> backend parses, chunks, embeds, stores
    setStep(0, "Uploading and parsing your document…");
    let uploadResult;
    try {
      const formData = new FormData();
      formData.append("file", currentFile);

      const uploadResp = await fetch(APP_CONFIG.API_BASE_URL + "/upload", {
        method: "POST",
        body: formData,
      });

      if (!uploadResp.ok) {
        const errBody = await safeJson(uploadResp);
        return goToError(
          "upload",
          (errBody && errBody.detail) || "Upload failed (" + uploadResp.status + ")."
        );
      }
      uploadResult = await uploadResp.json();
    } catch (err) {
      return goToError("network", "Couldn't reach the backend. Is it running?");
    }

    setStep(2, "Retrieving relevant context…");

    // Step 4: study plan generation
    let planResult;
    try {
      const planResp = await fetch(APP_CONFIG.API_BASE_URL + "/study-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          top_k: 5,
          document_id: uploadResult.document_id,
        }),
      });

      if (!planResp.ok) {
        const errBody = await safeJson(planResp);
        return goToError(
          "plan",
          (errBody && errBody.detail) || "Study plan generation failed (" + planResp.status + ")."
        );
      }
      planResult = await planResp.json();
    } catch (err) {
      return goToError("network", "Couldn't reach the backend. Is it running?");
    }

    setStep(4, "Writing your study plan…");

    // Only navigate to result.html with a real backend response.
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        fileName: uploadResult.filename,
        documentId: uploadResult.document_id,
        topic,
        plan: planResult,
        generatedAt: Date.now(),
      })
    );
    window.location.href = "result.html";
  }

  async function safeJson(resp) {
    try {
      return await resp.json();
    } catch {
      return null;
    }
  }
})();

/* ---------------------------------------------------------
   ERROR PAGE — read query params to tailor the message
--------------------------------------------------------- */
(function initErrorPage() {
  const titleEl = document.getElementById("errorTitle");
  const detailEl = document.getElementById("errorDetail");
  if (!titleEl) return;

  const params = new URLSearchParams(window.location.search);
  const reason = params.get("reason");
  const name = params.get("name");
  const message = params.get("message");

  if (reason === "type") {
    titleEl.textContent = "That file type isn't supported yet";
    detailEl.textContent = (name ? `"${name}" ` : "That file ") +
      "isn't a PDF, TXT, or DOCX file. Convert it or paste the text into a .txt file instead.";
  } else if (reason === "size") {
    const maxMb = Math.round(APP_CONFIG.MAX_FILE_BYTES / (1024 * 1024));
    titleEl.textContent = "That file is too large";
    detailEl.textContent = (name ? `"${name}" ` : "That file ") +
      `is over the ${maxMb}MB limit. Try splitting it or removing images before uploading.`;
  } else if (reason === "upload") {
    titleEl.textContent = "We couldn't process that upload";
    detailEl.textContent = message || "The document could not be parsed. It may be scanned as an image, empty, or corrupted.";
  } else if (reason === "plan") {
    titleEl.textContent = "We couldn't generate a study plan";
    detailEl.textContent = message || "Something went wrong while generating the plan from your notes.";
  } else if (reason === "network") {
    titleEl.textContent = "Can't reach the backend";
    detailEl.textContent = message || "The FastAPI server isn't responding. Make sure it's running and try again.";
  }
})();

/* ---------------------------------------------------------
   RESULT PAGE — renders the real backend response only
--------------------------------------------------------- */
(function initResultPage() {
  const topicHeadline = document.getElementById("topicHeadline");
  if (!topicHeadline) return;

  const raw = sessionStorage.getItem(STORAGE_KEY);
  const run = raw ? JSON.parse(raw) : null;

  if (!run || !run.plan) {
    // No real backend response in this session — send back to upload
    // instead of rendering fabricated data.
    window.location.href = "upload.html";
    return;
  }

  const plan = run.plan;
  const retrieval = plan.retrieval || { chunks_retrieved: 0, sources: [] };

  topicHeadline.textContent = plan.topic || run.topic;
  document.getElementById("aiSummary").textContent = plan.summary || "";
  document.getElementById("chunksRetrieved").textContent = retrieval.chunks_retrieved;
  document.getElementById("studyTime").textContent =
    (plan.estimated_total_hours != null ? plan.estimated_total_hours : "—") + " hr";
  document.getElementById("dayCount").textContent = (plan.days || []).length;
  document.getElementById("sourceFileName").textContent = run.fileName || "your document";

  const scheduleList = document.getElementById("scheduleList");
  (plan.days || []).forEach((day) => {
    const row = document.createElement("div");
    row.className = "schedule-row";
    const tasks = (day.tasks || []).map((t) => `<li>${escapeHtml(t)}</li>`).join("");
    row.innerHTML = `
      <span class="sched-order">${day.day}</span>
      <div class="sched-body">
        <div class="sched-topic">${escapeHtml(day.focus || "")}</div>
        <ul class="sched-tasks">${tasks}</ul>
      </div>
      <span class="sched-time">${day.estimated_hours != null ? day.estimated_hours + " hr" : ""}</span>
    `;
    scheduleList.appendChild(row);
  });
  if (!(plan.days || []).length) {
    const empty = document.createElement("p");
    empty.className = "block-sub";
    empty.textContent = "No schedule was returned.";
    scheduleList.appendChild(empty);
  }

  const sourcesList = document.getElementById("sourcesList");
  (retrieval.sources || []).forEach((s, i) => {
    const item = document.createElement("div");
    item.className = "source-item";
    item.innerHTML = `<span class="src-tag">${escapeHtml(s.filename || "source")} · chunk ${s.chunk_index != null ? s.chunk_index : i} · score ${s.score != null ? s.score : ""}</span>${escapeHtml(s.text || "")}`;
    sourcesList.appendChild(item);
  });
  if (!(retrieval.sources || []).length) {
    const empty = document.createElement("p");
    empty.className = "block-sub";
    empty.textContent = "No source passages were returned.";
    sourcesList.appendChild(empty);
  }

  document.getElementById("downloadBtn").addEventListener("click", () => {
    downloadPlan(plan, run);
  });
})();

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

function downloadPlan(plan, run) {
  const retrieval = plan.retrieval || { chunks_retrieved: 0, sources: [] };
  const lines = [
    "AI STUDY COMPANION — STUDY PLAN",
    "================================",
    "",
    "Topic: " + (plan.topic || run.topic),
    "Source document: " + (run.fileName || "unknown"),
    "Chunks retrieved: " + retrieval.chunks_retrieved,
    "Estimated total hours: " + plan.estimated_total_hours,
    "",
    "SUMMARY",
    plan.summary || "",
    "",
    "SCHEDULE",
    ...(plan.days || []).map(
      (d) =>
        "Day " + d.day + " — " + d.focus + " (" + d.estimated_hours + " hr)\n  - " +
        (d.tasks || []).join("\n  - ")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "study-plan.txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
