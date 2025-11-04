     const profile = document.querySelector('.nav-item.profile');
        const dropdown = document.querySelector('.profile-dropdown');

        profile.addEventListener('mouseenter', () => {
            dropdown.classList.add('active');
            gsap.fromTo(dropdown, 
                {opacity: 0, y: -10}, 
                {opacity: 1, y: 0, duration: 0.5, ease: "power3.out"}
            );
        });

        profile.addEventListener('mouseleave', () => {
            gsap.to(dropdown, 
                {opacity: 0, y: -10, duration: 0.4, ease: "power3.in", onComplete: () => {
                    dropdown.classList.remove('active');
                }}
            );
        });