document.addEventListener("DOMContentLoaded", function() {
    
    // 1. Charger les paramètres actuels depuis le backend au démarrage de la page
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            document.getElementById('sensitivity').value = data.sensitivity;
            document.getElementById('confidence').value = data.confidence;
            document.getElementById('alerts_enabled').checked = data.alerts_enabled;
            document.getElementById('alert_delay').value = data.alert_delay;
        })
        .catch(err => console.error("Erreur de chargement des paramètres:", err));


    // 2. Sauvegarder les nouveaux paramètres quand on clique sur le bouton
    const saveBtn = document.getElementById('saveSettings');

    saveBtn.addEventListener('click', function() {
        // Animation du bouton
        this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sauvegarde en cours...';
        this.style.pointerEvents = 'none';
        
        // Récupération des valeurs saisies par l'utilisateur
        const newSettings = {
            sensitivity: document.getElementById('sensitivity').value,
            confidence: document.getElementById('confidence').value,
            alerts_enabled: document.getElementById('alerts_enabled').checked,
            alert_delay: document.getElementById('alert_delay').value
        };

        // Envoi au backend Python
        fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(newSettings)
        })
        .then(response => response.json())
        .then(data => {
            if(data.status === "success") {
                // Succès ! Animation du bouton en vert (style Royal)
                this.innerHTML = '<i class="fa-solid fa-check"></i> IA Mise à jour !';
                this.style.background = 'rgba(52, 211, 153, 0.2)'; 
                this.style.color = '#34d399';
                this.style.borderColor = 'rgba(52, 211, 153, 0.5)';
                this.style.boxShadow = '0 0 25px rgba(52, 211, 153, 0.4)';

                // Remise à l'état normal après 2.5 secondes
                setTimeout(() => {
                    this.innerHTML = 'Enregistrer les modifications';
                    this.style.background = '';
                    this.style.color = '';
                    this.style.borderColor = '';
                    this.style.boxShadow = '';
                    this.style.pointerEvents = 'auto';
                }, 2500);
            }
        })
        .catch(err => {
            console.error("Erreur lors de la sauvegarde :", err);
            this.innerHTML = 'Erreur de sauvegarde';
        });
    });
});