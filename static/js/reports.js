document.addEventListener("DOMContentLoaded", function() {
    const ctx = document.getElementById('trendChart').getContext('2d');

    // On récupère les données dynamiques de l'API historique
    fetch('/api/report')
        .then(res => res.json())
        .then(data => {
            
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
                            ticks: { color: '#f5eeda', font: { size: 14 } } 
                        },
                        x: { 
                            grid: { display: false }, 
                            ticks: { color: '#f5eeda', font: { size: 14 } } 
                        }
                    }
                }
            });

            // --- 2. REMPLISSAGE DU TABLEAU HISTORIQUE ---
            const tableBody = document.getElementById('reportTableBody');
            data.daily_data.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.date}</td>
                    <td>15 Clients</td>
                    <td><span class="badge-satisfaction">${row.satisfaction}%</span></td>
                    <td><span class="badge-alert">2</span></td>
                `;
                tableBody.appendChild(tr);
            });
        });
});