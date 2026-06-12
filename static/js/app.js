(function () {
  const root = document.documentElement;
  const themeToggle = document.getElementById("themeToggle");
  const savedTheme = localStorage.getItem("idp-theme") || "light";
  root.setAttribute("data-theme", savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", nextTheme);
      localStorage.setItem("idp-theme", nextTheme);
    });
  }

  const uploadForm = document.getElementById("uploadForm");
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const browseButton = document.getElementById("browseButton");
  const addMoreFilesButton = document.getElementById("addMoreFilesButton");
  const clearFilesButton = document.getElementById("clearFilesButton");
  const uploadSpinner = document.getElementById("uploadSpinner");
  const processButton = document.getElementById("processButton");
  const resultsContainer = document.getElementById("uploadResults");
  const uploadStatus = document.getElementById("uploadStatus");
  const selectedFilesText = document.getElementById("selectedFilesText");
  const selectedFilesList = document.getElementById("selectedFilesList");
  const selectedFiles = [];

  function setUploadStatus(message, variant = "info") {
    if (!uploadStatus) {
      return;
    }
    uploadStatus.className = `alert alert-${variant}`;
    uploadStatus.textContent = message;
    uploadStatus.classList.remove("d-none");
  }

  function clearUploadStatus() {
    if (!uploadStatus) {
      return;
    }
    uploadStatus.classList.add("d-none");
    uploadStatus.textContent = "";
  }

  function fileKey(file) {
    return `${file.name}:${file.size}:${file.lastModified}`;
  }

  function addSelectedFiles(files) {
    Array.from(files || []).forEach((file) => {
      if (!selectedFiles.some((selectedFile) => fileKey(selectedFile) === fileKey(file))) {
        selectedFiles.push(file);
      }
    });
    if (fileInput) {
      fileInput.value = "";
    }
    updateSelectedFiles();
  }

  function removeSelectedFile(index) {
    selectedFiles.splice(index, 1);
    updateSelectedFiles();
  }

  function clearSelectedFiles() {
    selectedFiles.splice(0, selectedFiles.length);
    if (fileInput) {
      fileInput.value = "";
    }
    updateSelectedFiles();
  }

  function updateSelectedFiles() {
    if (!selectedFilesText || !selectedFilesList) {
      return;
    }
    selectedFilesText.textContent = selectedFiles.length
      ? `${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"} selected.`
      : "No files selected yet.";
    selectedFilesList.innerHTML = selectedFiles.map((file, index) => `
      <div class="list-group-item d-flex align-items-center justify-content-between gap-3">
        <div class="text-truncate">
          <span class="text-success fw-bold me-2">✓</span>${escapeHtml(file.name)}
        </div>
        <button type="button" class="btn btn-outline-danger btn-sm" data-remove-file-index="${index}">Remove File</button>
      </div>
    `).join("");
  }

  if (browseButton && fileInput) {
    browseButton.addEventListener("click", () => fileInput.click());
  }

  if (addMoreFilesButton && fileInput) {
    addMoreFilesButton.addEventListener("click", () => fileInput.click());
  }

  if (clearFilesButton) {
    clearFilesButton.addEventListener("click", clearSelectedFiles);
  }

  if (selectedFilesList) {
    selectedFilesList.addEventListener("click", (event) => {
      const removeButton = event.target.closest("[data-remove-file-index]");
      if (!removeButton) {
        return;
      }
      removeSelectedFile(Number(removeButton.dataset.removeFileIndex));
    });
  }

  if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropZone.classList.add("dragover");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
    dropZone.addEventListener("drop", (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragover");
      addSelectedFiles(event.dataTransfer.files);
      console.log("[upload] files dropped", event.dataTransfer.files.length);
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", () => {
      addSelectedFiles(fileInput.files);
      console.log("[upload] files selected", selectedFiles.length);
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!selectedFiles.length) {
        setUploadStatus("Please select at least one file before processing.", "warning");
        console.warn("[upload] submit blocked: no files selected");
        return;
      }
      const formData = new FormData();
      selectedFiles.forEach((file) => formData.append("files", file));
      console.log("[upload] sending request", {
        count: selectedFiles.length,
        names: selectedFiles.map((file) => file.name),
      });
      setUploadStatus("Processing documents...", "info");
      if (uploadSpinner) uploadSpinner.classList.remove("d-none");
      if (processButton) processButton.setAttribute("disabled", "disabled");
      if (resultsContainer) resultsContainer.innerHTML = "";
      const resultsSummaryContainer = document.getElementById("resultsSummaryContainer");
      if (resultsSummaryContainer) resultsSummaryContainer.classList.add("d-none");
      try {
        const response = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        });
        const responseText = await response.text();
        console.log("[upload] response received", response.status, responseText.slice(0, 300));
        if (!response.ok) {
          throw new Error(responseText || `Upload failed with status ${response.status}`);
        }
        const payload = JSON.parse(responseText);
        renderUploadResults(payload.results || [], payload.excel_url, payload.excel_filename);
        setUploadStatus(`Processed ${payload.results?.length || 0} document(s) successfully.`, "success");
      } catch (error) {
        console.error("[upload] request failed", error);
        setUploadStatus(error.message || "Upload failed.", "danger");
        if (resultsContainer) {
          resultsContainer.innerHTML = `<div class="alert alert-danger">Upload failed: ${error.message}</div>`;
        }
      } finally {
        if (uploadSpinner) uploadSpinner.classList.add("d-none");
        if (processButton) processButton.removeAttribute("disabled");
      }
    });
  }

  function renderUploadResults(results, excelUrl, excelFilename) {
    if (!resultsContainer) return;
    if (!results.length) {
      resultsContainer.innerHTML = '<div class="empty-state">No processing results yet.</div>';
      return;
    }

    // Calculate statistics
    const processedCount = results.length;
    const approvedCount = results.filter((r) => r.status === "Approved").length;
    const needsReviewCount = results.filter((r) => r.status === "Needs Review").length;
    const avgConfidence = results.reduce((acc, r) => acc + (r.confidence || 0), 0) / processedCount;

    // Update summary counters
    const summaryProcessed = document.getElementById("summaryProcessed");
    const summaryApproved = document.getElementById("summaryApproved");
    const summaryNeedsReview = document.getElementById("summaryNeedsReview");
    const summaryAvgConfidence = document.getElementById("summaryAvgConfidence");
    const resultsSummaryContainer = document.getElementById("resultsSummaryContainer");
    const downloadExcelBtn = document.getElementById("downloadExcelBtn");
    const downloadExcelBtnText = document.getElementById("downloadExcelBtnText");

    if (summaryProcessed) summaryProcessed.textContent = processedCount;
    if (summaryApproved) summaryApproved.textContent = approvedCount;
    if (summaryNeedsReview) summaryNeedsReview.textContent = needsReviewCount;
    if (summaryAvgConfidence) summaryAvgConfidence.textContent = `${Math.round(avgConfidence * 100)}%`;

    if (downloadExcelBtn && excelUrl) {
      downloadExcelBtn.href = excelUrl;
      const exportFilename = excelFilename || (processedCount === 1 ? "invoice.xlsx" : "combined_export.xlsx");
      downloadExcelBtnText.textContent = processedCount === 1 ? "Download Excel" : "Download Combined Excel";
      downloadExcelBtn.setAttribute("download", exportFilename);
    }

    if (resultsSummaryContainer) {
      resultsSummaryContainer.classList.remove("d-none");
    }

    resultsContainer.innerHTML = results.map((result) => {
      const validation = result.validation || {};
      const extractedJson = JSON.stringify(result.json_output || {}, null, 2);
      const validationJson = JSON.stringify(validation, null, 2);
      
      return `
        <div class="panel">
          <div class="panel-body">
            <div class="d-flex justify-content-between align-items-start border-bottom pb-3 mb-3">
              <div>
                <h5 class="fw-bold mb-1">${escapeHtml(result.filename || "")}</h5>
                <div class="text-secondary small">Document Type: ${escapeHtml(result.document_type || "unknown")}</div>
              </div>
              <div class="text-end">
                <span class="status-pill status-${(result.status || "").toLowerCase().replace(' ', '_')}">${escapeHtml(result.status || "")}</span>
                <div class="small text-secondary mt-1">Confidence: ${Math.round((result.confidence || 0) * 100)}%</div>
              </div>
            </div>
            
            <div class="mb-4">
              <h6 class="fw-semibold text-secondary text-uppercase mb-2">OCR Text</h6>
              <pre class="json-block mt-2" style="white-space: pre-wrap; word-break: break-all;">${escapeHtml(result.raw_text || "")}</pre>
            </div>
            
            <div class="mb-4">
              <h6 class="fw-semibold text-secondary text-uppercase mb-2">Raw LLM Response</h6>
              <pre class="json-block mt-2" style="white-space: pre-wrap; word-break: break-all;">${escapeHtml(result.raw_llm_response || "")}</pre>
            </div>
            
            <div class="mb-4">
              <h6 class="fw-semibold text-secondary text-uppercase mb-2">Validation Result</h6>
              <pre class="json-block mt-2">${escapeHtml(validationJson)}</pre>
            </div>
            
            <div class="mb-3">
              <h6 class="fw-semibold text-secondary text-uppercase mb-2">Extracted JSON</h6>
              <pre class="json-block mt-2">${escapeHtml(extractedJson)}</pre>
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function renderChart(canvasId, chartConfig) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;
    return new Chart(canvas, chartConfig);
  }

  const dashboardCharts = window.dashboardCharts;
  if (dashboardCharts) {
    const typeLabels = (dashboardCharts.documents_by_type || []).map((item) => item.label);
    const typeValues = (dashboardCharts.documents_by_type || []).map((item) => item.value);
    const trendLabels = (dashboardCharts.daily_processing_trend || []).map((item) => item.label);
    const trendValues = (dashboardCharts.daily_processing_trend || []).map((item) => item.value);
    const confidenceValues = dashboardCharts.confidence_distribution || [];

    renderChart("typeChart", {
      type: "doughnut",
      data: { labels: typeLabels, datasets: [{ data: typeValues, backgroundColor: ["#2563eb", "#0ea5e9", "#8b5cf6", "#14b8a6", "#f59e0b"] }] },
      options: { plugins: { legend: { position: "bottom" } } },
    });
    renderChart("trendChart", {
      type: "line",
      data: { labels: trendLabels, datasets: [{ label: "Documents", data: trendValues, borderColor: "#2563eb", tension: 0.35, fill: true, backgroundColor: "rgba(37, 99, 235, 0.16)" }] },
      options: { plugins: { legend: { display: false } } },
    });
    renderChart("confidenceChart", {
      type: "bar",
      data: { labels: confidenceValues.map((_, index) => `#${index + 1}`), datasets: [{ label: "Confidence", data: confidenceValues, backgroundColor: "#0ea5e9" }] },
      options: { plugins: { legend: { display: false } } },
    });
  }

  const analyticsCharts = window.analyticsCharts;
  if (analyticsCharts) {
    renderChart("analyticsTypeChart", {
      type: "bar",
      data: {
        labels: (analyticsCharts.documents_by_type || []).map((item) => item.label),
        datasets: [{ label: "Documents", data: (analyticsCharts.documents_by_type || []).map((item) => item.value), backgroundColor: "#2563eb" }],
      },
      options: { plugins: { legend: { display: false } } },
    });
    renderChart("analyticsTrendChart", {
      type: "line",
      data: {
        labels: (analyticsCharts.daily_processing_trend || []).map((item) => item.label),
        datasets: [{ label: "Documents", data: (analyticsCharts.daily_processing_trend || []).map((item) => item.value), borderColor: "#0ea5e9", tension: 0.35 }],
      },
      options: { plugins: { legend: { display: false } } },
    });
  }
})();
