// Live suggestions for the nav search input (shared)
(function(){
  const input = document.getElementById('nav-search')
  const box = document.getElementById('nav-suggestions')
  if(!input || !box) return
  let timer = null
  function hide(){ box.style.display='none'; box.innerHTML = '' }
  function render(items){
    if(!items || items.length===0){ hide(); return }
    box.innerHTML = items.map(i=>`
      <a href="${location.origin}/books/${i.id}" style="display:flex;gap:8px;padding:8px 10px;align-items:center;text-decoration:none;color:#111">
        <div style="width:40px;height:56px;flex:0 0 40px;background:#f3f4f6;border-radius:4px;overflow:hidden">${i.image?`<img src='/static/uploads/${i.image}' style='width:100%;height:100%;object-fit:cover'/>`:''}</div>
        <div style='flex:1'><div style='font-weight:600'>${i.title}</div><div style='color:#6b7280;font-size:.9rem'>${i.author||''}</div></div>
      </a>
    `).join('')
    box.style.display = 'block'
  }
  input.addEventListener('input', function(){
    const q = input.value.trim()
    if(timer) clearTimeout(timer)
    if(!q){ hide(); return }
    timer = setTimeout(()=>{
      fetch(`/search/suggest?q=${encodeURIComponent(q)}`)
        .then(r=>r.json()).then(j=>{ render(j.suggestions || []) }).catch(()=>{ hide() })
    }, 180)
  })
  // Submit on Enter -> go to full search page
  input.addEventListener('keydown', function(e){
    if(e.key === 'Enter'){
      const q = input.value.trim()
      if(q) location.href = `${location.origin}/search?q=${encodeURIComponent(q)}`
    }
  })
  document.addEventListener('click', function(e){ if(!box.contains(e.target) && e.target !== input) hide() })
})()
