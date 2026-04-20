document.addEventListener("DOMContentLoaded", function() {
    
    // --- 1. GESTION DE L'AFFICHAGE (IP vs VIDEO) ---
    const cameraSelect = document.getElementById('camera_source');
    const ipUrlGroup = document.getElementById('ip_url_group');
    const videoUploadGroup = document.getElementById('video_upload_group');
    const ipUrlInput = document.getElementById('ip_url');
    const videoFileInput = document.getElementById('video_file');

    // Changer l'affichage selon le choix de la source
    cameraSelect.addEventListener('change', function() {
        ipUrlGroup.style.display = 'none';
        videoUploadGroup.style.display = 'none';
        
        if (this.value === 'ip') {
            ipUrlGroup.style.display = 'block';
        } else if (this.value === 'video') {
            videoUploadGroup.style.display = 'block';
        }
    });

    // --- 2. CHARGEMENT DES DONNEES AU DEMARRAGE ---
    let currentSavedVideoPath = ""; // Pour mémoriser la vidéo si on l'a déjà envoyée

    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            document.getElementById('sensitivity').value = data.sensitivity || 5;
            document.getElementById('confidence').value = data.confidence || 70;
            document.getElementById('alerts_enabled').checked = data.alerts_enabled;
            document.getElementById('alert_delay').value = data.alert_delay || 10;
            
            if (data.scan_mode) document.getElementById('scan_mode').value = data.scan_mode;
            if (data.data_retention) document.getElementById('data_retention').value = data.data_retention;

            // Détecter la bonne source de caméra (PC, IP, ou Fichier vidéo)
            if (data.camera_source === "0" || data.camera_source === "1") {
                cameraSelect.value = data.camera_source;
            } 
            else if (data.camera_source && data.camera_source.startsWith("http")) {
                cameraSelect.value = "ip";
                ipUrlGroup.style.display = 'block';
                ipUrlInput.value = data.camera_source;
            } 
            else if (data.camera_source) {
                // C'est un fichier vidéo local
                cameraSelect.value = "video";
                videoUploadGroup.style.display = 'block';
                currentSavedVideoPath = data.camera_source;
            }
        })
        .catch(err => console.error("Erreur de chargement des paramètres:", err));


    // --- 3. SAUVEGARDE ET UPLOAD ---
    const saveBtn = document.getElementById('saveSettings');

    saveBtn.addEventListener('click', function() {
        this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Traitement...';
        this.style.pointerEvents = 'none';
        
        // Fonction interne pour envoyer le JSON final au serveur
        const sendFinalSettings = (finalCameraSource) => {
            const newSettings = {
                sensitivity: document.getElementById('sensitivity').value,
                confidence: document.getElementById('confidence').value,
                alerts_enabled: document.getElementById('alerts_enabled').checked,
                alert_delay: document.getElementById('alert_delay').value,
                scan_mode: document.getElementById('scan_mode').value,
                data_retention: document.getElementById('data_retention').value,
                camera_source: finalCameraSource
            };

            fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newSettings)
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === "success") {
                    this.innerHTML = '<i class="fa-solid fa-check"></i> IA Mise à jour !';
                    this.style.background = 'rgba(52, 211, 153, 0.2)'; 
                    this.style.color = '#34d399';
                    this.style.borderColor = 'rgba(52, 211, 153, 0.5)';
                    this.style.boxShadow = '0 0 25px rgba(52, 211, 153, 0.4)';

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
            .catch(() => {
                this.innerHTML = 'Erreur serveur';
                this.style.pointerEvents = 'auto';
            });
        };

        // Logique de vérification (Vidéo vs IP vs Webcam)
        if (cameraSelect.value === 'video') {
            // Si l'utilisateur a uploadé un nouveau fichier
            if (videoFileInput.files.length > 0) {
                this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Upload de la vidéo...';
                let formData = new FormData();
                formData.append("video_file", videoFileInput.files[0]);
                
                fetch('/api/upload_video', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if (data.status === "success") {
                        currentSavedVideoPath = data.filepath; // On mémorise la nouvelle vidéo
                        sendFinalSettings(data.filepath);
                    } else {
                        alert("Erreur lors de l'upload de la vidéo.");
                        this.innerHTML = 'Enregistrer les modifications';
                        this.style.pointerEvents = 'auto';
                    }
                });
            } else {
                // Si on a choisi "Vidéo" mais sans mettre de nouveau fichier, on utilise l'ancien
                sendFinalSettings(currentSavedVideoPath || "0");
            }
        } 
        else if (cameraSelect.value === 'ip') {
            sendFinalSettings(ipUrlInput.value);
        } 
        else {
            sendFinalSettings(cameraSelect.value); // Webcam 0 ou 1
        }
    });
});