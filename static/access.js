"use strict";
let currentUser=null, administrationState=null;
const can=permission=>Boolean(currentUser?.permissions.includes(permission));
async function accessRequest(url,method="GET",body,view) {
    const {response,payload}=await requestData(url,{method,cache:"no-store",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined},view);
    if(!response.ok) {if(response.status===401 && currentUser && url!=="/auth/login")location.replace("/login");throw new Error(typeof payload.detail==="string"?payload.detail:"Request could not be completed. Check the entered values.");}
    return payload;
}
function feedback(id,message) {(document.getElementById(id)||document.getElementById("page-feedback")).textContent=message;}
function checkboxes(container,items,checked=[]) {
    const root=document.getElementById(container);root.replaceChildren();
    for(const [value,title] of items) {const label=document.createElement("label"),input=document.createElement("input");input.type="checkbox";input.value=value;input.checked=checked.includes(value);label.append(input,document.createTextNode(title));root.append(label);}
}
function checked(id) {return [...document.querySelectorAll("#"+id+" input:checked")].map(i=>i.value);}
function uiButton(text,callback) {const button=document.createElement("button");button.type="button";button.className="ui button";button.textContent=text;button.addEventListener("click",callback);return button;}
async function authenticateDashboard() {
    try{currentUser=await accessRequest("/auth/me");}catch {location.replace('/login');return false;}
    setupAccessControls();
    document.getElementById("settings-button").hidden=!can("admin");
    document.querySelector('footer a[href="/docs"]').hidden=!can("api.view");
    document.getElementById("service-details-button").hidden=!can("server.view");
    document.querySelector(".host-label").textContent="";
    document.querySelector("main").hidden=!can("dashboard.view");
    if(!can("dashboard.view")){document.getElementById("server-status").textContent="Dashboard access not granted";return false;}
    document.getElementById("system-cpu").closest("section").hidden=!can("server.view");
    document.getElementById("system-information").hidden=!can("server.view");
    document.getElementById("time-server-heading").closest("section").hidden=!can("time.view");
    document.querySelector('[data-acquisition="fix"]').closest("section").hidden=!can("time.view");
    document.getElementById("world-panel").hidden=!can("clocks.view");
    document.getElementById("clients-panel").hidden=!can("clients.summary")&&!can("clients.view");
    document.querySelector("#clients-panel .summary-grid").hidden=!can("clients.summary");
    document.querySelector("#clients-panel .controls").hidden=!can("clients.view");
    document.getElementById("client-grid").hidden=!can("clients.view");
    for(const card of document.querySelectorAll('[data-history]')) if(!can(['cpu','ram','storage','temperature'].includes(card.dataset.history)?'server.history':'time.history')){card.disabled=true;card.removeAttribute('role');card.tabIndex=-1;}
    setInterval(async()=>{try{const user=await accessRequest('/auth/me');if(JSON.stringify(user)!==JSON.stringify(currentUser))location.reload();}catch{}},30000);
    return true;
}
function renderClockSettings() {
    const list=document.getElementById("clock-settings-list");if(!list)return;list.replaceChildren();
    for(const clock of TIMEZONES) {
        const row=document.createElement("div");row.className="settings-clock";const label=document.createElement("span");label.textContent=clock.name+" — "+clock.zone;row.append(label);
        if(can("clocks.amend"))row.append(uiButton("Remove",async()=>{try{await saveSharedSettings({clocks:TIMEZONES.filter(c=>c.zone!==clock.zone)});feedback("user-feedback","Clock removed.");}catch(e){feedback("user-feedback",e.message);}}));
        list.append(row);
    }
}
async function listKeys() {
    const list=document.getElementById("key-list");list.replaceChildren();if(!can('api.view'))return;
    for(const key of await accessRequest('/user/keys')) {
        const row=document.createElement('div');row.className='settings-clock';const name=document.createElement('span');name.textContent=key.name+' · '+new Date(key.created*1000).toLocaleDateString();row.append(name,uiButton('Revoke',async()=>{try{await accessRequest('/user/keys/'+key.id,'DELETE');await listKeys();}catch(e){feedback('user-feedback',e.message);}}));list.append(row);
    }
}
function setupAccessControls() {
    document.getElementById('settings-button').addEventListener('click',()=>location.assign('/admin'));
    document.getElementById('user-settings-button').addEventListener('click',()=>location.assign('/user-settings'));
    document.getElementById('logout-button').addEventListener('click',async()=>{await accessRequest('/auth/logout','POST');location.replace('/login');});
}
