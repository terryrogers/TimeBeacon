let monitoredServices=new Set(), availableServices=[];
function renderServicePicker(){
    for(const [id,items] of [['available-services',availableServices.filter(s=>!monitoredServices.has(s))],['monitored-services',[...monitoredServices]]]){
        const select=document.getElementById(id);select.replaceChildren(...items.sort((a,b)=>a.localeCompare(b)).map(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;return option;}));
        document.getElementById(id+'-count').textContent=items.length+' services';
    }
    updateServiceArrows();
}
function updateServiceArrows(){document.getElementById('monitor-selected').disabled=!document.getElementById('available-services').selectedOptions.length;document.getElementById('unmonitor-selected').disabled=!document.getElementById('monitored-services').selectedOptions.length;}
async function initialiseServicePicker(){
    const save=document.getElementById('save-services');save.disabled=true;
    try{
        const inventory=await accessRequest('/administration/services');availableServices=inventory.services;monitoredServices=new Set(inventory.monitored);renderServicePicker();
        for(const id of ['available-services','monitored-services'])document.getElementById(id).onchange=updateServiceArrows;
        document.getElementById('monitor-selected').onclick=()=>{for(const option of document.getElementById('available-services').selectedOptions)monitoredServices.add(option.value);renderServicePicker();};
        document.getElementById('unmonitor-selected').onclick=()=>{for(const option of document.getElementById('monitored-services').selectedOptions){monitoredServices.delete(option.value);if(!availableServices.includes(option.value))availableServices.push(option.value);}renderServicePicker();};
        save.disabled=false;feedback('service-picker-feedback','');
    }catch(error){feedback('service-picker-feedback',error.message);}
}
