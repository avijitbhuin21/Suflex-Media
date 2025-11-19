import { showLoading, verifyAuth, handleLogout, authenticatedFetch } from './shared/auth-utils.js';
import { showModal, closeModal } from './shared/ui-utils.js';

const toastHost = document.getElementById('toast');
const backBtn = document.getElementById('backBtn');
const logoutBtn = document.getElementById('logoutBtn');
const addUserBtn = document.getElementById('addUserBtn');
const statusFilter = document.getElementById('statusFilter');
const usersList = document.getElementById('usersList');

const addUserModal = document.getElementById('addUserModal');
const addUserForm = document.getElementById('addUserForm');
const closeAddModal = document.getElementById('closeAddModal');
const cancelAddBtn = document.getElementById('cancelAddBtn');

const updatePasswordModal = document.getElementById('updatePasswordModal');
const updatePasswordForm = document.getElementById('updatePasswordForm');
const closeUpdateModal = document.getElementById('closeUpdateModal');
const cancelUpdateBtn = document.getElementById('cancelUpdateBtn');

const confirmModal = document.getElementById('confirmModal');
const closeConfirmModal = document.getElementById('closeConfirmModal');
const cancelConfirmBtn = document.getElementById('cancelConfirmBtn');
const confirmActionBtn = document.getElementById('confirmActionBtn');

let allUsers = [];
let currentAction = null;

async function loadUsers() {
  try {
    const res = await authenticatedFetch("/api/admin-users", {
      method: "GET"
    });

    if (!res.ok) {
      throw new Error("Failed to load users");
    }

    const data = await res.json();
    allUsers = data.users || [];
    renderUsers();
  } catch (err) {
    console.error("Error loading users:", err);
    toast("Failed to load users", "error");
    usersList.innerHTML = '<div class="loading-placeholder"><p>Failed to load users</p></div>';
  }
}

function renderUsers() {
  const filterValue = statusFilter.value;
  let filteredUsers = allUsers;

  if (filterValue === 'active') {
    filteredUsers = allUsers.filter(user => user.active);
  } else if (filterValue === 'inactive') {
    filteredUsers = allUsers.filter(user => !user.active);
  }

  if (filteredUsers.length === 0) {
    usersList.innerHTML = '<div class="loading-placeholder"><p>No users found</p></div>';
    return;
  }

  usersList.innerHTML = filteredUsers.map(user => `
    <div class="user-card" data-user-id="${user.id}">
      <div class="user-header">
        <div class="user-info">
          <h3 class="user-name">${escapeHtml(user.username)}</h3>
        </div>
        <span class="status-badge ${user.active ? 'status-active' : 'status-inactive'}">
          ${user.active ? 'Active' : 'Inactive'}
        </span>
      </div>
      <div class="user-actions">
        <button class="action-btn" data-action="update" data-user-id="${user.id}" data-username="${escapeHtml(user.username)}">
          Update Password
        </button>
        <button class="action-btn ${user.active ? 'deactivate' : 'activate'}" 
                data-action="${user.active ? 'deactivate' : 'activate'}" 
                data-user-id="${user.id}"
                data-username="${escapeHtml(user.username)}">
          ${user.active ? 'Deactivate' : 'Activate'}
        </button>
        <button class="action-btn delete" data-action="delete" data-user-id="${user.id}" data-username="${escapeHtml(user.username)}">
          Delete
        </button>
      </div>
    </div>
  `).join('');

  attachUserActionListeners();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function attachUserActionListeners() {
  const actionButtons = document.querySelectorAll('.action-btn');
  actionButtons.forEach(btn => {
    btn.addEventListener('click', handleUserAction);
  });
}

function handleUserAction(e) {
  const action = e.target.dataset.action;
  const userId = e.target.dataset.userId;
  const username = e.target.dataset.username;

  switch(action) {
    case 'update':
      openUpdatePasswordModal(userId, username);
      break;
    case 'activate':
      openConfirmModal('activate', userId, username);
      break;
    case 'deactivate':
      openConfirmModal('deactivate', userId, username);
      break;
    case 'delete':
      openConfirmModal('delete', userId, username);
      break;
  }
}

function openUpdatePasswordModal(userId, username) {
  document.getElementById('updateUserId').value = userId;
  document.getElementById('updateUsername').textContent = username;
  document.getElementById('updatePassword').value = '';
  showModal(updatePasswordModal);
}

function openConfirmModal(action, userId, username) {
  currentAction = { action, userId, username };
  const confirmTitle = document.getElementById('confirmTitle');
  const confirmMessage = document.getElementById('confirmMessage');

  switch(action) {
    case 'activate':
      confirmTitle.textContent = 'Activate User';
      confirmMessage.textContent = `Are you sure you want to activate user "${username}"? They will be able to log in.`;
      break;
    case 'deactivate':
      confirmTitle.textContent = 'Deactivate User';
      confirmMessage.textContent = `Are you sure you want to deactivate user "${username}"? They will not be able to log in.`;
      break;
    case 'delete':
      confirmTitle.textContent = 'Delete User';
      confirmMessage.textContent = `Are you sure you want to delete user "${username}"? This action cannot be undone.`;
      break;
  }

  showModal(confirmModal);
}

async function handleAddUser(e) {
  e.preventDefault();
  
  const username = document.getElementById('newUsername').value.trim();
  const email = document.getElementById('newEmail').value.trim();
  const password = document.getElementById('newPassword').value;

  if (!username || !email || !password) {
    toast("All fields are required", "error");
    return;
  }

  try {
    const res = await authenticatedFetch("/api/admin-users", {
      method: "POST",
      body: JSON.stringify({ username, email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Failed to create user");
    }

    toast("Admin user created successfully", "success");
    closeModal(addUserModal);
    addUserForm.reset();
    await loadUsers();
  } catch (err) {
    console.error("Error creating user:", err);
    toast(err.message || "Failed to create user", "error");
  }
}

async function handleUpdatePassword(e) {
  e.preventDefault();
  
  const userId = document.getElementById('updateUserId').value;
  const newPassword = document.getElementById('updatePassword').value;

  if (!newPassword) {
    toast("Password is required", "error");
    return;
  }

  try {
    const res = await authenticatedFetch(`/api/admin-users/${userId}`, {
      method: "PUT",
      body: JSON.stringify({ password: newPassword })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Failed to update password");
    }

    toast("Password updated successfully", "success");
    closeModal(updatePasswordModal);
    updatePasswordForm.reset();
  } catch (err) {
    console.error("Error updating password:", err);
    toast(err.message || "Failed to update password", "error");
  }
}

async function handleConfirmAction() {
  if (!currentAction) return;

  const { action, userId, username } = currentAction;

  try {
    let res;
    
    if (action === 'delete') {
      res = await authenticatedFetch(`/api/admin-users/${userId}`, {
        method: "DELETE"
      });
    } else {
      const newStatus = action === 'activate';
      res = await authenticatedFetch(`/api/admin-users/${userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ active: newStatus })
      });
    }

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || `Failed to ${action} user`);
    }

    toast(`User ${action}d successfully`, "success");
    closeModal(confirmModal);
    currentAction = null;
    await loadUsers();
  } catch (err) {
    console.error(`Error ${action} user:`, err);
    toast(err.message || `Failed to ${action} user`, "error");
  }
}

function toast(message, type) {
  const host = toastHost || document.getElementById('toast');
  if (!host) return;
  
  const el = document.createElement('div');
  el.className = 'msg' + (type === 'error' ? ' error' : type === 'success' ? ' success' : '');
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

backBtn.addEventListener('click', () => {
  window.location.href = '/admin';
});

if (logoutBtn) {
  logoutBtn.addEventListener('click', handleLogout);
}

addUserBtn.addEventListener('click', () => {
  showModal(addUserModal);
});

closeAddModal.addEventListener('click', () => {
  closeModal(addUserModal);
});

cancelAddBtn.addEventListener('click', () => {
  closeModal(addUserModal);
});

addUserForm.addEventListener('submit', handleAddUser);

closeUpdateModal.addEventListener('click', () => {
  closeModal(updatePasswordModal);
});

cancelUpdateBtn.addEventListener('click', () => {
  closeModal(updatePasswordModal);
});

updatePasswordForm.addEventListener('submit', handleUpdatePassword);

closeConfirmModal.addEventListener('click', () => {
  closeModal(confirmModal);
  currentAction = null;
});

cancelConfirmBtn.addEventListener('click', () => {
  closeModal(confirmModal);
  currentAction = null;
});

confirmActionBtn.addEventListener('click', handleConfirmAction);

statusFilter.addEventListener('change', renderUsers);

addUserModal.addEventListener('click', (e) => {
  if (e.target === addUserModal) {
    closeModal(addUserModal);
  }
});

updatePasswordModal.addEventListener('click', (e) => {
  if (e.target === updatePasswordModal) {
    closeModal(updatePasswordModal);
  }
});

confirmModal.addEventListener('click', (e) => {
  if (e.target === confirmModal) {
    closeModal(confirmModal);
    currentAction = null;
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal(addUserModal);
    closeModal(updatePasswordModal);
    closeModal(confirmModal);
    currentAction = null;
  }
});

(async function init() {
  showLoading(true);
  const authSuccess = await verifyAuth();
  if (authSuccess) {
    await loadUsers();
  }
})();