document.addEventListener("DOMContentLoaded", function () {
    
    // --- 1. CONFIGURATION DU GRAPHIQUE (Royal Theme) ---
    const ctx = document.getElementById('emotionChart').getContext('2d');
    
    const colors = {
        'angry': '#ef4444',    // Rouge
        'disgust': '#d97706',  // Marron/Orange
        'fear': '#8b5cf6',     // Violet
        'happy': '#34d399',    // Vert émeraude (Royal)
        'neutral': '#94a3b8',  // Gris ardoise
        'sad': '#3b82f6',      // Bleu royal
        'surprise': '#f59e0b'  // Or
    };

    let emotionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Colère', 'Dégoût', 'Peur', 'Joie', 'Neutre', 'Tristesse', 'Surprise'],
            datasets: [{
                data: [0, 0, 0, 0, 0, 0, 0],
                backgroundColor: Object.values(colors),
                borderWidth: 3,
                borderColor: '#1a3a2d', 
                hoverOffset: 15
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: { position: 'bottom', labels: { color: '#f5eeda', padding: 25, font: { family: 'Inter', size: 14, weight: '600' } } },
                tooltip: { backgroundColor: 'rgba(18, 42, 33, 0.95)', titleFont: { size: 16, weight: '700' }, bodyFont: { size: 14 }, padding: 15, cornerRadius: 12 }
            }
        }
    });

    // --- 2. SYSTÈME DE TOAST ET ENVOI D'EMAIL ---
    let lastAlertTime = 0;
    const alertSound = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
    
    function showToast() {
        const now = Date.now();
        // Empêcher le spam : 1 alerte toutes les 20 secondes max
        if (now - lastAlertTime < 20000) return; 
        lastAlertTime = now;

        // 1. Jouer le son
        alertSound.play().catch(e => console.log("Son bloqué"));

        // 2. Afficher la notification visuelle
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color: #ef4444; font-size: 2rem;"></i>
                           <div>
                               <strong style="display: block; font-size: 1.25rem;">Alerte Mécontentement</strong>
                               <span style="font-size: 1rem; color: #d9d1c1;">Colère détectée ! Un email a été envoyé.</span>
                           </div>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 500);
        }, 7000);

        // 3. NOUVEAU : Déclencher l'envoi de l'email au compte connecté
        fetch('/api/send_alert_email', { method: 'POST' })
            .then(response => response.json())
            .then(data => console.log("Statut Email:", data.message))
            .catch(err => console.error("Erreur Email:", err));
    }

    // --- 3. MISE À JOUR EN TEMPS RÉEL (Stats) ---
    function fetchStats() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                document.getElementById('totalFaces').innerText = data.total_customers;
                document.getElementById('satisfactionScore').innerText = data.satisfaction_score + '%';
                
                const statusEl = document.getElementById('currentEmotion');
                if (data.current_emotion.face_detected) {
                    const emo = data.current_emotion.emotion;
                    statusEl.innerText = emo.toUpperCase();
                    statusEl.style.color = colors[emo];
                } else {
                    statusEl.innerText = "Recherche...";
                    statusEl.style.color = "#94a3b8";
                }

                // Déclenchement de l'alerte depuis le backend
                if (data.current_emotion.alert) {
                    showToast();
                }

                const emos = data.emotions;
                emotionChart.data.datasets[0].data = [
                    emos.angry.count, emos.disgust.count, emos.fear.count,
                    emos.happy.count, emos.neutral.count, emos.sad.count, emos.surprise.count
                ];
                emotionChart.update();
            })
            .catch(err => console.error("API Error :", err));
    }

    setInterval(fetchStats, 1000);

    // --- 4. BOUTON RESET (AVEC SMART SUMMARY) ---
    document.getElementById('resetBtn').addEventListener('click', function() {
        this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Clôture...';
        
        fetch('/api/reset_stats', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                setTimeout(() => {
                    this.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Reset Session';
                    fetchStats();
                }, 500);

                if (data.summary && data.summary.trim() !== "") {
                    prompt("📋 Bilan de Service généré avec succès.\nCopiez ce texte pour votre manager :", data.summary);
                }
            });
    });
});