// // theme_modal.js - Fixed for local Bootstrap
// (function () {
//   "use strict";

//   /* ---------------------------
//      Helpers / constants
//   ----------------------------*/
//   const VALID = ['light','dark','system'];
//   const STORAGE_KEY = 'mv-theme';
  
//   // Wait for Bootstrap to be available
//   let settingsModal = null;
//   let bootstrapLoaded = false;

//   function initializeBootstrap() {
//     if (typeof bootstrap !== 'undefined') {
//       const settingsModalEl = document.getElementById('settingsModal');
//       if (settingsModalEl) {
//         settingsModal = new bootstrap.Modal(settingsModalEl);
//       }
//       bootstrapLoaded = true;
//     }
//   }

//   function log(...args){ try { console.log('[theme_modal]', ...args); } catch(e){} }

//   /* ---------------------------
//      Detect preferred initial theme
//   ----------------------------*/
//   function getInitialTheme(){
//     try {
//       if (window.MV && window.MV.loggedIn && window.MV.serverTheme) {
//         if (VALID.includes(window.MV.serverTheme)) return window.MV.serverTheme;
//       }
//       const stored = localStorage.getItem(STORAGE_KEY);
//       if (stored && VALID.includes(stored)) return stored;
//       const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
//       return prefersDark ? 'dark' : 'light';
//     } catch(e){
//       return 'light';
//     }
//   }

//   /* ---------------------------
//      Apply theme to documentElement
//   ----------------------------*/
//   function applyTheme(t){
//     document.documentElement.classList.remove('light-theme','dark-theme');
//     if (t === 'dark') {
//       document.documentElement.classList.add('dark-theme');
//     } else {
//       document.documentElement.classList.add('light-theme');
//     }
//     log('Applied theme ->', t);
//   }

//   /* ---------------------------
//      Save theme
//   ----------------------------*/
//   async function saveTheme(theme){
//     try {
//       if (!VALID.includes(theme)) return;
//       localStorage.setItem(STORAGE_KEY, theme);
//       log('Saved locally:', theme);

//       if (window.MV && window.MV.loggedIn === true) {
//         try {
//           const resp = await fetch('/set_theme', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({ theme: theme }),
//             credentials: 'same-origin'
//           });
//           if (!resp.ok) log('Server theme save failed', resp.status);
//           else log('Server theme saved');
//         } catch(err) {
//           log('Error saving theme to server', err);
//         }
//       }
//     } catch(e){
//       log('saveTheme error', e);
//     }
//   }

//   /* ---------------------------
//      UI wiring for modal cards
//   ----------------------------*/
//   function setupModalUI(){
//     const cards = Array.from(document.querySelectorAll('.theme-card'));
//     const saveBtn = document.getElementById('settings-save-btn');

//     function markSelected(theme){
//       cards.forEach(c => {
//         if (c.dataset.theme === theme) {
//           c.classList.add('selected');
//           c.setAttribute('aria-pressed','true');
//         } else {
//           c.classList.remove('selected');
//           c.setAttribute('aria-pressed','false');
//         }
//       });
//     }

//     // Initialize selection based on initial theme
//     const initial = getInitialTheme();
//     markSelected(initial);
//     applyTheme(initial);

//     // Card clicks
//     cards.forEach(c => {
//       c.addEventListener('click', () => {
//         const theme = c.dataset.theme;
//         markSelected(theme);
//       });
//     });

//     // Save button
//     if (saveBtn) {
//       saveBtn.addEventListener('click', () => {
//         const sel = document.querySelector('.theme-card.selected');
//         const theme = sel ? sel.dataset.theme : getInitialTheme();
//         if (!theme) return;
        
//         if (theme === 'system') {
//           const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
//           applyTheme(prefersDark ? 'dark' : 'light');
//         } else {
//           applyTheme(theme);
//         }
//         saveTheme(theme);
        
//         if (settingsModal && bootstrapLoaded) {
//           settingsModal.hide();
//         } else {
//           // Fallback for when Bootstrap is not available
//           const modalEl = document.getElementById('settingsModal');
//           if (modalEl) {
//             modalEl.classList.remove('show');
//             modalEl.style.display = 'none';
//           }
//         }
//       });
//     }
//   }

//   /* ---------------------------
//      Setup FAB click handler
//   ----------------------------*/
//   function setupFab(){
//     const settingsFab = document.getElementById('settings-fab');
//     if (!settingsFab) return;
    
//     settingsFab.addEventListener('click', (e) => {
//       e.preventDefault();
//       if (settingsModal && bootstrapLoaded) {
//         settingsModal.show();
//       } else {
//         // Fallback - manually show modal
//         const modalEl = document.getElementById('settingsModal');
//         if (modalEl) {
//           modalEl.classList.add('show');
//           modalEl.style.display = 'block';
//           modalEl.style.background = 'rgba(0,0,0,0.5)';
//         }
//       }
//     });
//   }

//   /* ---------------------------
//      Initialize everything
//   ----------------------------*/
//   function initializeApp() {
//     log('Initializing app...');
    
//     // Initialize Bootstrap
//     initializeBootstrap();
    
//     // If Bootstrap not loaded immediately, try again
//     if (!bootstrapLoaded) {
//       setTimeout(initializeBootstrap, 100);
//     }
    
//     setupFab();
//     setupModalUI();
    
//     // Apply initial theme
//     const initialTheme = getInitialTheme();
//     applyTheme(initialTheme);
    
//     log('App initialized successfully');
//   }

//   // Wait for DOM and Bootstrap to be ready
//   if (document.readyState === 'loading') {
//     document.addEventListener('DOMContentLoaded', initializeApp);
//   } else {
//     initializeApp();
//   }

// })();




// // // 3. Perfect Theme System
// // const themeCards = document.querySelectorAll('.theme-card');
// // const saveThemeBtn = document.getElementById('saveTheme');

// // function applyTheme(theme) {
// //   document.documentElement.className = theme + '-theme';
// //   localStorage.setItem('mv-theme', theme);
  
// //   // Update theme cards selection
// //   themeCards.forEach(card => {
// //     card.classList.remove('active');
// //     if (card.dataset.theme === theme) {
// //       card.classList.add('active');
// //     }
// //   });
// // }

// // // Theme card clicks
// // themeCards.forEach(card => {
// //   card.addEventListener('click', function() {
// //     const theme = this.dataset.theme;
// //     themeCards.forEach(c => c.classList.remove('active'));
// //     this.classList.add('active');
// //   });
// // });

// // // Save theme
// // if (saveThemeBtn) {
// //   saveThemeBtn.addEventListener('click', function() {
// //     const activeCard = document.querySelector('.theme-card.active');
// //     if (activeCard) {
// //       const theme = activeCard.dataset.theme;
// //       applyTheme(theme);
// //       settingsModal.classList.remove('active');
// //     }
// //   });
// // }

// // // Initialize with saved theme
// // const savedTheme = localStorage.getItem('mv-theme') || 'dark';
// // applyTheme(savedTheme);