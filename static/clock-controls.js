let clockChangePending=false;
async function changeClocks(clocks,version,onSaved,reload,message='Clock order saved.'){
    if(clockChangePending)return;
    clockChangePending=true;
    document.querySelectorAll('.clock-drag,.clock-remove,.clock-row-actions button,.clock-reset').forEach(b=>b.disabled=true);
    try{
        const payload=await accessRequest('/dashboard/settings','PATCH',{version,clocks});
        await onSaved(payload);feedback('clock-feedback',message);return payload;
    }catch(error){try{await reload();}catch{}feedback('clock-feedback',error.message);}
    finally{clockChangePending=false;document.querySelectorAll('.clock-drag,.clock-remove,.clock-row-actions button,.clock-reset').forEach(b=>b.disabled=false);}
}
function configureClockControls(container,clocks,version,onSaved,reload,defaults,warmReset=false){
    const reset=document.getElementById('reset-clocks');
    if(reset){reset.hidden=!can('clocks.amend');reset.onclick=async event=>{
        event.preventDefault();event.stopPropagation();
        const payload=await changeClocks(defaults,version,onSaved,reload,'Clocks reset to system defaults.');
        if(payload&&warmReset&&payload.settings.clock_backgrounds&&can('dashboard.view')&&can('clocks.view')){
            await Promise.all(defaults.map(clock=>preloadClockImage(clock.zone)));
        }
    };}
    if(!can('clocks.amend'))return;
    for(const [index,row] of [...container.children].entries()){
        const clock=clocks[index];row.dataset.clockZone=clock.zone;
        const card=row.classList.contains('clock-card');
        const actions=card?row:document.createElement('div');if(!card){actions.className='clock-row-actions';row.append(actions);}
        const handle=uiButton('⠿',()=>{});handle.className='ui icon button clock-drag';
        handle.title='Drag to Reorder · Arrow Keys Also Move This Clock';
        handle.setAttribute('aria-label','Reorder '+clock.name+' clock');
        const remove=uiButton(card?'×':'Remove',()=>changeClocks(clocks.filter(c=>c.zone!==clock.zone),version,onSaved,reload,'Clock removed.'));
        if(card)remove.className='ui icon button clock-remove';
        remove.setAttribute('aria-label','Remove '+clock.name+' clock');actions.append(handle,remove);
        const move=destination=>{
            if(destination===index||destination<0||destination>=clocks.length)return;
            const ordered=[...clocks];ordered.splice(index,1);ordered.splice(destination,0,clock);
            return changeClocks(ordered,version,onSaved,reload).then(()=>{
                const moved=[...container.querySelectorAll('[data-clock-zone]')].find(r=>r.dataset.clockZone===clock.zone);
                moved?.querySelector('.clock-drag')?.focus();
            });
        };
        handle.onkeydown=event=>{const step={ArrowLeft:-1,ArrowUp:-1,ArrowRight:1,ArrowDown:1}[event.key];if(step){event.preventDefault();move(index+step);}};
        let drag=null;
        const finish=event=>{
            if(!drag)return;const state=drag;drag=null;
            row.classList.remove('clock-dragging');container.querySelectorAll('.clock-drop-target').forEach(r=>r.classList.remove('clock-drop-target'));
            if(handle.hasPointerCapture(event.pointerId))handle.releasePointerCapture(event.pointerId);
            if(event.type==='pointerup'&&state.moved&&state.target!==null)move(state.target);
        };
        handle.onpointerdown=event=>{if(event.button!==0||clockChangePending)return;event.preventDefault();handle.focus();drag={x:event.clientX,y:event.clientY,target:null,moved:false};handle.setPointerCapture(event.pointerId);};
        handle.onpointermove=event=>{
            if(!drag)return;
            if(Math.hypot(event.clientX-drag.x,event.clientY-drag.y)<6&&!drag.moved)return;
            drag.moved=true;row.classList.add('clock-dragging');
            container.querySelectorAll('.clock-drop-target').forEach(r=>r.classList.remove('clock-drop-target'));
            const target=document.elementFromPoint(event.clientX,event.clientY)?.closest('[data-clock-zone]');
            drag.target=target&&target.parentElement===container?[...container.children].indexOf(target):null;
            if(drag.target!==null&&target!==row)target.classList.add('clock-drop-target');
            const rect=container.getBoundingClientRect();
            if(event.clientY<rect.top+35)container.scrollTop-=18;else if(event.clientY>rect.bottom-35)container.scrollTop+=18;
        };
        handle.onpointerup=finish;handle.onpointercancel=finish;
    }
}
