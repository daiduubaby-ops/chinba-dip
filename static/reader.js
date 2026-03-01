document.addEventListener('DOMContentLoaded', function(){
  const pages = window.PAGES || []
  const reader = document.getElementById('reader')
  const pageNum = document.getElementById('pageNum')
  const pageInput = document.getElementById('pageInput')
  const pageOf = document.getElementById('pageOf')
  const prev = document.getElementById('prev')
  const next = document.getElementById('next')
  const toggleSingle = document.getElementById('toggleSingle')
  const fullscreenBtn = document.getElementById('fullscreenBtn')

  let pageIndex = 0
  let singlePageMode = false
  let animating = false
  let _prevSingleMode = null

  function clampIndex(i){
    return Math.max(0, Math.min(i, Math.max(0, pages.length - 1)))
  }

  function render(){
    if(!reader) return
    reader.innerHTML = ''
    // in Chrome when in fullscreen element there can be vendor prefixed pseudo-classes
    // ensure reader uses correct layout; style adjustments handled via template CSS
    if(singlePageMode){
      const single = document.createElement('div')
      single.className = 'page single'
      if(pages.length > pageIndex){
        const img = document.createElement('img')
        img.src = pages[pageIndex]
        single.appendChild(img)
      }
      reader.appendChild(single)
    } else {
      const left = document.createElement('div')
      left.className = 'page'
      const right = document.createElement('div')
      right.className = 'page'

      if(pages.length > pageIndex){
        const img = document.createElement('img')
        img.src = pages[pageIndex]
        left.appendChild(img)
      }
      if(pages.length > pageIndex + 1){
        const img = document.createElement('img')
        img.src = pages[pageIndex + 1]
        right.appendChild(img)
      }
      reader.appendChild(left)
      reader.appendChild(right)
    }

    if(pageNum) pageNum.textContent = (pageIndex + 1)
    if(pageInput) pageInput.value = (pageIndex + 1)
    if(pageOf) pageOf.textContent = '/ ' + (pages.length || 0)

    if(prev) prev.disabled = (pageIndex <= 0)
    if(next) next.disabled = (pageIndex + (singlePageMode ? 1 : 2) > pages.length - 1)
  }

  function animateFlip(direction, updateFn){
    console.log('[reader] animateFlip called', {direction, pageIndex, singlePageMode, animating, pagesLen: pages.length})
    if(animating) return
    const canMove = direction === 'next'
      ? (singlePageMode ? (pageIndex + 1 < pages.length) : (pageIndex + 2 < pages.length))
      : (singlePageMode ? (pageIndex - 1 >= 0) : (pageIndex - 2 >= 0))
    if(!canMove) return
    animating = true

    // If in single-page mode, animate the single page element out/in instead of using reader-level flip
    if(singlePageMode){
      const current = reader && reader.querySelector('.page')
      if(!current){ animating = false; return }
      // add outgoing class
      const outCls = direction === 'next' ? 'single-out-next' : 'single-out-prev'
      console.log('[reader] single-page outgoing class:', outCls)
      current.classList.add(outCls)
      // after outgoing animation, update content and animate incoming
      setTimeout(function(){
        try{ updateFn() }catch(e){}
        // render new page
        render()
        const incoming = reader && reader.querySelector('.page')
        if(incoming){
          console.log('[reader] adding single-in to incoming')
          incoming.classList.add('single-in')
          setTimeout(function(){ incoming.classList.remove('single-in'); animating = false }, 420)
        } else {
          animating = false
        }
      }, 420)
      return
    }

    // two-page mode: perform a JS-driven 3D flip so it's visible in fullscreen and across browsers
    try{
      const pagesEls = reader ? Array.from(reader.querySelectorAll('.page')) : []
      const leftEl = pagesEls[0]
      const rightEl = pagesEls[1]
      const duration = 520
      const easing = 'cubic-bezier(.2,.8,.2,1)'
      if(leftEl && rightEl){
        // prepare styles
        leftEl.style.transition = `transform ${duration}ms ${easing}, opacity ${duration}ms ${easing}`
        rightEl.style.transition = `transform ${duration}ms ${easing}, opacity ${duration}ms ${easing}`
        leftEl.style.transformOrigin = 'left center'
        rightEl.style.transformOrigin = 'right center'
        // ensure starting state for incoming page
        rightEl.style.transform = 'rotateY(90deg) translateZ(-200px)'
        rightEl.style.opacity = '0'
        // force layout then animate
        void leftEl.offsetWidth
        // animate left out, right in
        leftEl.style.transform = 'rotateY(-120deg) translateZ(-280px)'
        leftEl.style.opacity = '0'
        rightEl.style.transform = 'rotateY(0deg) translateZ(0)'
        rightEl.style.opacity = '1'

        setTimeout(function(){
          try{ updateFn() }catch(e){}
          // cleanup inline styles and re-render to ensure correct DOM
          leftEl.style.transition = ''
          rightEl.style.transition = ''
          leftEl.style.transform = ''
          rightEl.style.transform = ''
          leftEl.style.opacity = ''
          rightEl.style.opacity = ''
          animating = false
          render()
        }, duration + 20)
        return
      }
    }catch(e){ console.error('[reader] two-page JS flip failed', e) }
    // fallback: use class-based approach if JS-driven flip fails
    const cls = direction === 'next' ? 'flip-next' : 'flip-prev'
    if(reader){ try{ reader.classList.add(cls) }catch(e){}}
    setTimeout(function(){ try{ updateFn() }catch(e){} if(reader){ try{ reader.classList.remove(cls) }catch(e){} } animating = false; render() }, 520)
  }

  if(prev) prev.addEventListener('click', function(){
    console.log('prev clicked', {pageIndex, singlePageMode})
    animateFlip('prev', function(){ if(singlePageMode) pageIndex = clampIndex(pageIndex - 1); else pageIndex = clampIndex(pageIndex - 2) })
  })
  if(next) next.addEventListener('click', function(){
    console.log('next clicked', {pageIndex, singlePageMode})
    // extra debug: show reader class list before animate
    try{ console.log('[reader-debug] before animate, reader.classList=', reader && reader.classList ? Array.from(reader.classList) : null) }catch(e){}
    animateFlip('next', function(){ if(singlePageMode) pageIndex = clampIndex(pageIndex + 1); else pageIndex = clampIndex(pageIndex + 2) })
    // after: log current classList (will show after animation start)
    setTimeout(function(){ try{ console.log('[reader-debug] after animate, reader.classList=', reader && reader.classList ? Array.from(reader.classList) : null) }catch(e){} }, 20)
  })

  if(pageInput){
    pageInput.addEventListener('change', function(){
      let v = parseInt(pageInput.value, 10) || 1
      v = Math.max(1, Math.min(v, pages.length || 1))
      pageIndex = clampIndex(v - 1)
      render()
    })
  }

  window.addEventListener('keydown', function(e){
    if(e.key === 'ArrowLeft'){
      if(singlePageMode){ if(pageIndex - 1 >= 0){ pageIndex = clampIndex(pageIndex - 1); render() } }
      else { if(pageIndex - 2 >= 0){ pageIndex = clampIndex(pageIndex - 2); render() } }
    } else if(e.key === 'ArrowRight'){
      if(singlePageMode){ if(pageIndex + 1 < pages.length){ pageIndex = clampIndex(pageIndex + 1); render() } }
      else { if(pageIndex + 2 < pages.length){ pageIndex = clampIndex(pageIndex + 2); render() } }
    }
  })

  if(toggleSingle) toggleSingle.addEventListener('click', function(){
    singlePageMode = !singlePageMode
    // show current mode on the button: "Нэг хуудас" when in single-page mode, "Хоёр хуудас" when in two-page mode
    toggleSingle.textContent = singlePageMode ? 'Нэг хуудас' : 'Хоёр хуудас'
    if(!singlePageMode){ pageIndex = Math.max(0, pageIndex - (pageIndex % 2)) }
    render()
  })

  if(fullscreenBtn) fullscreenBtn.addEventListener('click', function(){
    const el = document.getElementById('reader')
    if(!el) return
    try{
      if(document.fullscreenElement === el){
        document.exitFullscreen().catch(()=>{})
      } else {
        // request fullscreen on the reader element
        if(el.requestFullscreen){ el.requestFullscreen() }
        else if(el.webkitRequestFullscreen){ el.webkitRequestFullscreen() }
        else if(el.msRequestFullscreen){ el.msRequestFullscreen() }
      }
    }catch(e){}
  })

  // When entering/exiting fullscreen, ensure page alignment but do NOT force a mode
  // so the user can toggle single/two page while in fullscreen. This keeps both
  // single-page and two-page modes functional in fullscreen.
  document.addEventListener('fullscreenchange', function(){
    const el = document.getElementById('reader')
    if(document.fullscreenElement === el){
      // entering fullscreen: if currently in two-page mode make sure left page index is even
      if(!singlePageMode){ pageIndex = Math.max(0, pageIndex - (pageIndex % 2)) }
      render()
    } else {
      // exiting fullscreen: no automatic mode change, just re-render
      render()
    }
  })

  // initial render
  render()
})
