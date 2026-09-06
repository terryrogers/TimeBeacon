"use strict";
// One delayed Semantic UI status per region, shared by overlapping operations.
const loadingRegions=new Map();
function beginLoading({target=null,label='Loading…',silent=false}={}) {
    if(silent)return ()=>{};
    let key=target||document.body;
    if(target){
        const parent=[...loadingRegions.keys()].find(region=>region!==document.body&&region.contains(target));
        if(parent)key=parent;
    }
    let state=loadingRegions.get(key);
    if(!state){
        const status=document.createElement('div'),spinner=document.createElement('div'),text=document.createElement('span');
        status.className='loading-status'+(target?'':' loading-dock');status.setAttribute('role','status');status.setAttribute('aria-live','polite');status.hidden=true;
        spinner.className='ui active mini inline loader';spinner.setAttribute('aria-hidden','true');text.textContent=label;status.append(spinner,text);
        state={count:0,status,priorBusy:key.getAttribute('aria-busy')};loadingRegions.set(key,state);
        state.timer=setTimeout(()=>{if(!key.isConnected)return;key.setAttribute('aria-busy','true');key.prepend(status);status.hidden=false;},350);
    }
    state.count++;
    let done=false;
    return ()=>{if(done)return;done=true;if(--state.count)return;clearTimeout(state.timer);state.status.remove();if(state.priorBusy===null)key.removeAttribute('aria-busy');else key.setAttribute('aria-busy',state.priorBusy);loadingRegions.delete(key);};
}
async function withLoading(action,view) {const finish=beginLoading(view);try{return await action();}finally{finish();}}
function loadingView(url,method='GET') {
    const path=new URL(url,location.origin).pathname;
    const byId=id=>document.getElementById(id),section=id=>byId(id)?.closest('section');
    let target=null,label=method==='GET'?'Loading…':'Saving Changes…';
    if(path.startsWith('/auth/')){target=document.querySelector('.signin-card');label='Please Wait…';}
    else if(path==='/dashboard/history'){target=byId('history-dialog')?.querySelector('.window-content');label='Loading History…';}
    else if(path.includes('/services/repair')){target=byId('service-repair-dialog')?.querySelector('.window-content');label='Checking Service Health…';}
    else if(path.endsWith('/photo')){target=byId('photo-dialog')?.querySelector('.window-content');label='Updating Photo…';}
    else if(path.startsWith('/user/location')||path==='/user/theme'){target=byId('daylight-display');label=path.includes('/search')?'Searching Locations…':'Loading Location…';}
    else if(path==='/dashboard/tracking'){target=section('time-server-heading');label='Updating Time Server…';}
    else if(path==='/dashboard/clients'){target=byId('clients-panel');label='Updating Time Clients…';}
    else if(path==='/dashboard/status'){target=section('system-cpu');label='Updating Server Status…';}
    else if(path==='/dashboard/time'){target=byId('world-panel');label='Synchronising Clocks…';}
    else if(path.includes('/clocks/')||path==='/static/timezones.json'||path==='/dashboard/settings'){target=byId('user-clocks')||byId('world-panel');label='Loading Clocks…';}
    else if(path.startsWith('/user/keys')){target=byId('key-section');label='Updating API Keys…';}
    else if(path==='/administration/users'&&method!=='GET'){target=byId('edit-user-dialog')?.querySelector('.window-content');}
    if(target?.tagName==='DETAILS'&&!target.open)target=null;
    return {target,label};
}
async function requestData(url,options={},view) {
    return withLoading(async()=>{
        const response=await fetch(url,{signal:AbortSignal.timeout(60000),...options});
        const payload=await response.json();
        return {response,payload};
    },view||loadingView(url,options.method));
}
function trackLoadingImage(image,target) {
    const finish=beginLoading({target,label:'Loading Photo…'});
    const done=()=>{clearTimeout(timer);image.removeEventListener('load',done);image.removeEventListener('error',done);finish();};
    const timer=setTimeout(done,15000);
    image.addEventListener('load',done,{once:true});image.addEventListener('error',done,{once:true});
}
