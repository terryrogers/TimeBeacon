async function initialiseSignIn(){
    document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
    let resetToken=new URLSearchParams(location.hash.slice(1)).get('reset')||'';
    if(location.hash)history.replaceState(null,'',location.pathname);
    const stage=name=>{document.querySelectorAll('.signin-stage').forEach(panel=>panel.hidden=panel.dataset.stage!==name);$('restart-signin').hidden=name==='password'||name==='codes';feedback('login-feedback','');document.querySelector('.signin-stage:not([hidden]) input')?.focus();};
    const complete=async()=>{document.querySelectorAll('.signin-card form').forEach(form=>form.reset());$('signin-recovery-codes').textContent='';const me=await accessRequest('/auth/me');location.replace(me.permissions.includes('dashboard.view')?'/':'/user-settings');};
    const proceed=async result=>{if(result.stage==='complete')return complete();stage(result.stage);if(result.stage==='enroll'){const enrollment=await accessRequest('/auth/enrollment/start','POST',{});$('signin-enrollment-qr').src=enrollment.qr;$('signin-enrollment-secret').textContent=enrollment.secret;}};
    submit('login-form',async form=>{const body=values(form);form.elements.password.value='';await proceed(await accessRequest('/auth/login','POST',body));},'login-feedback');
    submit('factor-form',async form=>{const body=values(form);form.reset();await proceed(await accessRequest('/auth/second-factor','POST',body));},'login-feedback');
    submit('recovery-form',async form=>{const body=values(form);form.reset();await proceed(await accessRequest('/auth/second-factor','POST',{...body,recovery:true}));},'login-feedback');
    submit('required-password-form',async form=>{if(form.elements.required_password.value!==form.elements.confirm.value)throw Error('The passwords do not match.');const password=form.elements.required_password.value;form.reset();await proceed(await accessRequest('/auth/change-required-password','POST',{password}));},'login-feedback');
    $('no-authenticator-link').onclick=event=>{event.preventDefault();stage('recovery');};
    $('back-to-authenticator').onclick=event=>{event.preventDefault();stage('factor');};
    $('forgot-password-link').onclick=event=>{event.preventDefault();$('forgot-form').elements.account.value=$('login-form').elements.username.value;stage('forgot');};
    $('restart-signin').onclick=async event=>{event.preventDefault();try{await accessRequest('/auth/logout','POST',{});location.replace('/login');}catch(error){feedback('login-feedback',error.message);}};
    submit('forgot-form',async form=>{const result=await accessRequest('/auth/forgot-password','POST',{username:form.elements.account.value});feedback('login-feedback',result.message);},'login-feedback');
    submit('reset-password-form',async form=>{if(form.elements.new_password.value!==form.elements.confirm.value)throw Error('The passwords do not match.');const password=form.elements.new_password.value;form.reset();const result=await accessRequest('/auth/reset-password','POST',{token:resetToken,password});resetToken='';stage('password');feedback('login-feedback',result.message);},'login-feedback');
    $('email-recovery-admin').onclick=async()=>{const button=$('email-recovery-admin');button.disabled=true;try{const result=await accessRequest('/auth/recovery-request','POST',{});feedback('login-feedback',result.message);}catch(error){feedback('login-feedback',error.message);}finally{button.disabled=false;}};
    submit('signin-enrollment-form',async form=>{const body=values(form);form.reset();const result=await accessRequest('/auth/enrollment/confirm','POST',body);$('signin-enrollment-qr').removeAttribute('src');$('signin-enrollment-secret').textContent='';stage('codes');$('signin-recovery-codes').textContent=result.recovery_codes.join('\n');},'login-feedback');
    $('finish-enrollment').onclick=()=>complete().catch(error=>feedback('login-feedback',error.message));
    window.addEventListener('hashchange',()=>{const token=new URLSearchParams(location.hash.slice(1)).get('reset');if(token){resetToken=token;history.replaceState(null,'',location.pathname);stage('reset');}});
    stage(resetToken?'reset':'password');
}

async function initialiseSecurityAdmin(){
    const result=await accessRequest('/administration/security');
    let version=result.version;
    const select=$('recovery-administrator');select.replaceChildren(new Option('Not Configured',''));
    result.administrators.forEach(user=>select.add(new Option((user.name||user.username)+' · '+user.email,user.id)));
    select.value=result.settings.recovery_admin_id||'';$('enforce-2fa').checked=result.settings.enforce_2fa;
    submit('admin-security-form',async()=>{const saved=await accessRequest('/administration/security','PUT',{version,enforce_2fa:$('enforce-2fa').checked,recovery_admin_id:select.value?Number(select.value):null});version=saved.version;feedback('page-feedback','Security settings saved.');});
    const list=$('recovery-requests');list.replaceChildren();
    if(!result.requests.length)list.append(makeText('p','No pending recovery requests.','muted'));
    for(const request of result.requests){const row=makeText('div','','recovery-request');row.append(makeText('strong',request.name||request.username),makeText('span',request.username+' · '+new Date(request.created*1000).toLocaleString(),'muted'));if(currentUser.id===result.settings.recovery_admin_id){row.append(uiButton('Allow Authenticator Re-registration',()=>{$('recovery-approval-form').reset();$('recovery-request-id').value=request.id;$('recovery-request-user').textContent=request.name||request.username;feedback('recovery-approval-feedback','');$('recovery-approval-dialog').showModal();}));}list.append(row);}
    submit('recovery-approval-form',async form=>{const body=values(form);const result=await accessRequest('/administration/security/recovery/'+body.request_id,'POST',{password:body.password,code:body.code});form.reset();$('recovery-approval-dialog').close();feedback('page-feedback',result.message);await refreshRecoveryList();},'recovery-approval-feedback');
    async function refreshRecoveryList(){const updated=await accessRequest('/administration/security');if(!updated.requests.length)list.replaceChildren(makeText('p','No pending recovery requests.','muted'));else location.reload();}
    $('recovery-approval-dialog').addEventListener('close',()=>$('recovery-approval-form').reset());
}

async function initialiseEmailAdmin(){
    const result=await accessRequest('/administration/email');let version=result.version;
    const form=$('admin-email-form');fill(form,{hostname:'',port:587,security:'starttls',username:'',from_email:'',from_name:'TimeBeacon',public_url:location.origin,...result.settings});
    $('email-fields').disabled=false;form.elements.password.placeholder=result.settings.password_set?'Saved · Leave Blank To Keep':'SMTP Password';
    submit('admin-email-form',async form=>{const body=values(form);body.version=version;body.port=Number(body.port);const result=await accessRequest('/administration/email','PUT',body);version=result.version;form.elements.password.value='';form.elements.password.placeholder='Saved · Leave Blank To Keep';feedback('page-feedback','Email settings saved.');});
    submit('test-email-form',async form=>{feedback('email-test-feedback','Sending test email using the saved configuration…');const result=await accessRequest('/administration/email/test','POST',values(form));feedback('email-test-feedback',result.message);},'email-test-feedback');
}
