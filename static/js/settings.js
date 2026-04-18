document.addEventListener("DOMContentLoaded", function() {
    
    const saveBtn = document.getElementById('saveSettings');

    saveBtn.addEventListener('click', function() {
        // 1. On change l'état en "Chargement"
        this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sauvegarde Royal...';
        this.style.pointerEvents = 'none'; // Empêche de cliquer 2 fois
        
        // 2. On simule un appel API au backend
        setTimeout(() => {
            // 3. Succès ! On met le bouton en vert émeraude
            this.innerHTML = '<i class="fa-solid fa-check"></i> Enregistré avec succès !';
            this.style.background = 'rgba(52, 211, 153, 0.2)'; // Vert happy
            this.style.color = '#34d399';
            this.style.borderColor = 'rgba(52, 211, 153, 0.5)';
            this.style.boxShadow = '0 0 25px rgba(52, 211, 153, 0.4)';

            // 4. On remet le bouton à son état normal après 2.5 secondes
            setTimeout(() => {
                this.innerHTML = 'Enregistrer les modifications Premium';
                this.style.background = ''; // Revient au CSS
                this.style.color = '';
                this.style.borderColor = '';
                this.style.boxShadow = '';
                this.style.pointerEvents = 'auto';
            }, 2500);
            
        }, 1000); // Faux délai pour l'UX
    });
});