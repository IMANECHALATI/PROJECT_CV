let emotionChart = null;

// =====================================
// INITIALISATION
// =====================================
document.addEventListener("DOMContentLoaded", function () {
    fetchStats();

    setInterval(fetchStats, 2000);
});

// =====================================
// FETCH API
// =====================================
function fetchStats() {
    fetch("/api/stats")
        .then(response => response.json())
        .then(data => {
            updateUI(data);
            updateChart(data.emotions);
        })
        .catch(error => {
            console.log("Error:", error);
        });
}

// =====================================
// UPDATE UI
// =====================================
function updateUI(data) {

    // Total customers
    document.getElementById("totalFaces").innerText =
        data.total_faces;

    // Satisfaction score
    document.getElementById("satisfactionScore").innerText =
        data.satisfaction_score + "%";

    document.getElementById("satisfactionGauge").innerText =
        data.satisfaction_score + "%";

    // Current emotion
    const current = data.current_emotion;

    const icons = {
        angry: "",
        happy: "",
        neutral: "",
        sad: "",
        surprise: ""
    };

    document.getElementById("currentEmotionIcon").innerText =
        icons[current.emotion] || "";

    document.getElementById("currentEmotionText").innerText =
        current.emotion.toUpperCase();

    const confidencePercent =
        Math.round(current.confidence * 100);

    document.getElementById("currentConfidenceBar").style.width =
        confidencePercent + "%";

    document.getElementById("currentConfidenceText").innerText =
        "Confidence: " + confidencePercent + "%";

    // Emotion stats
    const container =
        document.getElementById("emotionStatsContainer");

    container.innerHTML = "";

    for (const [emotion, stats] of Object.entries(data.emotions)) {

        const row = `
            <div class="mb-2">

                <div class="d-flex justify-content-between">
                    <span>${emotion}</span>
                    <span>${stats.count} (${stats.percentage}%)</span>
                </div>

                <div class="progress">
                    <div
                        class="progress-bar"
                        style="
                            width:${stats.percentage}%;
                            background-color:${stats.color};
                        ">
                    </div>
                </div>

            </div>
        `;

        container.innerHTML += row;
    }

    // Alert
    if (
        current.emotion === "angry" &&
        current.confidence > 0.70
    ) {
        document.getElementById("alertCard").style.display =
            "block";
    } else {
        document.getElementById("alertCard").style.display =
            "none";
    }
}

// =====================================
// UPDATE CHART
// =====================================
function updateChart(emotions) {

    const ctx =
        document.getElementById("emotionChart").getContext("2d");

    const labels = Object.keys(emotions);

    const values =
        labels.map(label => emotions[label].percentage);

    const colors =
        labels.map(label => emotions[label].color);

    if (emotionChart) {

        emotionChart.data.labels = labels;
        emotionChart.data.datasets[0].data = values;
        emotionChart.update();

    } else {

        emotionChart = new Chart(ctx, {
            type: "bar",

            data: {
                labels: labels,

                datasets: [{
                    label: "Emotion Distribution (%)",
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors,
                    borderWidth: 1
                }]
            },

            options: {
                responsive: true,

                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
}

// =====================================
// RESET
// =====================================
function resetStats() {
    fetch("/api/reset_stats", {
        method: "POST"
    })
    .then(() => fetchStats());
}