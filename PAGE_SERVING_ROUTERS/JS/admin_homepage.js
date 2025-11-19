import { showLoading, verifyAuth, handleLogout } from './shared/auth-utils.js';

const toastHost = document.getElementById('toast');
const cards = document.querySelectorAll('.card');
const logoutBtn = document.getElementById('logoutBtn');

(function initAuth() {
  showLoading(true);
  verifyAuth();
})();

cards.forEach(card => {
  card.addEventListener('click', function() {
    const page = this.dataset.page;
    handleCardClick(page);
  });

  card.addEventListener('mouseenter', function() {
    this.style.transition = 'all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1)';
  });
});

function handleCardClick(page) {
  const pageMap = {
    'analytics': {
      title: 'Analytics',
      url: '/admin/analytics'
    },
    'blogs': {
      title: 'Blogs',
      url: '/admin/blogs'
    },
    'case-studies': {
      title: 'Case Studies',
      url: '/admin/case-studies'
    },
    'admin-users': {
      title: 'Admin Users',
      url: '/admin/users'
    }
  };

  const pageInfo = pageMap[page];
  if (pageInfo) {
    toast(`Navigating to ${pageInfo.title}...`);
    setTimeout(() => {
      window.location.href = pageInfo.url;
    }, 800);
  }
}

function toast(message, type) {
  const host = toastHost || document.getElementById('toast');
  if (!host) return;
  
  const el = document.createElement('div');
  el.className = 'msg' + (type === 'error' ? ' error' : '');
  el.textContent = message;
  host.appendChild(el);
  
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(6px)';
  }, 2200);
  
  setTimeout(() => {
    if (el.parentNode) host.removeChild(el);
  }, 2700);
}

if (logoutBtn) {
  logoutBtn.addEventListener('click', handleLogout);
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    const toastMessages = toastHost.querySelectorAll('.msg');
    toastMessages.forEach(msg => {
      msg.style.opacity = '0';
      msg.style.transform = 'translateY(6px)';
      setTimeout(() => {
        if (msg.parentNode) toastHost.removeChild(msg);
      }, 300);
    });
  }
});