document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.admin-desc').forEach(function(el){
    const btn = document.createElement('button')
    btn.className = 'admin-see-more'
    btn.textContent = 'See more'
    btn.addEventListener('click', function(){
      el.classList.toggle('expanded')
      btn.textContent = el.classList.contains('expanded') ? 'See less' : 'See more'
    })
    el.parentNode.insertBefore(btn, el.nextSibling)
  })
})
