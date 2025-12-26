document.addEventListener('DOMContentLoaded', function () {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', function () {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('active');
        });

        const links = navLinks.querySelectorAll('a:not(.dropdown-toggle)');
        links.forEach(link => {
            link.addEventListener('click', function () {
                hamburger.classList.remove('active');
                navLinks.classList.remove('active');
            });
        });
    }

    const dropdown = document.querySelector('.dropdown');
    const dropdownToggle = document.querySelector('.dropdown-toggle');

    if (dropdown && dropdownToggle) {
        dropdownToggle.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.innerWidth <= 768) {
                dropdown.classList.toggle('active');
            }
        });

        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 768 && !dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
            }
        });
    }
});

document.getElementById('contactForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const form = this;
    const submitBtn = form.querySelector('.submit-btn');
    const originalBtnText = submitBtn.textContent;

    submitBtn.textContent = 'Sending...';
    submitBtn.disabled = true;

    const templateParams = {
        title: "New Contact Form Submission",
        name: form.name.value,
        email: form.email.value,
        phone: form.phone.value,
        service: form.service.options[form.service.selectedIndex].text,
        message: form.message.value,
        time: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
    };

    try {
        await emailjs.send("service_wkbsrmi", "template_q6h4zks", templateParams);
        form.reset();
        const currentParams = window.location.search;
        window.location.href = '/thank-you' + currentParams;
    } catch (error) {
        console.error('Error submitting form:', error);
        alert('An error occurred. Please try again later.');
        submitBtn.textContent = originalBtnText;
        submitBtn.disabled = false;
    }
});