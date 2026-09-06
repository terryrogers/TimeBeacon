function alternateColour(hex) {
    // Reflect lightness while retaining hue and saturation.
    const rgb=hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255),hi=Math.max(...rgb),lo=Math.min(...rgb),l=(hi+lo)/2;
    if(hi===lo)return '#'+rgb.map(()=>Math.round((1-l)*255).toString(16).padStart(2,'0')).join('');
    const shift=1-2*l;
    return '#'+rgb.map(x=>Math.round(Math.max(0,Math.min(1,x+shift))*255).toString(16).padStart(2,'0')).join('');
}
function applyClientColours(palette) {
    if(!palette)return;
    let style=document.getElementById('client-palette');if(!style){style=document.createElement('style');style.id='client-palette';document.head.append(style);}
    const rules=[];
    for(const mode of ['light','dark'])for(const [key,state] of [['healthy','ok'],['warning','warning'],['critical','critical'],['unknown','unknown']]) {
        const pair=palette[key];if(!pair || !/^#[0-9a-f]{6}$/i.test(pair.background) || !/^#[0-9a-f]{6}$/i.test(pair.foreground))continue;
        const bg=mode===palette.mode?pair.background:alternateColour(pair.background),fg=mode===palette.mode?pair.foreground:alternateColour(pair.foreground);
        const selectors=[`.summary-card.${state}`,`.client-head.${state}`].map(s=>`[data-theme="${mode}"] ${s}`).join(',');
        rules.push(`${selectors}{background:${bg}!important;color:${fg}!important}`);
        rules.push(`[data-theme="${mode}"] .client-head.${state} .client-ip{color:${fg}!important}`);
    }
    style.textContent=rules.join('\n');
}
function initialiseClientColours(palette) {
    const root=document.getElementById('client-colour-fields');if(!root)return;
    const mode=document.getElementById('client-colour-mode');mode.checked=palette.mode==='dark';
    function update(){document.getElementById('client-colour-mode-label').textContent=mode.checked?'Dark Mode':'Light Mode';for(const row of root.children){row.querySelector('.colour-preview').style.background=row.querySelector('[data-colour=background]').value;row.querySelector('.colour-preview').style.color=row.querySelector('[data-colour=foreground]').value;}}
    for(const [state,title] of [['healthy','Healthy'],['warning','Warning'],['critical','Critical'],['unknown','Unknown']]){
        const row=document.createElement('div');row.className='client-colour-row';row.dataset.state=state;
        const preview=document.createElement('strong');preview.className='colour-preview';preview.textContent=title;row.append(preview);
        for(const [kind,label] of [['background','Background'],['foreground','Text']]){const wrapper=document.createElement('label');wrapper.textContent=label;const input=document.createElement('input');input.type='color';input.dataset.colour=kind;input.value=palette[state][kind];input.setAttribute('aria-label',title+' '+label.toLowerCase()+' colour');input.oninput=update;wrapper.append(input);row.append(wrapper);}root.append(row);
    }
    mode.onchange=update;update();
}
function selectedClientColours(){const palette={mode:document.getElementById('client-colour-mode').checked?'dark':'light'};for(const row of document.getElementById('client-colour-fields').children)palette[row.dataset.state]=Object.fromEntries([...row.querySelectorAll('input')].map(input=>[input.dataset.colour,input.value]));return palette;}
