document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.admin-desc').forEach(function(el){
    const btn = document.createElement('button')
    btn.className = 'admin-see-more'
    btn.textContent = 'Дэлгэрэнгүй'
    btn.addEventListener('click', function(){
      el.classList.toggle('expanded')
      btn.textContent = el.classList.contains('expanded') ? 'Бага' : 'Дэлгэрэнгүй'
    })
    el.parentNode.insertBefore(btn, el.nextSibling)
  })

  // feature toggle handling
  document.querySelectorAll('.feature-toggle').forEach(function(cb){
    cb.addEventListener('change', function(e){
      const bookId = cb.getAttribute('data-book-id')
      const featured = cb.checked ? 1 : 0
      fetch(`/admin/books/${bookId}/feature`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ featured })
      }).then(resp=>{
        if(!resp.ok){
          alert('Failed to update featured flag')
          cb.checked = !cb.checked
        }
      }).catch(()=>{
        alert('Failed to update featured flag')
        cb.checked = !cb.checked
      })
    })
  })
})
