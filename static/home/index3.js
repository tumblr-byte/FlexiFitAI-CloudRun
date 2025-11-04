  // Slide-in animation
        gsap.from(".form-card", {duration: 1, y: -50, opacity: 0, ease: "power3.out"});

        const fileInput = document.querySelector('input[type="file"]');
        const uploadIcon = document.getElementById('uploadIcon');
        const previewImg = document.getElementById('previewImg');

        // Click icon to open file picker
        uploadIcon.addEventListener('click', function() {
            fileInput.click();
        });

        // Show preview when file selected
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImg.setAttribute('src', e.target.result);
                    previewImg.style.display = 'block';
                }
                reader.readAsDataURL(file);
            } else {
                previewImg.style.display = 'none';
            }
        });