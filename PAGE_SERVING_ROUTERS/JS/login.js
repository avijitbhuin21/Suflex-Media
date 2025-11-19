(function(){
  const loginForm = document.getElementById('loginForm');
  const toastHost = document.getElementById('toast');

  function setCookie(name, value, days = 365) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Strict`;
  }

  function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
      let c = ca[i];
      while (c.charAt(0) === ' ') c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  }

  function deleteCookie(name) {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
  }

  document.querySelectorAll('.field input').forEach(inp=>{
    const fld = inp.parentElement;
    inp.addEventListener('blur', ()=>{
      fld.classList.add('shrink');
      setTimeout(()=> fld.classList.remove('shrink'), 350);
    });
  });

  (function autoLoginOnLoad(){
    const hashedEmail = getCookie('hashed_email');
    const hashedPassword = getCookie('hashed_password');
    
    if(hashedEmail && hashedPassword){
      console.log("Found stored credentials in cookies, attempting auto-login...");
      
      document.querySelectorAll('.field').forEach(field => {
        field.style.display = 'none';
      });
      
      loading(loginForm, true, "Authenticating...");
      
      autoLogin(hashedEmail, hashedPassword).then(success=>{
        if(success){
          console.log("✓ Auto-login successful, redirecting...");
          toast("Welcome back! Redirecting...");
          setTimeout(()=> location.replace("/admin"), 800);
        }else{
          console.log("✗ Auto-login failed, clearing stored credentials");
          deleteCookie('hashed_email');
          deleteCookie('hashed_password');
          
          document.querySelectorAll('.field').forEach(field => {
            field.style.display = '';
          });
          
          loading(loginForm, false);
        }
      }).catch(()=>{
        console.log("✗ Auto-login error, clearing stored credentials");
        deleteCookie('hashed_email');
        deleteCookie('hashed_password');
        
        document.querySelectorAll('.field').forEach(field => {
          field.style.display = '';
        });
        
        loading(loginForm, false);
      });
    }
  })();

  if (loginForm){
    loginForm.addEventListener('submit', async (e)=>{
      e.preventDefault();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value.trim();
      if(!email || !password){ toast("Please fill all fields","error"); return; }
      loading(loginForm, true, "Logging in...");
      try{
        const res = await fetch("/api/login",{
          method:"POST",
          headers:{ "Content-Type":"application/json", "Accept":"application/json" },
          body: JSON.stringify({ email, password }),
          credentials: 'include'
        });
        if(!res.ok){ throw new Error("Login failed"); }
        const data = await res.json();
        console.log("✓ Login successful");
        
        setCookie('hashed_email', data.hashed_email, 365);
        setCookie('hashed_password', data.hashed_password, 365);
        console.log("✓ Hashed credentials stored in cookies");
        
        if (data.access_token) {
          localStorage.setItem('authToken', data.access_token);
          console.log("✓ JWT access token stored in localStorage");
        }
        
        toast("Login successful. Redirecting...");
        setTimeout(()=> {
          console.log("Redirecting to admin home page...");
          window.location.href = "/admin";
        }, 800);
      }catch(err){
        toast(err.message || "Login error","error");
      }finally{
        loading(loginForm, false);
      }
    });
  }

  async function autoLogin(hashedEmail, hashedPassword){
    try{
      console.log("Attempting auto-login with stored hashed credentials...");
      const res = await fetch("/api/auto-login",{
        method:"POST",
        headers:{ "Content-Type":"application/json", "Accept":"application/json" },
        body: JSON.stringify({
          hashed_email: hashedEmail,
          hashed_password: hashedPassword
        }),
        credentials: 'include'
      });
      console.log("Auto-login response status:", res.status);
      if(!res.ok) return false;
      const data = await res.json().catch(()=>null);
      console.log("Auto-login result:", data && data.status === "success");
      
      if (data && data.status === "success" && data.access_token) {
        localStorage.setItem('authToken', data.access_token);
        console.log("✓ JWT access token stored in localStorage");
      }
      
      return !!(data && data.status === "success");
    }catch(err){
      console.error("Error during auto-login:", err);
      return false;
    }
  }

  function loading(form, on, label){
    const btn = form.querySelector('button.primary');
    if(!btn) return;
    if(on){
      btn.disabled = true;
      btn.dataset._text = btn.textContent;
      btn.innerHTML = '<span class="spinner"></span>'+(label||'Working...');
    }else{
      btn.disabled = false;
      btn.textContent = btn.dataset._text || 'Continue';
    }
  }

  function toast(message, type){
    const host = toastHost || document.getElementById('toast');
    if(!host) return;
    const el = document.createElement('div');
    el.className = 'msg' + (type==='error'?' error':'');
    el.textContent = message;
    host.appendChild(el);
    setTimeout(()=>{ el.style.opacity='0'; el.style.transform='translateY(6px)'; }, 2200);
    setTimeout(()=> { if(el.parentNode) host.removeChild(el); }, 2700);
  }

})();