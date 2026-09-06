let monitoredServices=new Set(),availableServices=[],serviceDetails={};
function selectedServices(id){return [...document.querySelectorAll('#'+id+' input:checked')].map(input=>input.value);}
function renderServicePicker(){
    for(const [id,items] of [['available-services',availableServices.filter(s=>!monitoredServices.has(s))],['monitored-services',[...monitoredServices]]]){
        const list=document.getElementById(id);list.replaceChildren(...items.sort((a,b)=>a.localeCompare(b)).map(name=>{
            const info=serviceDetails[name]||{startup:'Unavailable',status:'Unavailable'},row=document.createElement('label');row.className='service-choice';
            const check=document.createElement('input');check.type='checkbox';check.value=name;check.setAttribute('aria-label',name);check.onchange=updateServiceArrows;row.append(check);
            for(const [text,kind] of [[name,'service-name'],[info.startup,'service-startup'],[info.status,'service-current']]){const span=document.createElement('span');span.className=kind;span.textContent=text;span.title=text;row.append(span);}return row;
        }));document.getElementById(id+'-count').textContent=items.length+(items.length===1?' service':' services');
    }updateServiceArrows();
}
function updateServiceArrows(){document.getElementById('monitor-selected').disabled=!selectedServices('available-services').length;document.getElementById('unmonitor-selected').disabled=!selectedServices('monitored-services').length;}
async function initialiseServicePicker(){
    const save=document.getElementById('save-services');save.disabled=true;
    try{const inventory=await accessRequest('/administration/services');availableServices=inventory.services;serviceDetails=Object.fromEntries((inventory.details||[]).map(info=>[info.name,info]));monitoredServices=new Set(inventory.monitored);renderServicePicker();
        document.getElementById('monitor-selected').onclick=()=>{for(const name of selectedServices('available-services'))monitoredServices.add(name);renderServicePicker();};
        document.getElementById('unmonitor-selected').onclick=()=>{for(const name of selectedServices('monitored-services')){monitoredServices.delete(name);if(!availableServices.includes(name))availableServices.push(name);}renderServicePicker();};
        save.disabled=false;feedback('service-picker-feedback','');
    }catch(error){feedback('service-picker-feedback',error.message);}
}
