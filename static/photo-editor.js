function initialisePhotoEditor(){
    const dialog=document.getElementById('photo-dialog'),gravatar=document.getElementById('photo-gravatar'),clear=document.getElementById('clear-photo'),file=document.getElementById('photo-file'),message=document.getElementById('photo-feedback');
    let busy=false;
    function sync(){gravatar.checked=personalProfile.gravatar_enabled;clear.hidden=!personalProfile.custom_photo;document.getElementById('photo-preview').src=personalProfile.avatar;}
    document.getElementById('edit-photo').onclick=()=>{sync();file.value='';message.textContent='';dialog.showModal();};
    async function update(action){if(busy)return;busy=true;for(const control of [gravatar,clear,file])control.disabled=true;try{await action();await refreshProfile();sync();message.textContent='Profile photo updated.';}catch(error){sync();message.textContent=error.message;}finally{busy=false;for(const control of [gravatar,clear,file])control.disabled=false;}}
    gravatar.onchange=()=>update(()=>accessRequest('/user/photo','PATCH',{gravatar_enabled:gravatar.checked}));
    clear.onclick=()=>update(()=>accessRequest('/user/photo','PATCH',{gravatar_enabled:gravatar.checked,clear:true}));
    file.onchange=()=>{const image=file.files[0];if(!image)return;if(image.size>4*1024*1024){message.textContent='Choose an image smaller than 4 MB.';file.value='';return;}
        update(async()=>{const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Image could not be read.'));reader.readAsDataURL(image);});await accessRequest('/user/photo','POST',{image:encoded});file.value='';});};
    document.getElementById('photo-preview').onerror=event=>{event.target.onerror=null;event.target.src='/static/avatar-default.svg';};
}
