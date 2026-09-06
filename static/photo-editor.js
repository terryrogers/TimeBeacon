function initialisePhotoEditor({getProfile=()=>personalProfile,endpoint=()=>'/user/photo',onUpdate=()=>refreshProfile()}={}){
    const dialog=document.getElementById('photo-dialog'),gravatar=document.getElementById('photo-gravatar'),clear=document.getElementById('clear-photo'),file=document.getElementById('photo-file'),message=document.getElementById('photo-feedback');
    let busy=false;
    function sync(){const profile=getProfile();gravatar.checked=profile.gravatar_enabled;clear.hidden=!profile.custom_photo;document.getElementById('photo-preview').src=profile.avatar;}
    document.getElementById('edit-photo').onclick=()=>{sync();file.value='';message.textContent='';dialog.showModal();};
    async function update(action){if(busy)return;const target=getProfile();busy=true;for(const control of [gravatar,clear,file])control.disabled=true;try{await onUpdate(await action(),target);sync();message.textContent='Profile photo updated.';}catch(error){sync();message.textContent=error.message;}finally{busy=false;for(const control of [gravatar,clear,file])control.disabled=false;}}
    gravatar.onchange=()=>update(()=>accessRequest(endpoint(),'PATCH',{gravatar_enabled:gravatar.checked}));
    clear.onclick=()=>update(()=>accessRequest(endpoint(),'PATCH',{gravatar_enabled:gravatar.checked,clear:true}));
    file.onchange=()=>{const image=file.files[0];if(!image)return;if(image.size>4*1024*1024){message.textContent='Choose an image smaller than 4 MB.';file.value='';return;}const url=endpoint();
        update(async()=>{const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Image could not be read.'));reader.readAsDataURL(image);});const result=await accessRequest(url,'POST',{image:encoded});file.value='';return result;});};
    document.getElementById('photo-preview').onerror=event=>{event.target.onerror=null;event.target.src='/static/avatar-default.svg';};
}
