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

    const form = document.getElementById('contactForm');
    const submitBtn = form.querySelector('.submit-btn');
    const requiredFields = form.querySelectorAll('[required]');

    function validateForm() {
        let isValid = true;

        requiredFields.forEach(field => {
            if (field.type === 'checkbox') {
                if (!field.checked) {
                    isValid = false;
                }
            } else if (field.tagName === 'SELECT') {
                if (!field.value || field.value === '') {
                    isValid = false;
                }
            } else {
                if (!field.value.trim()) {
                    isValid = false;
                }
            }
        });

        submitBtn.disabled = !isValid;

        if (isValid) {
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
        } else {
            submitBtn.style.opacity = '0.6';
            submitBtn.style.cursor = 'not-allowed';
        }
    }

    requiredFields.forEach(field => {
        field.addEventListener('input', validateForm);
        field.addEventListener('change', validateForm);
    });

    validateForm();
});

document.getElementById('contactForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const form = this;
    const submitBtn = form.querySelector('.submit-btn');
    const originalBtnText = submitBtn.textContent;

    const nameValue = form.name.value.trim();
    const emailValue = form.email.value.trim();
    const phoneValue = form.phone.value.trim();
    const serviceValue = form.service.value;
    const messageValue = form.message.value.trim();
    const termsChecked = form.terms.checked;
    const consentChecked = form.consent.checked;

    if (!nameValue) {
        alert('Please enter your name.');
        return;
    }
    if (!emailValue) {
        alert('Please enter your email.');
        return;
    }
    if (!phoneValue) {
        alert('Please enter your phone number.');
        return;
    }
    if (!serviceValue) {
        alert('Please select a service.');
        return;
    }
    if (!messageValue) {
        alert('Please enter a message.');
        return;
    }
    if (!termsChecked) {
        alert('Please agree to the Terms of Service.');
        return;
    }


    submitBtn.textContent = 'Sending...';
    submitBtn.disabled = true;

    const templateParams = {
        title: "New Contact Form Submission",
        name: nameValue,
        email: emailValue,
        phone: phoneValue,
        service: form.service.options[form.service.selectedIndex].text,
        message: messageValue,
        time: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
    };

    try {
        await emailjs.send("service_suflexmedia", "template_utfeunq", templateParams);
        form.reset();
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.6';
        submitBtn.style.cursor = 'not-allowed';
        const currentParams = window.location.search;
        window.location.href = '/thank-you' + currentParams;
    } catch (error) {
        console.error('Error submitting form:', error);
        alert('An error occurred. Please try again later.');
        submitBtn.textContent = originalBtnText;
        submitBtn.disabled = false;
    }
});