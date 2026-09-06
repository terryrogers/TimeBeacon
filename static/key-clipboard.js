function initialiseKeyClipboard(){
    const form=document.getElementById('key-form'),output=document.getElementById('new-key'),retry=document.getElementById('copy-key-retry');
    let secret=null,deadline=0,timer=null,clearing=false;
    const finish=message=>{secret=null;deadline=0;clearInterval(timer);timer=null;retry.hidden=true;form.querySelector('button').disabled=false;output.textContent=message;};
    async function check(){
        if(!secret || !deadline || clearing)return;
        const remaining=Math.max(0,Math.ceil((deadline-Date.now())/1000));
        if(remaining){output.textContent=`API key copied. Clipboard clearance in ${remaining} seconds. Keep this page open.`;return;}
        clearing=true;
        try{const current=await navigator.clipboard.readText();if(current===secret){await navigator.clipboard.writeText('');finish('API key cleared from the clipboard.');}else finish('Clipboard changed. Your current clipboard was left untouched.');}
        catch{clearInterval(timer);timer=null;output.textContent='Automatic clearance is waiting for clipboard access. Return to this page or select Clear Clipboard and allow access to finish.';retry.textContent='Clear Clipboard';retry.hidden=false;}
        finally{clearing=false;}
    }
    async function copy(){
        if(!secret)return;
        retry.disabled=true;
        try{await navigator.clipboard.writeText(secret);deadline=Date.now()+60000;retry.hidden=true;clearInterval(timer);timer=setInterval(check,1000);await check();}
        catch{output.textContent='The key was created, but clipboard access was blocked. Select Copy Key to retry; the key is never displayed.';retry.textContent='Copy Key';retry.hidden=false;}
        finally{retry.disabled=false;}
    }
    retry.onclick=()=>deadline?check():copy();
    form.addEventListener('submit',async event=>{
        event.preventDefault();if(secret)return;
        if(!navigator.clipboard){output.textContent='Clipboard access is unavailable. Use a supported browser over HTTPS to create and copy a key.';return;}
        const button=form.querySelector('button');button.disabled=true;
        try{const result=await accessRequest('/user/keys','POST',Object.fromEntries(new FormData(form)));secret=result.key;form.reset();await copy();await listKeys();}
        catch(error){output.textContent=error.message;if(!secret)button.disabled=false;}
    });
    window.addEventListener('focus',check);document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();});
    window.addEventListener('beforeunload',event=>{if(secret){event.preventDefault();event.returnValue='';}});
}
