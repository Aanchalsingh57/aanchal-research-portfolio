'use strict';
document.documentElement.classList.add('js');
const toggle=document.querySelector('.menu-toggle');
const nav=document.querySelector('#navigation');
if(toggle&&nav){
 const close=()=>{nav.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');};
 toggle.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(open));nav.classList.toggle('is-open',open);});
 nav.addEventListener('click',event=>{if(event.target.closest('a'))close();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&toggle.getAttribute('aria-expanded')==='true'){close();toggle.focus();}});
 document.addEventListener('click',event=>{if(!event.target.closest('.site-header'))close();});
}
const links=[...document.querySelectorAll('#navigation a[href*="#"]')];
if('IntersectionObserver' in window){
 const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){links.forEach(link=>{const active=new URL(link.href).hash==='#'+entry.target.id;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');});}});},{rootMargin:'-15% 0px -55% 0px'});
 document.querySelectorAll('section[id]').forEach(section=>observer.observe(section));
}
document.querySelectorAll('.admin-sidebar nav a').forEach(link=>{if(new URL(link.href).pathname===location.pathname){link.classList.add('active');link.setAttribute('aria-current','page');}});
document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',event=>{if(!window.confirm(form.dataset.confirm))event.preventDefault();}));
document.querySelectorAll('form[method="post"]').forEach(form=>form.addEventListener('submit',event=>{if(event.defaultPrevented||!form.checkValidity())return;const button=form.querySelector('[type="submit"],input[type="submit"]');if(button){button.disabled=true;form.setAttribute('aria-busy','true');}}));
