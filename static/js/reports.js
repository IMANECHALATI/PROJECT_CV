let emotionPieChart = null;
let weeklyTrendChart = null;
let heatmapChart = null;

document.addEventListener("DOMContentLoaded", function () {
    setDefaultDates();
    generateReport();
    loadAvailableCSVFiles();
});

function setDefaultDates() {
    const today = new Date();
    const old = new Date();

    old.setDate(today.getDate() - 7);

    document.getElementById("startDate").value =
        old.toISOString().split("T")[0];

    document.getElementById("endDate").value =
        today.toISOString().split("T")[0];
}

function generateReport() {
    const startDate = document.getElementById("startDate").value;
    const endDate = document.getElementById("endDate").value;

    const dataSource =
        document.querySelector('input[name="dataSource"]:checked')?.value ||
        "online";

    showLoading(true);

    fetch(`/api/report?start=${startDate}&end=${endDate}&source=${dataSource}`)
        .then(response => response.json())
        .then(data => {
            updateSummary(data);
            updateCharts(data);
            updateTable(data);
            updateExportButtons();
            showLoading(false);
        })
        .catch(error => {
            console.error(error);
            alert("Unable to load report");
            showLoading(false);
        });
}

function updateSummary(data) {
    document.getElementById("totalCustomers").innerText =
        data.total_customers || 0;

    const satisfaction = data.satisfaction_rate || 0;

    document.getElementById("satisfactionRate").innerHTML = `
        <div class="progress" style="height:25px;">
            <div class="progress-bar bg-success"
                 style="width:${satisfaction}%">
                ${satisfaction}%
            </div>
        </div>
    `;

    document.getElementById("peakHour").innerText =
        data.peak_negative_hour || "--:--";

    document.getElementById("totalAlerts").innerText =
        data.total_alerts || 0;
}

function updateCharts(data) {
    const emotions = data.emotion_distribution || {};

    if (emotionPieChart) emotionPieChart.destroy();

    const pieCtx =
        document.getElementById("emotionPieChart").getContext("2d");

    emotionPieChart = new Chart(pieCtx, {
        type: "pie",
        data: {
            labels: Object.keys(emotions).map(e => e.toUpperCase()),
            datasets: [{
                data: Object.values(emotions),
                backgroundColor: [
                    "#28a745",
                    "#17a2b8",
                    "#dc3545",
                    "#ffc107",
                    "#6f42c1"
                ],
                borderWidth: 1,
                borderColor: "#fff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        font: { size: 10 },
                        boxWidth: 10
                    }
                }
            }
        }
    });

    const weekly = data.weekly_trend || [];

    if (weeklyTrendChart) weeklyTrendChart.destroy();

    const weeklyCtx =
        document.getElementById("weeklyTrendChart").getContext("2d");

    weeklyTrendChart = new Chart(weeklyCtx, {
        type: "line",
        data: {
            labels: weekly.map(x => x.day),
            datasets: [
                {
                    label: "Satisfaction %",
                    data: weekly.map(x => x.satisfaction),
                    borderColor: "#28a745",
                    fill: false,
                    tension: 0.3
                },
                {
                    label: "Negative %",
                    data: weekly.map(x => x.negative_rate || 0),
                    borderColor: "#dc3545",
                    fill: false,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });

    const hourly = data.hourly_data || [];

    if (heatmapChart) heatmapChart.destroy();

    const heatmapCtx =
        document.getElementById("heatmapChart").getContext("2d");

    heatmapChart = new Chart(heatmapCtx, {
        type: "bar",
        data: {
            labels: hourly.map(x => x.hour + "h"),
            datasets: [
                {
                    label: "Angry",
                    data: hourly.map(x => x.angry || 0),
                    backgroundColor: "rgba(220,53,69,0.7)"
                },
                {
                    label: "Sad",
                    data: hourly.map(x => x.sad || 0),
                    backgroundColor: "rgba(255,193,7,0.7)"
                },
                {
                    label: "Happy",
                    data: hourly.map(x => x.happy || 0),
                    backgroundColor: "rgba(40,167,69,0.7)"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });
}

function updateTable(data) {
    const tbody = document.getElementById("reportTableBody");
    tbody.innerHTML = "";

    const rows = data.daily_data || [];

    if (rows.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center small">
                    No data for selected period
                </td>
            </tr>
        `;
        return;
    }

    rows.forEach(row => {
        const satisfactionColor =
            row.satisfaction >= 70
                ? "success"
                : row.satisfaction >= 50
                ? "warning"
                : "danger";

        tbody.innerHTML += `
            <tr>
                <td><strong>${row.date}</strong></td>
                <td>${row.happy || 0}</td>
                <td>${row.neutral || 0}</td>
                <td>${row.angry || 0}</td>
                <td>${row.sad || 0}</td>
                <td>${row.surprise || 0}</td>
                <td>
                    <div class="progress" style="height:20px;">
                        <div class="progress-bar bg-${satisfactionColor}"
                             style="width:${row.satisfaction}%">
                            ${row.satisfaction}%
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });
}

function exportReport(format = "csv") {
    const startDate = document.getElementById("startDate").value;
    const endDate = document.getElementById("endDate").value;

    window.location.href =
        `/api/export_report?start=${startDate}&end=${endDate}&format=${format}`;
}

function printReport() {
    window.print();
}

function loadAvailableCSVFiles() {
    fetch("/api/list_csv_files")
        .then(response => response.json())
        .then(files => {
            const select = document.getElementById("csvFileSelect");

            if (select && files.length > 0) {
                select.innerHTML =
                    `<option value="">Select file</option>`;

                files.forEach(file => {
                    select.innerHTML += `
                        <option value="${file}">
                            ${file}
                        </option>
                    `;
                });
            }
        })
        .catch(error => console.error(error));
}

function uploadCSV() {
    const fileInput = document.getElementById("csvUpload");
    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a CSV file first");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    showLoading(true);

    fetch("/api/upload_csv", {
        method: "POST",
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Successfully uploaded ${data.rows} rows`);
                loadAvailableCSVFiles();
                generateReport();
            } else {
                alert("Upload failed");
            }

            showLoading(false);
        })
        .catch(error => {
            console.error(error);
            showLoading(false);
        });
}

function loadCSVFile() {
    const filename =
        document.getElementById("csvFileSelect").value;

    if (!filename) return;

    showLoading(true);

    fetch(`/api/load_csv_file?filename=${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSummary(data.data);
                updateCharts(data.data);
                updateTable(data.data);
            }

            showLoading(false);
        });
}

function downloadTemplate() {
    window.location.href = "/api/download_csv_template";
}

function updateExportButtons() {}

function showLoading(show) {
    const loader = document.getElementById("loadingOverlay");

    if (loader) {
        loader.style.display = show ? "flex" : "none";
    }
}