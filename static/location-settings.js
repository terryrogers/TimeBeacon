"use strict";
let locationReference,locationRequest=0,locationTimer;
function renderLocation(profile){
    const selected=profile.location,hasLocation=selected.latitude!=null&&selected.longitude!=null;
    document.getElementById('location-label').textContent=hasLocation?[...new Set([selected.location,selected.region,selected.country].filter(Boolean))].join(', '):'Location Not Set';
    document.getElementById('clear-location').hidden=!hasLocation;
    document.getElementById('manual-theme').hidden=hasLocation;
    document.getElementById('manual-dark').checked=selected.theme==='dark';
    document.getElementById('location-intro').textContent=hasLocation?'Light after sunrise. Dark after sunset.':'Choose Light or Dark, or set a location for an automatic theme.';
    locationReference=profile.reference_clock;
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
    let results=new Map();
    picker.dropdown({filterRemoteData:false,fullTextSearch:true,forceSelection:false,selectOnKeydown:false,onChange:async value=>{
        if(!results.has(value))return;
        const request=++locationRequest;clearTimeout(locationTimer);
        picker.addClass('disabled');
        try{await accessRequest('/user/location','PUT',{id:Number(value)});await refreshLocation();feedback('location-feedback','Location saved. The theme now follows local daylight.');}
        catch(error){feedback('location-feedback',error.message);}
        finally{if(request===locationRequest){results.clear();picker.dropdown('clear');picker.removeClass('disabled');}}
    }});
    input.setAttribute('aria-label','Search Cities and Towns');
    input.addEventListener('input',()=>{
        const query=input.value.trim(),request=++locationRequest;clearTimeout(locationTimer);results.clear();menu.replaceChildren();
        if(query.length<2){feedback('location-feedback','Type at least two characters to search.');return;}
        feedback('location-feedback','Searching…');
        locationTimer=setTimeout(async()=>{
            try{
                const response=await accessRequest('/user/locations/search?q='+encodeURIComponent(query));if(request!==locationRequest)return;
                menu.replaceChildren();results=new Map(response.places.map(place=>[String(place.id),place]));
                for(const place of response.places){
                    const item=document.createElement('div');item.className='item';item.dataset.value=String(place.id);item.dataset.text=place.city;
                    const flag=document.createElement('i');flag.className=place.country_code+' flag';flag.setAttribute('aria-hidden','true');
                    const name=document.createElement('span');name.className='place-name';name.textContent=[...new Set([place.city,place.region,place.country].filter(Boolean))].join(', ');
                    const zone=document.createElement('span');zone.className='place-timezone';zone.textContent=place.timezone;
                    item.append(flag,name,zone);menu.append(item);
                }
                picker.dropdown('refresh');picker.dropdown('show');
                feedback('location-feedback',response.places.length?'Select a town or city. Add a country or region to narrow your search.':'No matching places. Try another spelling or a nearby town.');
            }catch(error){if(request===locationRequest)feedback('location-feedback',error.message);}
        },250);
    });
    document.getElementById('clear-location').onclick=async()=>{
        const button=document.getElementById('clear-location');button.disabled=true;
        try{++locationRequest;clearTimeout(locationTimer);results.clear();picker.dropdown('clear');await accessRequest('/user/location','DELETE');await refreshLocation();feedback('location-feedback','Location cleared. Choose Light or Dark below.');}
        catch(error){feedback('location-feedback',error.message);}finally{button.disabled=false;}
    };
    document.getElementById('manual-dark').onchange=async event=>{
        const toggle=event.target;toggle.disabled=true;
        try{await accessRequest('/user/theme','PUT',{theme:toggle.checked?'dark':'light'});await applyTheme();feedback('location-feedback','Display preference saved.');}
        catch(error){toggle.checked=!toggle.checked;feedback('location-feedback',error.message);}finally{toggle.disabled=false;}
    };
    setInterval(renderReferenceClock,1000);
}
