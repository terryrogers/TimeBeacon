async function initialiseClockPicker() {
    const response=await fetch('/static/timezones.json');if(!response.ok)throw Error('The clock list could not be loaded. Reload and try again.');
    const catalogue=await response.json(),menu=document.querySelector('#clock-picker .menu');
    for(const clock of catalogue.zones){
        try {new Intl.DateTimeFormat('en',{timeZone:clock.zone});}catch{continue;}
        const item=document.createElement('div');item.className='item';item.dataset.value=clock.zone;item.dataset.text=clock.zone+' — '+clock.location;
        const flag=document.createElement('i');flag.className=clock.country?clock.country+' flag':'globe icon';flag.setAttribute('aria-hidden','true');
        const zone=document.createElement('span');zone.className='clock-picker-zone';zone.textContent=clock.zone;
        const location=document.createElement('span');location.className='clock-picker-location';location.textContent=clock.location;
        item.append(flag,zone,location);menu.append(item);
    }
    window.jQuery('#clock-picker').dropdown({fullTextSearch:'exact',forceSelection:false,selectOnKeydown:false,showOnFocus:true,placeholder:'Type to find a time zone or location',onChange:()=>document.getElementById('clock-feedback').textContent=''});
    const search=document.querySelector('#clock-picker input.search');search.setAttribute('aria-label','Search time zones and locations');
}
