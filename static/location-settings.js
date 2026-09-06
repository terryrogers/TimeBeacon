"use strict";
let locationReference,locationRequest=0,locationTimer,currentLocationCountry='';
function renderLocation(profile){
    const selected=profile.location,hasLocation=selected.latitude!=null&&selected.longitude!=null;
    document.getElementById('location-label').textContent=hasLocation?[...new Set([selected.location,selected.region,selected.country].filter(Boolean))].join(', '):'Location Not Set';
    document.getElementById('clear-location').hidden=!hasLocation;
    document.getElementById('manual-theme').hidden=hasLocation;
    document.getElementById('manual-dark').checked=selected.theme==='dark';
    document.getElementById('location-intro').textContent=hasLocation?'Light after sunrise. Dark after sunset.':'Choose Light or Dark, or set a location for an automatic theme.';
    locationReference=profile.reference_clock;
    currentLocationCountry=hasLocation?(selected.country_code||locationReference?.country_code||''):'';
    document.dispatchEvent(new CustomEvent('location-country',{detail:currentLocationCountry}));
    document.getElementById('reference-clock').hidden=!locationReference;
    renderReferenceClock();
    refreshLocationBackground();
}
function renderReferenceClock(){
    if(!locationReference)return;
    const now=new Date(),zone=locationReference.timezone;
    const time=new Intl.DateTimeFormat('en-GB',{timeZone:zone,hour:'numeric',minute:'2-digit',second:'2-digit',hour12:true}).format(now);
    const date=new Intl.DateTimeFormat('en-GB',{timeZone:zone,dateStyle:'medium'}).format(now);
    const offset=new Intl.DateTimeFormat('en',{timeZone:zone,timeZoneName:'longOffset'}).formatToParts(now).find(part=>part.type==='timeZoneName').value.replace('GMT','UTC ').trim();
    const clock=document.getElementById('reference-clock'),flag=document.createElement('i');flag.className=locationReference.country_code+' flag';flag.setAttribute('aria-label',locationReference.country_code.toUpperCase());
    clock.replaceChildren(flag,document.createTextNode('Reference Clock · '+locationReference.city+' · '+time+' · '+date+' · '+zone+' ('+(offset==='UTC'?'UTC +00:00':offset)+')'));
}
let referencePhotoRequest=0;
async function refreshLocationBackground(){
    const request=++referencePhotoRequest,panel=document.getElementById('daylight-display');
    panel.querySelectorAll('.daylight-photo,.reference-photo-button').forEach(node=>node.remove());
    if(!locationReference||!document.getElementById('clock-backgrounds').checked)return;
    try{
        const {image:photo}=await accessRequest('/user/location/image');
        if(!photo||request!==referencePhotoRequest)return;
        const image=document.createElement('img');image.className='daylight-photo';image.alt='';image.referrerPolicy='no-referrer';image.setAttribute('aria-hidden','true');
        const credit=document.createElement('button');credit.type='button';credit.className='ui icon button reference-photo-button';credit.textContent='ⓘ';credit.setAttribute('aria-label','Reference Clock Photo Credit');credit.hidden=true;
        credit.onclick=()=>{const content=document.getElementById('reference-photo-credit');content.replaceChildren();for(const value of [photo.city,photo.artist,photo.credit,photo.license]){if(value){const p=document.createElement('p');p.textContent=value;content.append(p);}}const link=document.createElement('a');link.href=photo.source_url;link.textContent='Original Photograph And Licence On Wikimedia Commons';link.target='_blank';link.rel='noopener noreferrer';content.append(link);document.getElementById('reference-photo-dialog').showModal();};
        image.onload=()=>credit.hidden=false;image.onerror=()=>{image.remove();credit.remove();};trackLoadingImage(image,panel);image.src=photo.image_url;panel.prepend(image);panel.append(credit);
    }catch{/* Optional photographs do not block account settings. */}
}
async function refreshLocation(){const profile=await accessRequest('/user/profile');renderLocation(profile);await applyTheme();}
function initialiseLocationSettings(){
    const picker=window.jQuery('#location-picker'),input=document.querySelector('#location-picker input.search'),menu=document.querySelector('#location-picker .menu');
    const loader=document.getElementById('location-search-loading'),activity=new Map();
    let results=new Map(),country='',countryRows=[],countryRequest=0,searchAbort,countryAbort;
    const normalise=value=>value.normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase();
    function busy(label){
        const key=Symbol();activity.set(key,label);paintActivity();
        return ()=>{activity.delete(key);paintActivity();};
    }
    function paintActivity(){
        loader.hidden=!activity.size;picker.toggleClass('loading',!!activity.size);
        picker.attr('aria-busy',String(!!activity.size));
        if(activity.size)loader.querySelector('span').textContent=[...activity.values()].at(-1);
    }
    function cancelSearch(){++locationRequest;clearTimeout(locationTimer);searchAbort?.abort();}
    function localMatches(query){
        const text=normalise(query),tokens=text.split(/\s+/).filter(Boolean);
        return countryRows.filter(place=>tokens.every(token=>place.search.includes(token)))
            .sort((a,b)=>Number(a.city_search!==text)-Number(b.city_search!==text)||Number(!a.city_search.startsWith(tokens[0]||''))-Number(!b.city_search.startsWith(tokens[0]||''))).slice(0,30);
    }
    function renderPlaces(places,show=true){
        menu.replaceChildren();results=new Map(places.map(place=>[String(place.id),place]));
        for(const place of places){
            const item=document.createElement('div');item.className='item';item.dataset.value=String(place.id);item.dataset.text=place.city;
            const flag=document.createElement('i');flag.className=place.country_code+' flag';flag.setAttribute('aria-hidden','true');
            const name=document.createElement('span');name.className='place-name';name.textContent=[...new Set([place.city,place.region,place.country].filter(Boolean))].join(', ');
            const zone=document.createElement('span');zone.className='place-timezone';zone.textContent=place.timezone;
            item.append(flag,name,zone);menu.append(item);
        }
        picker.dropdown('refresh');if(show&&places.length)picker.dropdown('show');
    }
    async function loadCountry(code){
        code=code.toLowerCase();if(code===country)return;
        country=code;countryRows=[];const request=++countryRequest;countryAbort?.abort();cancelSearch();
        renderPlaces([],false);if(!code)return;
        // Cache only public geographic data, scoped by country and catalogue revision.
        const key='timebeacon.places.20260906.v1.'+code;
        try{const saved=JSON.parse(sessionStorage.getItem(key)||'null');if(saved&&Date.now()-saved.saved<86400000&&Array.isArray(saved.places))countryRows=saved.places;}catch{}
        if(!countryRows.length){
            const finish=busy('Preparing Towns And Cities…');countryAbort=new AbortController();
            try{
                const {response,payload}=await requestData('/user/locations/country?code='+encodeURIComponent(code),{signal:AbortSignal.any([countryAbort.signal,AbortSignal.timeout(20000)])},{silent:true});
                if(!response.ok)throw Error('The country list could not be loaded. Worldwide search is still available.');
                if(request!==countryRequest)return;
                countryRows=payload.places;
                try{sessionStorage.setItem(key,JSON.stringify({saved:Date.now(),places:countryRows}));}catch{/* Storage limits do not prevent in-memory caching. */}
            }catch(error){if(request===countryRequest&&error.name!=='AbortError')feedback('location-feedback',error.message);}
            finally{finish();}
        }
        if(request===countryRequest&&!input.value.trim())renderPlaces(localMatches(''),document.activeElement===input);
    }
    picker.dropdown({filterRemoteData:false,fullTextSearch:true,forceSelection:false,selectOnKeydown:false,onChange:async value=>{
        if(!results.has(value))return;
        cancelSearch();const finish=busy('Saving Location…');picker.addClass('disabled');
        try{await accessRequest('/user/location','PUT',{id:Number(value)},{silent:true});await refreshLocation();feedback('location-feedback','Location saved. The theme now follows local daylight.');}
        catch(error){feedback('location-feedback',error.message);}
        finally{results.clear();picker.dropdown('clear');picker.removeClass('disabled');renderPlaces(localMatches(''),false);finish();}
    }});
    input.setAttribute('aria-label','Search Cities and Towns');
    input.addEventListener('input',()=>{
        cancelSearch();const query=input.value.trim(),request=locationRequest;
        renderPlaces(localMatches(query));
        if(query.length<2){feedback('location-feedback',countryRows.length?'Showing towns and cities in your selected country. Type to search worldwide.':'Type at least two characters to search.');return;}
        feedback('location-feedback','Searching worldwide…');
        const finish=busy('Searching Cities And Towns…');searchAbort=new AbortController();const signal=searchAbort.signal;
        // Cancellation covers the debounce period as well as the network request.
        signal.addEventListener('abort',finish,{once:true});
        locationTimer=setTimeout(async()=>{
            try{
                const {response,payload}=await requestData('/user/locations/search?q='+encodeURIComponent(query),{signal:AbortSignal.any([signal,AbortSignal.timeout(15000)])},{silent:true});
                if(!response.ok)throw Error('Worldwide search is unavailable. Cached country results are still available.');
                if(request!==locationRequest)return;
                const places=[...new Map([...localMatches(query),...payload.places].map(place=>[place.id,place])).values()];
                renderPlaces(places);
                feedback('location-feedback',places.length?'Select a town or city. Add a country or region to narrow your search.':'No matching places. Try another spelling or a nearby town.');
            }catch(error){if(request===locationRequest&&error.name!=='AbortError')feedback('location-feedback',error.message);}
            finally{signal.removeEventListener('abort',finish);finish();}
        },250);
    });
    document.addEventListener('location-country',event=>loadCountry(event.detail));
    loadCountry(currentLocationCountry);
    document.getElementById('clear-location').onclick=async()=>{
        const button=document.getElementById('clear-location');button.disabled=true;cancelSearch();
        try{results.clear();picker.dropdown('clear');await accessRequest('/user/location','DELETE');await refreshLocation();feedback('location-feedback','Location cleared. Choose Light or Dark below.');}
        catch(error){feedback('location-feedback',error.message);}finally{button.disabled=false;}
    };
    document.getElementById('manual-dark').onchange=async event=>{
        const toggle=event.target;toggle.disabled=true;
        try{await accessRequest('/user/theme','PUT',{theme:toggle.checked?'dark':'light'});await applyTheme();feedback('location-feedback','Display preference saved.');}
        catch(error){toggle.checked=!toggle.checked;feedback('location-feedback',error.message);}finally{toggle.disabled=false;}
    };
    setInterval(renderReferenceClock,1000);
}
