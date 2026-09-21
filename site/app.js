'use strict';
const $ = id => document.getElementById(id);
const fields = ['keywords','mode','sector','custom','age','location','exclude','unknown'];
let posts = [], visible = [], limit = 30;
const terms = value => value.split(',').map(x=>x.trim()).filter(Boolean);
const has = (text, value) => new RegExp('(^|[^\\p{L}\\p{N}_])'+value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?=$|[^\\p{L}\\p{N}_])','iu').test(text);
const date = value => value && Number.isFinite(Date.parse(value)) ? new Date(value) : null;
function within(post, hours){const earliest=date(post.published_earliest);return earliest && Date.now()-earliest.getTime()<=hours*3600000 && earliest.getTime()<=Date.now();}
function relative(value){const d=date(value);if(!d)return 'Unknown age';const hours=Math.max(0,(Date.now()-d.getTime())/3600000);return hours<1?'Less than 1h ago':hours<24?Math.floor(hours)+'h ago':Math.floor(hours/24)+'d ago';}
function safeLink(value){try{const u=new URL(value);return u.protocol==='https:'&&(u.hostname==='linkedin.com'||u.hostname.endsWith('.linkedin.com'));}catch{return false;}}
function filterPosts(){
  const keys=terms($('keywords').value), places=terms($('location').value), exclude=terms($('exclude').value), custom=terms($('custom').value);
  visible=posts.filter(p=>{
    const text=p.text||'';
    if(keys.length&&!($('mode').value==='all'?keys.every(k=>has(text,k)):keys.some(k=>has(text,k))))return false;
    if(places.length&&!places.some(k=>has(text,k)))return false;
    if(exclude.some(k=>has(text,k)))return false;
    if($('sector').value==='Custom sector'){if(custom.length&&!custom.some(k=>has(text,k)))return false;}
    else if($('sector').value!=='Any sector'&&!(p.sectors||[]).includes($('sector').value))return false;
    if($('age').value!=='all'){
      if(!date(p.published_earliest))return $('unknown').checked;
      if(!within(p,Number($('age').value)))return false;
    }
    return true;
  });
  render();
}
function render(){
  $('matches').textContent=visible.length;
  $('results').replaceChildren();
  $('export').disabled=!visible.length;
  if(!visible.length){
    const empty=document.createElement('div');empty.className='empty';
    const symbol=document.createElement('div');symbol.className='symbol';symbol.textContent='⌕';
    const title=document.createElement('h3');title.textContent=posts.length?'No posts match these filters':'Ready for your first scan';
    const message=document.createElement('p');message.textContent=posts.length?'Try a wider age window, fewer keywords, or a different sector. Filters work on posts already collected.':'Once the LinkedIn session is configured, run a scan from GitHub Actions. Real hiring posts will appear here after a successful collection.';
    empty.append(symbol,title,message);$('results').append(empty);
  }
  for(const p of visible.slice(0,limit)){
    const card=$('card').content.cloneNode(true);
    card.querySelector('h3').textContent=p.author||'LinkedIn member';
    card.querySelector('.avatar').textContent=(p.author||'LI').split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase();
    card.querySelector('.agebadge').textContent=relative(p.published_latest)+(p.published_latest?' · approx.':'');
    card.querySelector('.posttext').textContent=p.text.length>380?p.text.slice(0,380)+'…':p.text;
    card.querySelector('.fulltext').textContent=p.text;
    if(p.text.length<=380)card.querySelector('details').hidden=true;
    for(const sector of (p.sectors||[]).slice(0,3)){const tag=document.createElement('span');tag.className='tag';tag.textContent=sector;card.querySelector('.tags').append(tag);}
    card.querySelector('.collected').textContent='Collected '+(date(p.collected_at)?.toLocaleDateString()||'');
    const link=card.querySelector('.postlink');if(safeLink(p.url))link.href=p.url;else link.remove();
    $('results').append(card);
  }
  $('more').hidden=visible.length<=limit;
}
for(const id of fields)$(id).addEventListener('input',()=>{limit=30;filterPosts();updateLinkedInLink();});
$('reset').onclick=()=>{for(const id of ['keywords','custom','location','exclude'])$(id).value='';$('mode').value='any';$('sector').value='Any sector';$('age').value='168';$('unknown').checked=false;limit=30;filterPosts();};
$('more').onclick=()=>{limit+=30;render();};
$('linkedinSearch').addEventListener('click',updateLinkedInLink);
$('export').onclick=()=>{
  const columns=['author','author_url','age','published_earliest','published_latest','text','url','collected_at'];
  const cell=value=>{let s=String(value??'');if(/^[\s]*[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
  const csv='\uFEFF'+[columns.map(cell).join(','),...visible.map(p=>columns.map(c=>cell(p[c])).join(','))].join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='linkedin-hiring-posts.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
async function load(){
  try{
    const response=await fetch('data.json',{cache:'no-store'});if(!response.ok)throw Error();
    const data=await response.json();posts=(data.posts||[]).sort((a,b)=>(Date.parse(b.published_latest||b.collected_at)||0)-(Date.parse(a.published_latest||a.collected_at)||0));
    const repo=/^[\w.-]+\/[\w.-]+$/.test(data.repository||'')?data.repository:'Khanmi1973/linkedin-job-radar';
    $('scan').href='https://github.com/'+repo+'/actions/workflows/scan.yml';$('source').href='https://github.com/'+repo;updateLinkedInLink();
    $('total').textContent=posts.length;$('fresh').textContent=posts.filter(p=>within(p,24)).length;
    $('updated').textContent=date(data.last_success)?.toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})||'Not yet';
    const messages={success:'Scan complete. Scheduled at 08:17 and 20:17 Pakistan time; GitHub may start runs later. Filters below apply to the collected feed.',awaiting_first_scan:'Dashboard published. Add your LinkedIn session secret, then select Run a scan → Run workflow on GitHub.',missing_session_secret:'Setup needed: add the LINKEDIN_STORAGE_STATE secret in repository Settings → Secrets and variables → Actions.',invalid_session_secret:'The saved session secret is invalid. Run the local sign-in helper again and replace the GitHub Actions secret.',session_needs_refresh:'LinkedIn needs sign-in or verification. Refresh your session with the local sign-in helper. Previous results are retained.',access_restricted:'LinkedIn restricted the scan. Previous results are retained; check the workflow before trying again.',no_readable_posts:'No readable posts were found. The session, search results, or LinkedIn layout may need attention. Previous results are retained.',scan_failed:'The latest scan failed. Previous results are retained. Check the GitHub Actions run for its status.'};
    $('notice').textContent=messages[data.status]||'Waiting for the first successful scan.';$('notice').classList.toggle('attention',data.status!=='success');
    if(data.status==='success'&&data.excluded_visibility)$('notice').textContent+=' Posts without a confirmed public visibility label were excluded.';
    filterPosts();
  }catch{
    $('notice').textContent='The result file could not be loaded. Refresh the page or check the latest deployment in GitHub Actions.';$('notice').classList.add('attention');
    $('scan').href='https://github.com/Khanmi1973/linkedin-job-radar/actions/workflows/scan.yml';$('source').href='https://github.com/Khanmi1973/linkedin-job-radar';updateLinkedInLink();render();
  }
}
load();
