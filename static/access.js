"use strict";
let currentUser=null, administrationState=null;
const can=permission=>Boolean(currentUser?.permissions.includes(permission));
async function accessRequest(url,method="GET",body) {
    const response=await fetch(url,{method,cache:"no-store",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});
    const payload=await response.json();
    if(!response.ok) {if(response.status===401 && currentUser && url!=="/auth/login")location.reload();throw new Error(typeof payload.detail==="string"?payload.detail:"Request could not be completed. Check the entered values.");}
    return payload;
}
function feedback(id,message) {document.getElementById(id).textContent=message;}
function checkboxes(container,items,checked=[]) {
    const root=document.getElementById(container);root.replaceChildren();
    for(const [value,title] of items) {const label=document.createElement("label"),input=document.createElement("input");input.type="checkbox";input.value=value;input.checked=checked.includes(value);label.append(input,document.createTextNode(title));root.append(label);}
}
function checked(id) {return [...document.querySelectorAll("#"+id+" input:checked")].map(i=>i.value);}
function uiButton(text,callback) {const button=document.createElement("button");button.type="button";button.textContent=text;button.addEventListener("click",callback);return button;}
async function authenticateDashboard() {
    const login=document.getElementById("login-dialog");
    try{currentUser=await accessRequest("/auth/me");}catch {
        login.addEventListener("cancel",e=>e.preventDefault());login.showModal();
        document.getElementById("login-form").addEventListener("submit",async event=>{
            event.preventDefault();const form=event.target,button=form.querySelector("button");button.disabled=true;
            try {await accessRequest("/auth/login","POST",Object.fromEntries(new FormData(form)));form.reset();location.reload();}
            catch(error){feedback("login-feedback",error.message);}finally{button.disabled=false;}
        });return false;
    }
    setupAccessControls();
    document.getElementById("settings-button").hidden=!can("admin");
    document.querySelector('footer a[href="/docs"]').hidden=!can("api.view");
    document.getElementById("service-details-button").hidden=!can("server.view");
    document.querySelector(".host-label").textContent="";
    document.getElementById("user-clocks").hidden=!can("dashboard.view") || (!can("clocks.view")&&!can("clocks.amend"));
    document.getElementById("key-section").hidden=!can("api.view");
    document.querySelector("main").hidden=!can("dashboard.view");
    if(!can("dashboard.view")){document.getElementById("server-status").textContent="Dashboard access not granted";return false;}
    document.getElementById("system-cpu").closest("section").hidden=!can("server.view");
    document.getElementById("time-server-heading").closest("section").hidden=!can("time.view");
    document.querySelector('[data-acquisition="fix"]').closest("section").hidden=!can("time.view");
    document.getElementById("world-panel").hidden=!can("clocks.view");
    document.getElementById("clients-panel").hidden=!can("clients.summary")&&!can("clients.view");
    document.querySelector("#clients-panel .summary-grid").hidden=!can("clients.summary");
    document.querySelector("#clients-panel .controls").hidden=!can("clients.view");
    document.getElementById("client-grid").hidden=!can("clients.view");
    document.getElementById("user-clocks").hidden=!can("clocks.view")&&!can("clocks.amend");
    document.getElementById("key-section").hidden=!can("api.view");
    document.getElementById("clock-form").hidden=!can("clocks.amend");
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
    const clockForm=document.getElementById('clock-form'),clockFeedback=document.getElementById('clock-feedback');document.getElementById('user-clocks').append(clockForm,clockFeedback);
    document.getElementById('logout-button').addEventListener('click',async()=>{await accessRequest('/auth/logout','POST');location.reload();});
    document.getElementById('user-settings-button').addEventListener('click',async()=>{
        feedback('user-identity',currentUser.username+' · '+currentUser.roles.join(', '));feedback('user-feedback','');feedback('new-key','');renderClockSettings();document.getElementById('user-dialog').showModal();try{await listKeys();}catch(e){feedback('user-feedback',e.message);}
    });
    document.getElementById('user-dialog').addEventListener('close',()=>feedback('new-key',''));
    document.getElementById('password-form').addEventListener('submit',async event=>{event.preventDefault();try{await accessRequest('/user/password','POST',Object.fromEntries(new FormData(event.target)));event.target.reset();location.reload();}catch(e){feedback('user-feedback',e.message);}});
    document.getElementById('key-form').addEventListener('submit',async event=>{event.preventDefault();try{const key=await accessRequest('/user/keys','POST',Object.fromEntries(new FormData(event.target)));feedback('new-key',key.message+'\n'+key.key);event.target.reset();await listKeys();}catch(e){feedback('user-feedback',e.message);}});
    document.getElementById('settings-button').addEventListener('click',async()=>{try{await loadAdministration();document.getElementById('admin-dialog').showModal();}catch(e){showError(e.message);}});
    document.getElementById('new-user').addEventListener('click',()=>{document.getElementById('admin-user-form').reset();document.querySelector('#admin-user-form [name=id]').value='';checkboxes('user-roles',administrationState.roles.map(r=>[r.name,r.name]),['User']);});
    document.getElementById('admin-user-form').addEventListener('submit',async event=>{
        event.preventDefault();const form=event.target,values=Object.fromEntries(new FormData(form));const body={id:values.id?Number(values.id):null,username:values.username,roles:checked('user-roles'),enabled:form.elements.enabled.checked};if(values.password)body.password=values.password;
        try{await accessRequest('/administration/users','PUT',body);form.reset();form.elements.id.value='';await loadAdministration();feedback('admin-feedback','User saved.');}catch(e){feedback('admin-feedback',e.message);}
    });
    document.getElementById('admin-role-form').addEventListener('submit',async event=>{event.preventDefault();try{await accessRequest('/administration/roles','PUT',{name:event.target.elements.name.value,permissions:checked('role-permissions')});await loadAdministration();feedback('admin-feedback','Role saved.');}catch(e){feedback('admin-feedback',e.message);}});
    document.getElementById('admin-config-form').addEventListener('submit',async event=>{
        event.preventDefault();const values=Object.fromEntries(new FormData(event.target));values.services=values.services.split(/\s+/).filter(Boolean);for(const key of ['warning_seconds','critical_seconds','warning_drops','critical_drops','latitude','longitude'])values[key]=Number(values[key]);
        try{const result=await accessRequest('/administration/config','PUT',values);feedback('admin-feedback',result.message);await loadSharedSettings();configureTheme();}catch(e){feedback('admin-feedback',e.message);}
    });
}
async function loadAdministration() {
    administrationState=await accessRequest('/administration');const state=administrationState;
    checkboxes('user-roles',state.roles.map(r=>[r.name,r.name]),['User']);checkboxes('role-permissions',Object.entries(state.permissions));
    const users=document.getElementById('admin-users');users.replaceChildren();
    for(const user of state.users)users.append(uiButton(user.username+' · '+user.roles.join(', ')+(user.enabled?'':' (disabled)'),()=>{const form=document.getElementById('admin-user-form');form.elements.id.value=user.id;form.elements.username.value=user.username;form.elements.password.value='';form.elements.enabled.checked=user.enabled;checkboxes('user-roles',state.roles.map(r=>[r.name,r.name]),user.roles);}));
    const roles=document.getElementById('admin-roles');roles.replaceChildren();
    for(const role of state.roles)if(role.name!=='Administrator')roles.append(uiButton(role.name,()=>{document.querySelector('#admin-role-form [name=name]').value=role.name;checkboxes('role-permissions',Object.entries(state.permissions),role.permissions);}));
    const form=document.getElementById('admin-config-form');for(const key of ['location','latitude','longitude','warning_seconds','critical_seconds','warning_drops','critical_drops'])form.elements[key].value=state.config[key];form.elements.services.value=state.config.services.join('\n');
}
