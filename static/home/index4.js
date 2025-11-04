  const profile = document.querySelector('.nav-item.profile img');
    const dropdown = document.querySelector('.profile-dropdown');
    const closeBtn = document.querySelector('.close-dropdown');
    let dropdownOpen = false;

    // Show dropdown on profile click
    profile.addEventListener('click', () => {
      if (!dropdownOpen) {
        gsap.to(dropdown, { duration: 0.4, opacity: 1, y: 0, ease: "power2.out" });
        dropdown.style.pointerEvents = "auto";
        dropdownOpen = true;
      }
    });

    // Close dropdown with X icon
    closeBtn.addEventListener('click', () => {
      gsap.to(dropdown, { duration: 0.3, opacity: 0, y: -10, ease: "power2.in" });
      dropdown.style.pointerEvents = "none";
      dropdownOpen = false;
    });

    // Optional: close if clicked outside
    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target) && !profile.contains(e.target)) {
        gsap.to(dropdown, { duration: 0.3, opacity: 0, y: -10, ease: "power2.in" });
        dropdown.style.pointerEvents = "none";
        dropdownOpen = false;
      }
    });

    // Animate logo text on load
    gsap.from(".app-name", {duration: 1, opacity: 0, x: -20, ease: "power2.out"});