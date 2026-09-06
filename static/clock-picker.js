let clockCatalogue;
async function preloadClockImage(zone){
    try{
        const response=await fetch('/dashboard/clocks/image?zone='+encodeURIComponent(zone),{cache:'no-store',signal:AbortSignal.timeout(20000)});
        if(!response.ok)return false;
        const {image:photo}=await response.json();
        if(!photo?.image_url)return false;
        return await new Promise(resolve=>{
            const image=new Image();image.referrerPolicy='no-referrer';
            const finish=ready=>{clearTimeout(timeout);image.onload=null;image.onerror=null;resolve(ready);};
            const timeout=setTimeout(()=>finish(false),10000);
            image.onload=()=>finish(true);image.onerror=()=>finish(false);
            // Match the dashboard URL and referrer policy so its browser cache entry is reused.
            image.src=photo.image_url;
        });
    }catch{return false;}
}
async function loadClockCatalogue(){if(!clockCatalogue){const response=await fetch('/static/timezones.json');if(!response.ok)throw Error('The clock list could not be loaded. Reload and try again.');clockCatalogue=(await response.json()).zones.map(clock=>({...clock,location:clock.location.replace(/\bGMT\s*(?=[+-])/g,'UTC ').replace(/\bGMT\b/g,'UTC')}));}return clockCatalogue;}
function clockDescription(zone){return (clockCatalogue||[]).find(clock=>clock.zone===zone)||(clockCatalogue||[]).find(clock=>{try{return new Intl.DateTimeFormat('en',{timeZone:clock.zone}).resolvedOptions().timeZone===new Intl.DateTimeFormat('en',{timeZone:zone}).resolvedOptions().timeZone;}catch{return false;}})||{zone,country:'',location:''};}
function appendClockDescription(row,zone){const clock=clockDescription(zone),flag=document.createElement('i');flag.className=clock.country?clock.country+' flag':'globe icon';flag.setAttribute('aria-hidden','true');row.append(flag);for(const [value,className] of [[zone,'clock-picker-zone'],[clock.location,'clock-picker-location']]){const span=document.createElement('span');span.className=className;span.textContent=value;row.append(span);}}
async function initialiseClockPicker(selector='#clock-picker') {
    const catalogue=await loadClockCatalogue(),menu=document.querySelector(selector+' .menu');menu.replaceChildren();
    for(const clock of catalogue){
        try {new Intl.DateTimeFormat('en',{timeZone:clock.zone});}catch{continue;}
        const item=document.createElement('div');item.className='item';item.dataset.value=clock.zone;item.dataset.text=clock.zone+' — '+clock.location;
        const flag=document.createElement('i');flag.className=clock.country?clock.country+' flag':'globe icon';flag.setAttribute('aria-hidden','true');
        const zone=document.createElement('span');zone.className='clock-picker-zone';zone.textContent=clock.zone;
        const location=document.createElement('span');location.className='clock-picker-location';location.textContent=clock.location;
        item.append(flag,zone,location);menu.append(item);
    }
    window.jQuery(selector).dropdown({fullTextSearch:'exact',forceSelection:false,selectOnKeydown:false,showOnFocus:true,placeholder:'Type to find a time zone or location',onChange:value=>{const selected=document.querySelector(selector+' > .text');if(value&&selected){selected.replaceChildren();appendClockDescription(selected,value);}const output=document.getElementById('clock-feedback');if(output)output.textContent='';}});
    const search=document.querySelector(selector+' input.search');search.setAttribute('aria-label','Search time zones and locations');
}
