document.addEventListener("DOMContentLoaded", function() {
    const ctx = document.getElementById('trendChart').getContext('2d');

    // On récupère les VRAIES données historiques du serveur
    fetch('/api/report')
        .then(res => res.json())
        .then(data => {
            
            // Si aucune session n'a été sauvegardée
            if(data.weekly_trend.length === 0) {
                document.getElementById('reportTableBody').innerHTML = "<tr><td colspan='4' style='text-align:center;'>Aucune session enregistrée pour le moment. Allez sur le Dashboard, analysez, puis cliquez sur Reset.</td></tr>";
                return;
            }

            // --- 1. GRAPHIQUE DE TENDANCE (Or sur Vert Royal) ---
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.weekly_trend.map(d => d.day),
                    datasets: [{
                        label: 'Satisfaction %',
                        data: data.weekly_trend.map(d => d.satisfaction),
                        borderColor: '#e6b800', // Or Royal
                        backgroundColor: 'rgba(230, 184, 0, 0.1)', // Légère ombre or
                        fill: true,
                        tension: 0.4,
                        borderWidth: 4,
                        pointBackgroundColor: '#f5eeda', // Beige point
                        pointRadius: 6,
                        pointHoverRadius: 9
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { 
                            grid: { color: 'rgba(245, 238, 218, 0.05)' }, 
                            ticks: { color: '#f5eeda', font: { size: 14 } },
                            min: 0,
                            max: 100
                        },
                        x: { 
                            grid: { display: false }, 
                            ticks: { color: '#f5eeda', font: { size: 14 } } 
                        }
                    }
                }
            });

            // --- 2. REMPLISSAGE DYNAMIQUE DU TABLEAU ---
            const tableBody = document.getElementById('reportTableBody');
            data.daily_data.forEach(row => {
                const tr = document.createElement('tr');
                
                // Coloration du badge Alerte : Rouge si > 0, Gris si 0
                const alertBadgeColor = row.alerts > 0 ? 'background: rgba(239, 68, 68, 0.2); color: #fca5a5;' : 'background: rgba(148, 163, 184, 0.2); color: #94a3b8;';
                
                tr.innerHTML = `
                    <td>${row.date}</td>
                    <td><strong>${row.customers}</strong> Clients</td>
                    <td><span class="badge-satisfaction">${row.satisfaction}%</span></td>
                    <td><span class="badge-alert" style="${alertBadgeColor}">${row.alerts}</span></td>
                `;
                tableBody.appendChild(tr);
            });
        });
});