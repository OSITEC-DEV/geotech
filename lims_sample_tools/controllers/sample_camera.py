# -*- coding: utf-8 -*-
import json
import base64
from datetime import date

from odoo import http
from odoo.http import request


# ─────────────────────────────────────────────────────────────────────────────
#  Self-contained HTML page (all CSS + JS inlined)
#  Served at /lims/camera — no login required, works on any tablet browser.
# ─────────────────────────────────────────────────────────────────────────────

CAMERA_PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
<meta name="mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="theme-color" content="#0f1117"/>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📷</text></svg>"/>
<title>Sample Photos — LIMS</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:#0f1117}
:root{
  --bg:#0f1117;--bg2:#181c26;--bg3:#1e2332;
  --border:rgba(255,255,255,0.08);--border2:rgba(255,255,255,0.14);
  --text:#f0f2f8;--muted:#7a8099;
  --accent:#3b82f6;--green:#22c55e;--green-bg:rgba(34,197,94,0.12);
  --amber:#f59e0b;--amber-bg:rgba(245,158,11,0.12);--red:#ef4444;
  --font:'DM Sans',sans-serif;--mono:'DM Mono',monospace;--radius:14px;
}
#app{display:flex;flex-direction:column;height:100vh;font-family:var(--font);color:var(--text);background:var(--bg)}
/* topbar */
.topbar{flex-shrink:0;display:flex;align-items:center;gap:12px;padding:14px 16px;background:var(--bg2);border-bottom:1px solid var(--border)}
.topbar-icon{width:34px;height:34px;background:var(--accent);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0}
.topbar-title{font-size:16px;font-weight:600;letter-spacing:-0.3px}
.topbar-sub{font-size:11px;color:var(--muted);margin-top:1px}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:8px}
.badge-pending{background:var(--red);color:#fff;font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;display:none}
.refresh-btn{width:32px;height:32px;background:var(--bg3);border:1px solid var(--border2);border-radius:7px;color:var(--muted);display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;transition:color .15s}
.refresh-btn.spinning{animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
/* search bar */
.search-bar{flex-shrink:0;padding:10px 16px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;gap:8px}
.search-input{flex:1;background:var(--bg3);border:1px solid var(--border2);border-radius:9px;padding:9px 14px;font-family:var(--font);font-size:13px;color:var(--text);outline:none;transition:border-color .15s}
.search-input::placeholder{color:var(--muted)}
.search-input:focus{border-color:var(--accent)}
.search-clear{display:none;align-items:center;justify-content:center;width:34px;height:36px;background:var(--bg3);border:1px solid var(--border2);border-radius:9px;color:var(--muted);cursor:pointer;font-size:16px;flex-shrink:0}
.search-clear.visible{display:flex}
/* mode tabs */
.mode-tabs{flex-shrink:0;display:flex;border-bottom:1px solid var(--border);background:var(--bg2)}
.mode-tab{flex:1;padding:10px;text-align:center;font-size:12px;font-weight:500;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;transition:color .15s,border-color .15s}
.mode-tab.active{color:var(--accent);border-bottom-color:var(--accent)}
/* cards */
.cards-wrap{flex:1;overflow-y:auto;padding:14px 14px 90px;-webkit-overflow-scrolling:touch}
.cards-wrap::-webkit-scrollbar{display:none}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:10px}
.sample-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;display:flex;flex-direction:column;gap:9px;animation:cardIn .2s ease both}
@keyframes cardIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.sample-card.has-photos{border-color:rgba(34,197,94,0.3)}
.sample-card.search-result{border-color:rgba(59,130,246,0.4);background:rgba(59,130,246,0.04)}
.card-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.card-code{font-family:var(--mono);font-size:13px;font-weight:500;color:var(--accent)}
.card-state{font-size:10px;font-weight:600;padding:2px 7px;border-radius:20px;text-transform:uppercase;letter-spacing:.4px;flex-shrink:0}
.state-recieved{background:var(--amber-bg);color:var(--amber)}
.state-prepared{background:var(--green-bg);color:var(--green)}
.state-todo{background:rgba(239,68,68,.12);color:var(--red)}
.card-name{font-size:14px;font-weight:600;line-height:1.3}
.card-meta{font-size:11px;color:var(--muted);display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.card-category{padding:1px 7px;border-radius:5px;font-size:10px;font-weight:500;background:rgba(59,130,246,.12);color:var(--accent)}
/* thumbnail strip */
.thumb-strip{display:flex;gap:5px;overflow-x:auto;padding-bottom:2px;-webkit-overflow-scrolling:touch}
.thumb-strip::-webkit-scrollbar{display:none}
.thumb-img{width:54px;height:54px;border-radius:7px;object-fit:cover;flex-shrink:0;cursor:pointer;border:2px solid transparent;transition:border-color .15s}
.thumb-img:hover{border-color:var(--accent)}
/* camera button */
/* camera label acts as the button — direct gesture, no JS click() needed */
.camera-label{display:flex;align-items:center;justify-content:center;gap:6px;
  width:100%;padding:10px;border-radius:9px;
  font-family:var(--font);font-size:13px;font-weight:600;cursor:pointer;
  background:var(--accent);color:#fff;transition:opacity .15s;-webkit-tap-highlight-color:transparent}
.camera-label:active{opacity:.8}
.camera-label.done{background:var(--green-bg);color:var(--green);border:1px solid rgba(34,197,94,.25)}
.camera-input{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;overflow:hidden}
/* pagination */
.pagination{display:flex;align-items:center;justify-content:center;gap:10px;padding:14px;flex-shrink:0;border-top:1px solid var(--border);background:var(--bg2)}
.page-btn{padding:7px 16px;border-radius:8px;font-size:12px;font-weight:500;font-family:var(--font);border:1px solid var(--border2);background:var(--bg3);color:var(--text);cursor:pointer;transition:background .15s}
.page-btn:disabled{opacity:.35;cursor:default}
.page-btn:not(:disabled):hover{background:var(--border)}
.page-info{font-size:12px;color:var(--muted);min-width:80px;text-align:center}
/* empty / loading */
.empty-state{display:none;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:50px 20px;text-align:center;color:var(--muted)}
.empty-state.visible{display:flex}
.empty-icon{font-size:44px;opacity:.4}
.empty-title{font-size:15px;font-weight:600;color:var(--text)}
.empty-sub{font-size:12px;line-height:1.5}
.skeleton{background:linear-gradient(90deg,var(--bg2) 25%,var(--bg3) 50%,var(--bg2) 75%);background-size:200% 100%;animation:shimmer 1.2s infinite;border-radius:10px;height:180px}
@keyframes shimmer{from{background-position:200% 0}to{background-position:-200% 0}}
/* preview overlay */
#preview-overlay{display:none;position:fixed;inset:0;z-index:100;background:#000;flex-direction:column}
#preview-overlay.open{display:flex}
.preview-img-wrap{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;overflow:hidden;width:100%;background:#000}
#preview-img{max-width:100%;max-height:100%;object-fit:contain;display:block}
.preview-bar{flex-shrink:0;display:flex;gap:8px;padding:14px 16px;background:#0a0a0a;border-top:1px solid #222}
.preview-info{flex:1;display:flex;flex-direction:column;gap:2px;justify-content:center}
.preview-code{font-family:var(--mono);font-size:12px;color:var(--accent)}
.preview-name{font-size:13px;font-weight:500;color:var(--text)}
.btn-discard{padding:10px 16px;border-radius:9px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);color:#fff;font-family:var(--font);font-size:13px;font-weight:600;cursor:pointer}
.btn-save{padding:10px 20px;border-radius:9px;background:var(--green);border:none;color:#fff;font-family:var(--font);font-size:13px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:5px}
.btn-save:disabled{opacity:.5}
/* lightbox */
#lightbox{display:none;position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.97);flex-direction:column;align-items:center;justify-content:center}
#lightbox.open{display:flex}
#lightbox-img{max-width:100%;max-height:calc(100vh - 90px);object-fit:contain;border-radius:6px}
.lightbox-bar{position:absolute;bottom:0;left:0;right:0;padding:14px 16px;background:linear-gradient(transparent,rgba(0,0,0,0.9));display:flex;align-items:center;gap:10px}
.lightbox-info{flex:1}
.lb-code{font-family:var(--mono);font-size:12px;color:var(--accent)}
.lb-counter{font-size:11px;color:var(--muted);margin-top:2px}
.lb-close{position:absolute;top:14px;right:14px;width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,.1);border:none;color:#fff;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.lb-nav{position:absolute;top:50%;transform:translateY(-50%);width:42px;height:42px;border-radius:50%;background:rgba(255,255,255,.1);border:none;color:#fff;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.lb-prev{left:10px}.lb-next{right:10px}
/* toast */
#toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(80px);background:#1a1a2e;border:1px solid var(--border2);color:var(--text);padding:11px 18px;border-radius:11px;font-size:13px;font-weight:500;white-space:nowrap;transition:transform .3s cubic-bezier(.34,1.56,.64,1);z-index:300;display:flex;align-items:center;gap:7px}
#toast.show{transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>
<div id="app">
  <div class="topbar">
    <div class="topbar-icon">📷</div>
    <div>
      <div class="topbar-title">Sample Photos</div>
      <div class="topbar-sub" id="topbar-date"></div>
    </div>
    <div class="topbar-right">
      <span class="badge-pending" id="badge-pending"></span>
      <button class="refresh-btn" id="refresh-btn" title="Refresh">↻</button>
    </div>
  </div>
  <div class="search-bar">
    <input class="search-input" id="search-input" type="search" placeholder="Search by sample code…" autocomplete="off" autocorrect="off" spellcheck="false"/>
    <button class="search-clear" id="search-clear">✕</button>
  </div>
  <div class="mode-tabs">
    <div class="mode-tab active" data-mode="pending">📋 Pending Photos</div>
    <div class="mode-tab" data-mode="search">🔍 Search Result</div>
  </div>
  <div class="cards-wrap">
    <div class="cards-grid" id="cards-grid"></div>
    <div class="empty-state" id="empty-state">
      <div class="empty-icon">✅</div>
      <div class="empty-title" id="empty-title">All done!</div>
      <div class="empty-sub" id="empty-sub">No samples are waiting for photos.</div>
    </div>
  </div>
  <div class="pagination" id="pagination" style="display:none">
    <button class="page-btn" id="prev-btn">← Prev</button>
    <span class="page-info" id="page-info"></span>
    <button class="page-btn" id="next-btn">Next →</button>
  </div>
</div>

<div id="preview-overlay">
  <div class="preview-img-wrap">
    <img id="preview-img" src="" alt="Preview"/>
  </div>
  <div class="preview-bar">
    <div class="preview-info">
      <div class="preview-code" id="preview-code"></div>
      <div class="preview-name" id="preview-name"></div>
    </div>
    <button class="btn-discard" id="btn-discard">Retake</button>
    <button class="btn-save" id="btn-save"><span>💾</span> Save</button>
  </div>
</div>

<div id="lightbox">
  <button class="lb-close" id="lb-close">✕</button>
  <button class="lb-nav lb-prev" id="lb-prev">‹</button>
  <img id="lightbox-img" src="" alt=""/>
  <button class="lb-nav lb-next" id="lb-next">›</button>
  <div class="lightbox-bar">
    <div class="lightbox-info">
      <div class="lb-code" id="lb-code"></div>
      <div class="lb-counter" id="lb-counter"></div>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
(function(){
'use strict';

// ── State ────────────────────────────────────────────────────────────────────
var MODE_PENDING='pending', MODE_SEARCH='search';
var mode=MODE_PENDING;
var pendingSamples=[];       // current page from server
var searchSamples=[];        // search result (1 or few records)
var currentPage=1;
var totalPages=1;
var totalPending=0;
var PAGE_SIZE=20;
var searchTimer=null;
var pending={sampleId:null,sampleCode:null,sampleName:null,dataUrl:null};

// ── DOM ───────────────────────────────────────────────────────────────────────
var grid=document.getElementById('cards-grid');
var emptyState=document.getElementById('empty-state');
var emptyTitle=document.getElementById('empty-title');
var emptySub=document.getElementById('empty-sub');
var badgePending=document.getElementById('badge-pending');
var refreshBtn=document.getElementById('refresh-btn');
var searchInput=document.getElementById('search-input');
var searchClear=document.getElementById('search-clear');
var paginationEl=document.getElementById('pagination');
var prevBtn=document.getElementById('prev-btn');
var nextBtn=document.getElementById('next-btn');
var pageInfo=document.getElementById('page-info');
var previewOverlay=document.getElementById('preview-overlay');
var previewImg=document.getElementById('preview-img');
var previewCode=document.getElementById('preview-code');
var previewName=document.getElementById('preview-name');
var btnDiscard=document.getElementById('btn-discard');
var btnSave=document.getElementById('btn-save');
var toastEl=document.getElementById('toast');
var lbEl=document.getElementById('lightbox');
var lbImg=document.getElementById('lightbox-img');
var lbCode=document.getElementById('lb-code');
var lbCounter=document.getElementById('lb-counter');

document.getElementById('topbar-date').textContent=(new Date()).toLocaleDateString('en-GB',{weekday:'short',day:'numeric',month:'short'});

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(v){return String(v||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function stateLabel(s){return{todo:'To Collect',recieved:'Received',prepared:'Prepared',cancel:'Cancelled'}[s]||s;}
function stateClass(s){return'state-'+(s||'todo');}
function imgUrl(aid){return'/web/image/ir.attachment/'+aid+'/datas?width=120&height=120';}
function imgUrlFull(aid){return'/web/image/ir.attachment/'+aid+'/datas';}
function showToast(msg,emoji){
  toastEl.innerHTML='<span>'+(emoji||'')+'</span><span>'+msg+'</span>';
  toastEl.classList.add('show');
  setTimeout(function(){toastEl.classList.remove('show');},2800);
}

// ── JSON-RPC ──────────────────────────────────────────────────────────────────
function getCsrf(){var m=document.cookie.match(/\bsession_id=([^;]+)/);return m?m[1]:'';}
function rpc(url,params){
  return fetch(url,{
    method:'POST',credentials:'include',
    headers:{'Content-Type':'application/json','X-Openerp-Session-Id':getCsrf()},
    body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:params||{}})
  }).then(function(r){
    if(!r.ok)throw new Error('HTTP '+r.status);
    return r.json();
  }).then(function(d){
    if(d.error)throw new Error((d.error.data&&d.error.data.message)||d.error.message||'RPC error');
    return d.result;
  });
}

// ── Load pending (paginated, no-photo-only) ───────────────────────────────────
function loadPending(page){
  page=page||1;
  refreshBtn.classList.add('spinning');
  showSkeletons();
  rpc('/lims/camera/samples',{page:page,page_size:PAGE_SIZE}).then(function(data){
    pendingSamples=data.samples||[];
    totalPending=data.total||0;
    totalPages=Math.max(1,Math.ceil(totalPending/PAGE_SIZE));
    currentPage=page;
    if(mode===MODE_PENDING) renderCards(pendingSamples,false);
    updatePendingBadge();
  }).catch(function(e){
    showError(e.message);
  }).then(function(){refreshBtn.classList.remove('spinning');});
}

// ── Search ────────────────────────────────────────────────────────────────────
function doSearch(query){
  query=(query||'').trim();
  if(!query){switchMode(MODE_PENDING);return;}
  showSkeletons();
  rpc('/lims/camera/search',{query:query}).then(function(data){
    searchSamples=Array.isArray(data)?data:[];
    switchMode(MODE_SEARCH);
    renderCards(searchSamples,true);
  }).catch(function(e){showError(e.message);});
}

// ── Render ────────────────────────────────────────────────────────────────────
function showSkeletons(){
  grid.innerHTML='<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
  emptyState.classList.remove('visible');
  paginationEl.style.display='none';
}

function showError(msg){
  grid.innerHTML='<div style="grid-column:1/-1;padding:30px;text-align:center;color:#7a8099">'
    +'<div style="font-size:36px;margin-bottom:10px">❌</div>'
    +'<div style="font-size:14px;font-weight:600;color:#f0f2f8;margin-bottom:6px">Failed to load</div>'
    +'<div style="font-size:12px">'+esc(msg)+'</div>'
    +(msg.indexOf('401')!==-1||msg.indexOf('logged')!==-1
      ?'<a href="/web/login?redirect=/lims/camera" style="display:inline-block;margin-top:14px;padding:9px 20px;background:#3b82f6;color:#fff;border-radius:8px;text-decoration:none;font-weight:600">Login →</a>'
      :'')
    +'</div>';
  paginationEl.style.display='none';
}

function updatePendingBadge(){
  if(totalPending>0){badgePending.style.display='inline-flex';badgePending.textContent=totalPending+' pending';}
  else{badgePending.style.display='none';}
}

function thumbStrip(s){
  var ids=s.photo_ids||[];
  if(!ids.length) return '';
  return '<div class="thumb-strip" id="thumbs-'+s.id+'">'
    +ids.map(function(aid,i){
      return '<img class="thumb-img" src="'+imgUrl(aid)+'" onclick="openLightbox('+s.id+','+i+');" loading="lazy" alt="Photo '+(i+1)+'"/>';
    }).join('')+'</div>';
}

function renderCards(samples,isSearch){
  if(!samples.length){
    grid.innerHTML='';
    paginationEl.style.display='none';
    emptyState.classList.add('visible');
    if(isSearch){
      emptyTitle.textContent='No sample found';
      emptySub.textContent='Try a different sample code.';
    } else {
      emptyTitle.textContent='All done!';
      emptySub.textContent='No samples are waiting for photos.';
    }
    return;
  }
  emptyState.classList.remove('visible');
  grid.innerHTML=samples.map(function(s,i){
    var hp=s.photo_count>0;
    var cat=s.category?'<span style="width:3px;height:3px;border-radius:50%;background:rgba(255,255,255,.14);display:inline-block;margin:0 2px"></span><span class="card-category">'+esc(s.category)+'</span>':'';
    return '<div class="sample-card'+(hp?' has-photos':'')+(isSearch?' search-result':'')+'" style="animation-delay:'+(i*35)+'ms" data-id="'+s.id+'">'
      +'<div class="card-head"><span class="card-code">'+esc(s.name)+'</span>'
      +'<span class="card-state '+stateClass(s.state)+'">'+stateLabel(s.state)+'</span></div>'
      +'<div class="card-name">'+esc(s.sample_name||'—')+'</div>'
      +'<div class="card-meta">👤 '+esc(s.registered_by||'Unknown')+cat+'</div>'
      +thumbStrip(s)
      +'<label class="camera-label'+(hp?' done':'')+'" id="btn-'+s.id+'" for="input-'+s.id+'">'
      +'📷 '+(hp?'Add Another Photo':'Take Photo')+'</label>'
      +'<input class="camera-input" type="file" accept="image/*" capture="environment" '
      +'id="input-'+s.id+'" onchange="onChosen(this,'+s.id+');"/>'
      +'</div>';
  }).join('');

  // Pagination — only for pending mode
  if(!isSearch&&totalPages>1){
    paginationEl.style.display='flex';
    prevBtn.disabled=currentPage<=1;
    nextBtn.disabled=currentPage>=totalPages;
    pageInfo.textContent='Page '+currentPage+' / '+totalPages;
  } else {
    paginationEl.style.display='none';
  }
}

// ── Mode switching ────────────────────────────────────────────────────────────
function switchMode(m){
  mode=m;
  document.querySelectorAll('.mode-tab').forEach(function(t){
    t.classList.toggle('active', t.dataset.mode===m);
  });
  if(m===MODE_PENDING){
    renderCards(pendingSamples,false);
  }
}

// ── Camera ────────────────────────────────────────────────────────────────────
function getSampleById(id){
  var all=pendingSamples.concat(searchSamples);
  for(var i=0;i<all.length;i++){if(all[i].id===id) return all[i];}
  return null;
}
/* openCam removed — label[for] handles camera trigger natively */
window.onChosen=function(input,id){
  var file=input.files&&input.files[0];if(!file)return;
  var s=getSampleById(id);
  var reader=new FileReader();
  reader.onload=function(e){
    pending={sampleId:id,sampleCode:s?s.name:String(id),sampleName:s?(s.sample_name||''):'',dataUrl:e.target.result};
    previewImg.src=pending.dataUrl;
    previewCode.textContent=pending.sampleCode;
    previewName.textContent=pending.sampleName;
    previewOverlay.classList.add('open');
    btnSave.disabled=false;btnSave.innerHTML='<span>💾</span> Save';
  };
  reader.readAsDataURL(file);
  input.value='';
};

btnDiscard.addEventListener('click',function(){
  var id=pending.sampleId;
  previewOverlay.classList.remove('open');previewImg.src='';
  pending={sampleId:null,sampleCode:null,sampleName:null,dataUrl:null};
  if(id){var inp=document.getElementById('input-'+id);if(inp)inp.click();}
});

btnSave.addEventListener('click',function(){
  if(!pending.dataUrl||!pending.sampleId) return;
  btnSave.disabled=true;btnSave.innerHTML='<span>⏳</span> Saving…';
  var cap=JSON.parse(JSON.stringify(pending));
  rpc('/lims/camera/save',{sample_id:cap.sampleId,image_data:cap.dataUrl,filename:cap.sampleCode+'_'+Date.now()+'.jpg'})
  .then(function(result){
    if(result&&result.success){
      // Update local arrays
      [pendingSamples,searchSamples].forEach(function(arr){
        for(var i=0;i<arr.length;i++){
          if(arr[i].id===cap.sampleId){
            arr[i].photo_count=result.photo_count;
            arr[i].photo_ids=result.photo_ids||arr[i].photo_ids||[];
            break;
          }
        }
      });
      // Append thumbnail live
      var strip=document.getElementById('thumbs-'+cap.sampleId);
      var card=document.querySelector('.sample-card[data-id="'+cap.sampleId+'"]');
      var btn=document.getElementById('btn-'+cap.sampleId);
      if(btn){btn.className='camera-label done';btn.textContent='📷 Add Another Photo';}
      if(card) card.classList.add('has-photos');
      if(result.new_id){
        var img=document.createElement('img');
        img.className='thumb-img';img.src=imgUrl(result.new_id);img.alt='New photo';
        var newIdx=(result.photo_ids||[]).length-1;
        img.setAttribute('onclick','openLightbox('+cap.sampleId+','+newIdx+');');
        if(strip){strip.appendChild(img);}
        else if(card&&btn){
          var ns=document.createElement('div');ns.className='thumb-strip';ns.id='thumbs-'+cap.sampleId;
          ns.appendChild(img);card.insertBefore(ns,btn);
        }
      }
      // If sample now has a photo, remove from pending list and reload pending count
      if(mode===MODE_PENDING){
        // Remove from pending array and re-render (it's no longer "no photo")
        pendingSamples=pendingSamples.filter(function(s){return s.id!==cap.sampleId;});
        totalPending=Math.max(0,totalPending-1);
        updatePendingBadge();
        // If page is now empty and not last page, reload
        if(pendingSamples.length===0&&currentPage>1){loadPending(currentPage-1);}
        else if(pendingSamples.length===0){renderCards([],false);}
        else{renderCards(pendingSamples,false);}
      }
      previewOverlay.classList.remove('open');previewImg.src='';
      pending={sampleId:null,sampleCode:null,sampleName:null,dataUrl:null};
      showToast('Saved for '+cap.sampleCode,'✅');
    } else {throw new Error((result&&result.error)||'Unknown error');}
  }).catch(function(e){
    btnSave.disabled=false;btnSave.innerHTML='<span>💾</span> Save';
    showToast('Save failed: '+e.message,'❌');
  });
});

// ── Lightbox ──────────────────────────────────────────────────────────────────
var lbIds=[],lbIdx=0,lbSid=null,lbTouchX=null;
window.openLightbox=function(sampleId,idx){
  var s=getSampleById(sampleId);
  if(!s||!s.photo_ids||!s.photo_ids.length) return;
  lbSid=sampleId;lbIds=s.photo_ids;lbIdx=idx||0;
  lbCode.textContent=s.name+(s.sample_name?' — '+s.sample_name:'');
  showLbPhoto();lbEl.classList.add('open');
};
function showLbPhoto(){
  lbImg.src=imgUrlFull(lbIds[lbIdx]);
  lbCounter.textContent=(lbIdx+1)+' / '+lbIds.length;
  document.getElementById('lb-prev').style.display=lbIds.length>1?'flex':'none';
  document.getElementById('lb-next').style.display=lbIds.length>1?'flex':'none';
}
document.getElementById('lb-close').addEventListener('click',function(){lbEl.classList.remove('open');lbImg.src='';});
document.getElementById('lb-prev').addEventListener('click',function(){lbIdx=(lbIdx-1+lbIds.length)%lbIds.length;showLbPhoto();});
document.getElementById('lb-next').addEventListener('click',function(){lbIdx=(lbIdx+1)%lbIds.length;showLbPhoto();});
lbEl.addEventListener('click',function(e){if(e.target===lbEl){lbEl.classList.remove('open');lbImg.src='';}});
lbEl.addEventListener('touchstart',function(e){lbTouchX=e.touches[0].clientX;},{passive:true});
lbEl.addEventListener('touchend',function(e){
  if(lbTouchX===null) return;
  var dx=e.changedTouches[0].clientX-lbTouchX;
  if(Math.abs(dx)>50){lbIdx=dx<0?(lbIdx+1)%lbIds.length:(lbIdx-1+lbIds.length)%lbIds.length;showLbPhoto();}
  lbTouchX=null;
},{passive:true});

// ── Search input ──────────────────────────────────────────────────────────────
searchInput.addEventListener('input',function(){
  var q=searchInput.value.trim();
  searchClear.classList.toggle('visible',q.length>0);
  clearTimeout(searchTimer);
  if(!q){switchMode(MODE_PENDING);return;}
  searchTimer=setTimeout(function(){doSearch(q);},400);
});
searchClear.addEventListener('click',function(){
  searchInput.value='';searchClear.classList.remove('visible');
  switchMode(MODE_PENDING);
});

// ── Mode tabs ─────────────────────────────────────────────────────────────────
document.querySelectorAll('.mode-tab').forEach(function(tab){
  tab.addEventListener('click',function(){
    if(tab.dataset.mode===MODE_SEARCH&&searchSamples.length){
      switchMode(MODE_SEARCH);
    } else {
      searchInput.value='';searchClear.classList.remove('visible');
      switchMode(MODE_PENDING);
    }
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────
prevBtn.addEventListener('click',function(){if(currentPage>1) loadPending(currentPage-1);});
nextBtn.addEventListener('click',function(){if(currentPage<totalPages) loadPending(currentPage+1);});

// ── Refresh & auto-refresh ────────────────────────────────────────────────────
refreshBtn.addEventListener('click',function(){
  if(mode===MODE_PENDING) loadPending(currentPage);
  else doSearch(searchInput.value);
});
setInterval(function(){if(mode===MODE_PENDING) loadPending(currentPage);},60000);

// ── Init ──────────────────────────────────────────────────────────────────────
loadPending(1);

})();
</script>
</body>
</html>
"""


class SampleCameraController(http.Controller):

    @http.route('/lims/camera', type='http', auth='user', csrf=False, save_session=False)
    def camera_page(self, **kwargs):
        """Fixed QR code target — self-contained HTML page, no static file needed."""
        return request.make_response(
            CAMERA_PAGE_HTML,
            headers=[
                ('Content-Type', 'text/html; charset=utf-8'),
                ('X-Frame-Options', 'SAMEORIGIN'),
                ('Cache-Control', 'no-cache'),
            ]
        )

    @http.route('/lims/camera/samples', type='json', auth='user', csrf=False)
    def get_samples(self, page=1, page_size=20, **kwargs):
        """Returns only samples with zero photos, paginated. Safe at any scale."""
        env     = request.env['lims.sample.preparation'].sudo()
        att_env = request.env['ir.attachment'].sudo()

        # One SQL query to get IDs of samples that already have photos
        att_res = att_env.read_group(
            [('res_model','=','lims.sample.preparation'),('mimetype','like','image/%')],
            ['res_id'], ['res_id']
        )
        has_photo_ids = set(r['res_id'] for r in att_res)

        all_lines = env.search([('state','in',['recieved','prepared','todo'])], order='id desc')
        no_photo  = [l for l in all_lines if l.id not in has_photo_ids]

        total     = len(no_photo)
        page      = max(1, int(page))
        page_size = min(50, max(1, int(page_size)))
        offset    = (page - 1) * page_size
        page_lines = no_photo[offset:offset + page_size]

        samples = []
        for line in page_lines:
            reg =  (line.create_uid and line.create_uid.name) or ''
            samples.append({
                'id':            line.id,
                'name':          line.name or '',
                'sample_name':   line.note or '',
                'state':         line.state or '',
                'registered_by': reg,
                'photo_count':   0,
                'photo_ids':     [],
                'category':      line.sample.name if line.sample else '',
            })

        return {'samples': samples, 'total': total, 'page': page, 'page_size': page_size}

    @http.route('/lims/camera/search', type='json', auth='user', csrf=False)
    def search_sample(self, query='', **kwargs):
        """Search by sample code — returns record with existing photos so staff can add more."""
        query = (query or '').strip()
        if not query:
            return []

        env     = request.env['lims.sample.preparation'].sudo()
        att_env = request.env['ir.attachment'].sudo()

        lines = env.search([
            ('name', 'ilike', query),
            ('state', 'in', ['recieved', 'prepared', 'todo', 'cancel']),
        ], order='id desc', limit=10)

        result = []
        for line in lines:
            attachments = att_env.search([
                ('res_model','=','lims.sample.preparation'),
                ('res_id','=',line.id),
                ('mimetype','like','image/%'),
            ], order='id asc')
            reg = (line.create_uid and line.create_uid.name) or ''
            result.append({
                'id':            line.id,
                'name':          line.name or '',
                'sample_name':   line.note or '',
                'state':         line.state or '',
                'registered_by': reg,
                'photo_count':   len(attachments),
                'photo_ids':     attachments.ids,
                'category':      line.sample.name if line.sample else '',
            })
        return result

    @http.route('/lims/camera/save', type='json', auth='user', csrf=False)
    def save_photo(self, sample_id=None, image_data=None, filename='photo.jpg', **kwargs):
        if not sample_id or not image_data:
            return {'success': False, 'error': 'Missing data'}
        try:
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]

            line = request.env['lims.sample.preparation'].sudo().browse(int(sample_id))
            if not line.exists():
                return {'success': False, 'error': 'Sample not found'}

            new_attachment = request.env['ir.attachment'].sudo().create({
                'name':      filename,
                'res_model': 'lims.sample.preparation',
                'res_id':    line.id,
                'datas':     image_data,
                'mimetype':  'image/jpeg',
                'type':      'binary',
            })

            attachments = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'lims.sample.preparation'),
                ('res_id', '=', line.id),
                ('mimetype', 'like', 'image/%'),
            ], order='id asc')
            return {
                'success':     True,
                'photo_count': len(attachments),
                'photo_ids':   attachments.ids,
                'new_id':      new_attachment.id,
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}