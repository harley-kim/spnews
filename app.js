const state={items:[],brand:'ALL',type:'all',query:''};
const $=s=>document.querySelector(s);
const BRAND_ICONS={
  'TAMRON':'https://www.tamron.com/favicon.ico',
  'Voigtlander':'https://www.cosina.co.jp/favicon.ico',
  'Kenko':'https://www.kenko-tokina.co.jp/favicon.ico',
  'Tokina':'https://www.kenko-tokina.co.jp/favicon.ico',
  'SLIK':'https://slik.com/favicon.ico',
  'BOYA':'https://www.boyamic.com/favicon.ico',
  'Celestron':'https://www.celestron.com/favicon.ico',
  'Sky-Watcher':'https://skywatcher.com/favicon.ico',
  'DOMKE':'https://tiffen.com/favicon.ico',
  'KODAK':'https://www.kodak.com/favicon.ico',
  'HEIPI':'https://heipivision.com/favicon.ico',
  'SUNWAYFOTO':'https://www.sunwayfoto.com/favicon.ico',
  'COLBOR':'https://www.colborlight.com/favicon.ico',
  'NEEWER':'https://neewer.com/favicon.ico',
  'Gura Gear':'https://guragear.com/favicon.ico'
};
const fmt=d=>{try{return new Intl.DateTimeFormat('ko-KR',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(d))}catch{return d||''}};
function escapeHtml(v=''){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function brands(){return ['ALL',...new Set(state.items.map(x=>x.brand).filter(Boolean))]}
function brandVisual(brand){const src=BRAND_ICONS[brand];return src?`<img src="${src}" alt="" loading="lazy" onerror="this.remove()"><span>${escapeHtml(brand)}</span>`:`<span>${escapeHtml(brand||'SP NEWS')}</span>`}
function renderBrands(){const root=$('#brandChips');root.innerHTML=brands().map(b=>`<button class="brand-chip ${state.brand===b?'active':''}" data-brand="${escapeHtml(b)}">${b==='ALL'?'전체 브랜드':escapeHtml(b)}</button>`).join('');root.querySelectorAll('button').forEach(btn=>btn.addEventListener('click',()=>{state.brand=btn.dataset.brand;renderBrands();render()}))}
function filtered(){const q=state.query.trim().toLowerCase();return state.items.filter(x=>{const brand=state.brand==='ALL'||x.brand===state.brand;const type=state.type==='all'||x.type===state.type;const hay=[x.title,x.summary,x.brand,x.source].join(' ').toLowerCase();return brand&&type&&(!q||hay.includes(q))}).sort((a,b)=>new Date(b.published_at)-new Date(a.published_at))}
function card(x){const type=x.type==='video'?'video':'news';return `<a class="card" href="${escapeHtml(x.url)}" target="_blank" rel="noopener noreferrer"><div class="card-brand">${brandVisual(x.brand)}</div><div class="card-body"><div class="meta"><span class="badge ${type}">${type==='video'?'YOUTUBE':'NEWS'}</span><span>${escapeHtml(fmt(x.published_at))}</span></div><h3>${escapeHtml(x.title)}</h3><p class="summary">${escapeHtml(x.summary||'원문에서 자세한 내용을 확인하세요.')}</p></div><div class="card-side"><span class="source">${escapeHtml(x.source||'Original')}</span><span class="arrow">↗</span></div></a>`}
function render(){const items=filtered();$('#timeline').innerHTML=items.map(card).join('');$('#resultCount').textContent=`${items.length.toLocaleString('ko-KR')}개의 소식`;$('#emptyState').hidden=items.length>0}
async function boot(){try{const res=await fetch(`./data/news.json?v=${Date.now()}`);if(!res.ok)throw new Error('data load failed');const data=await res.json();state.items=data.items||[];$('#lastUpdated').textContent=data.updated_at?fmt(data.updated_at):'업데이트 정보 없음';renderBrands();render()}catch(e){console.error(e);$('#lastUpdated').textContent='데이터 준비 중';$('#emptyState').hidden=false;$('#emptyState strong').textContent='뉴스 데이터를 불러오지 못했습니다.'}}
$('#searchInput').addEventListener('input',e=>{state.query=e.target.value;render()});
$('#typeTabs').querySelectorAll('button').forEach(btn=>btn.addEventListener('click',()=>{$('#typeTabs .active')?.classList.remove('active');btn.classList.add('active');state.type=btn.dataset.type;render()}));
boot();