"use strict";
async function fetchJson(url) {
    const response = await fetch(url, {cache:"no-store", signal:AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error("Server data unavailable");
    return response.json();
}
let refreshing = false;
async function refreshServer() {
    if (refreshing) return;
    refreshing = true;
    try {
        const data = await fetchJson("/dashboard/status");
        document.getElementById("operating-system").textContent = data.system_information?.operating_system || "Unavailable";
        document.getElementById("hardware-details").textContent = data.system_information?.hardware || "Unavailable";
        setServerStatus(data.healthy ? "ok" : "error", data.healthy ? "Server Online" : "Server Needs Attention");
        const failed = Object.entries(data.checks || {}).filter(([,ok]) => !ok).map(([name]) => name.replaceAll("_"," "));
        document.getElementById("health-message").textContent = data.stale ? "Monitoring data is stale or still starting." : failed.length ? "Check: "+failed.join(", ") : "";
        for (const key of ["cpu","ram","storage","temperature"]) {
            const value = data.stale ? null : data.metrics?.[key];
            document.getElementById("system-"+key).textContent = Number.isFinite(value) ? value.toFixed(1)+(key === "temperature" ? " °C" : " %") : "Unavailable";
        }
        const used=data.metrics?.storage_used, percent=data.metrics?.storage;
        document.getElementById("system-storage").textContent=!data.stale && Number.isFinite(used) && Number.isFinite(percent) ? `${(used/1e9).toFixed(1)} GB (${percent.toFixed(1)}%)` : "Unavailable";
        document.getElementById("time-server-heading").textContent=(data.time_daemon && !data.time_daemon.startsWith("Time Server") ? data.time_daemon+" " : "")+"Time Server Status";
        document.querySelector(".host-label").textContent=(data.hostname || "")+" Server Dashboard";
        acquisitionData=data; renderAcquisition();
        const uptime = data.metrics?.uptime;
        document.getElementById("system-uptime").textContent = Number.isFinite(uptime) && !data.stale ? `${Math.floor(uptime/86400)}d ${Math.floor(uptime%86400/3600)}h` : "Unavailable";
        renderServiceDetails(data);
        await Promise.all([can("time.view") ? refreshTracking() : Promise.resolve(),refreshClients()]);
        hideError();
    } catch(error) {
        showError(error.message);
        setServerStatus("unknown","Server Status Unavailable");
    } finally { refreshing=false; }
}
async function configureTheme() {
    try {
        const solar = await fetchJson("/dashboard/solar");
        document.documentElement.dataset.theme=solar.theme;
        document.getElementById("solar-summary").textContent=settings.location+" · "+(solar.theme === "dark" ? "Night" : "Daylight");
    } catch { document.getElementById("solar-summary").textContent="Daylight calculation unavailable"; }
}
function configureSettings() {}
function configureClocks() {
    if (!document.getElementById("clock-form")) return;
    const zones=[...new Set(["UTC", ...(Intl.supportedValuesOf ? Intl.supportedValuesOf("timeZone") : DEFAULT_TIMEZONES.map(item => item.zone))])];
    const cityLabel=zone => zone === "UTC" ? "UTC (Coordinated Universal Time)" : zone.split("/").slice(1).join(" / ").replaceAll("_"," ")+" — "+zone.split("/")[0];
    zones.sort((a,b)=>cityLabel(a).localeCompare(cityLabel(b)));
    const placeholder=document.createElement("option"); placeholder.value=""; placeholder.textContent="Choose a city or time zone…";
    document.getElementById("clock-zone").replaceChildren(placeholder,...zones.map(zone => {const option=document.createElement("option"); option.value=zone; option.textContent=cityLabel(zone); return option;}));
    document.getElementById("clock-form").addEventListener("submit", async event => {
        event.preventDefault();
        const input=document.getElementById("clock-zone"), feedback=document.getElementById("clock-feedback");
        let zone;
        try {zone=new Intl.DateTimeFormat("en",{timeZone:input.value.trim()}).resolvedOptions().timeZone;}
        catch {feedback.textContent="Choose a valid time zone such as Europe/London."; return;}
        if(TIMEZONES.some(item => item.zone === zone)) {feedback.textContent="That clock is already added."; return;}
        try {
            await saveSharedSettings({clocks:[...TIMEZONES,{zone,name:zone.split("/").pop().replaceAll("_"," ")}]});
            input.value="";feedback.textContent="Clock added to your account.";
        } catch(error) {feedback.textContent=error.message;}

    });
}
const GRAPH_METRICS={gps_used:["Satellites used",""],gps_visible:["Satellites visible",""],gps_mode:["GPS fix mode",""],gps_pps:["PPS receiving (1=yes, 0=no)",""],gps_hdop:["Horizontal dilution of precision",""],gps_tdop:["Time dilution of precision",""],cpu:["CPU","%"],ram:["RAM","%"],storage:["Storage","%"],temperature:["CPU Temperature","°C"],stratum:["Stratum",""],last_offset:["Last Offset","ms"],rms_offset:["RMS Offset","ms"],ntp_rtt:["NTP RTT","ms"]};
function configureGraphs() {
    document.getElementById("history-duration").addEventListener("change",event=>{
        graphPreset=event.target.value;
        graphEnd=Math.floor(Date.now()/1000);
        graphStart=graphPreset === "all" ? (graphBounds.first ?? 0) : graphEnd-Number(graphPreset)*60;
        showGraph(graphKey,false);
    });
    const applyPeriod=()=>{
        const start=Date.parse(document.getElementById("history-start").value)/1000,end=Date.parse(document.getElementById("history-end").value)/1000;
        if(!Number.isFinite(start)||!Number.isFinite(end)||start>=end) {document.getElementById("history-message").textContent="Choose a start before the end.";return;}
        graphPreset="custom";graphStart=Math.floor(start);graphEnd=Math.floor(end);showGraph(graphKey,false);
    };
    for(const id of ["history-start","history-end"]) document.getElementById(id).addEventListener("change",applyPeriod);
    for(const [id,key] of [["stratum","stratum"],["last-offset","last_offset"],["rms-offset","rms_offset"],["ntp-rtt","ntp_rtt"]]) {
        const card=document.getElementById(id).closest(".metric");
        card.dataset.history=key; card.tabIndex=0; card.setAttribute("role","button");
        card.setAttribute("aria-label",GRAPH_METRICS[key][0]+", view history graph");
        card.addEventListener("keydown",event => {if(["Enter"," "].includes(event.key)) {event.preventDefault(); card.click();}});
    }
    document.querySelectorAll("[data-history]").forEach(card => card.addEventListener("click",() => showGraph(card.dataset.history)));
}
let graphKey=null, graphStart=0, graphEnd=0, graphBounds={}, graphRequest=0, graphPreset="60";
function localInput(seconds) {const date=new Date(seconds*1000);return new Date(date-date.getTimezoneOffset()*60000).toISOString().slice(0,16);}
async function showGraph(key, reset=true) {
    if(!can(["cpu","ram","storage","temperature","uptime"].includes(key) ? "server.history" : "time.history"))return;
    graphKey=key;
    if(reset) {graphPreset="60";graphEnd=Math.floor(Date.now()/1000);graphStart=graphEnd-3600;}
    document.getElementById("history-start").value=localInput(graphStart);
    document.getElementById("history-end").value=localInput(graphEnd);
    document.getElementById("history-duration").value=graphPreset;
    const requestId=++graphRequest;
    const dialog=document.getElementById("history-dialog"), graph=document.getElementById("history-graph");
    const message=document.getElementById("history-message"), [label,unit]=GRAPH_METRICS[key];
    document.getElementById("history-title").textContent="Historic "+(key==="cpu" ? "CPU Usage" : label);
    graph.replaceChildren(); document.getElementById("history-details").replaceChildren(); message.textContent="Loading history…";document.getElementById("history-gap").textContent="";document.getElementById("history-count").textContent="0 samples";
    if(!dialog.open) dialog.showModal();
    try {
        const payload=await fetchJson(`/dashboard/history?metric=${encodeURIComponent(key)}&start=${graphStart}&end=${graphEnd}`),end=graphEnd,start=graphStart;
        if(requestId!==graphRequest)return;
        graphBounds=payload.bounds || {};
        if(key.startsWith("gps_") || ["last_offset","rms_offset","ntp_rtt"].includes(key)) {
            const rows=[];let previous="";
            for(const sample of payload.samples) {
                const gps=sample.gps || {},values=[sample.acquisition?.selected ?? "Unavailable",gps.fix ?? "Unavailable",gps.used ?? "Unavailable",gps.visible ?? "Unavailable",gps.pps === undefined ? "Unavailable" : gps.pps ? "Receiving" : "No PPS"];
                const signature=JSON.stringify(values);if(signature!==previous){rows.push([graphDate(sample.timestamp*1000),...values]);previous=signature;}
            }
            const heading=document.createElement("h3");heading.textContent="GPS and time acquisition changes in displayed samples";
            document.getElementById("history-details").append(heading,dataTable(["Time","Selected source","GPS fix","Used","Visible","PPS"],rows));
        }
        const samples=payload.samples.filter(s => s.timestamp>=start && Number.isFinite(s.metrics[key]));
        if(!samples.length) {message.textContent="No samples available for this period."; document.getElementById("history-gap").textContent="Gaps indicate unavailable data."; return;}
        const values=samples.map(s => s.metrics[key]); let low=Math.min(...values), high=Math.max(...values);
        const margin=(high-low)*0.1 || 1; low-=margin; high+=margin;
        const svg=(name,attrs,text) => {const el=document.createElementNS("http://www.w3.org/2000/svg",name); for(const [k,v] of Object.entries(attrs)) el.setAttribute(k,v); if(text) el.textContent=text; graph.append(el); return el;};
        for(let i=0;i<=4;i++) {
            const y=25+i*60;
            svg("line",{x1:90,y1:y,x2:880,y2:y,stroke:"var(--border)"});
            svg("text",{x:80,y:y+5,"text-anchor":"end",fill:"var(--text)","font-size":12},(high-(high-low)*i/4).toFixed(2)+" "+unit);
            svg("text",{x:90+i*197.5,y:305,"text-anchor":i===0?"start":i===4?"end":"middle",fill:"var(--text)","font-size":12},graphTime((start+i*(end-start)/4)*1000));
        }
        let path="",previous=null,missingGap=false;
        const missing=payload.samples.filter(s=>!Number.isFinite(s.metrics[key])).map(s=>s.timestamp);
        for(const sample of samples) {
            const x=90+(sample.timestamp-start)/(end-start)*790,y=265-(sample.metrics[key]-low)/(high-low)*240;
            const unavailable=previous!==null && missing.some(t=>t>previous && t<sample.timestamp);missingGap ||= unavailable;
            path+=(previous===null || unavailable || sample.timestamp-previous>Math.max(90,(end-start)/1500*3) ? "M":"L")+x+","+y+" "; previous=sample.timestamp;
            if(samples.length===1) svg("circle",{cx:x,cy:y,r:4,fill:"var(--blue)"});
        }
        svg("path",{d:path,fill:"none",stroke:"var(--blue)","stroke-width":2});
        message.textContent="";
        document.getElementById("history-count").textContent=samples.length+" samples";
        const gapLimit=Math.max(90,(end-start)/1500*3);
        const hasGaps=missingGap || samples[0].timestamp-start>gapLimit || end-samples.at(-1).timestamp>gapLimit || samples.some((s,i)=>i>0 && s.timestamp-samples[i-1].timestamp>gapLimit);
        document.getElementById("history-gap").textContent=hasGaps ? "Gaps indicate unavailable data." : "";
    } catch {message.textContent="History unavailable. Close and try again.";}
}

function graphTime(milliseconds) {
    return new Date(milliseconds).toLocaleTimeString("en-US",{hour:"numeric",minute:"2-digit",hour12:true}).replace(/\s/g,"").toLowerCase();
}
function graphDate(milliseconds) {return new Date(milliseconds).toLocaleDateString()+" "+graphTime(milliseconds);}
let acquisitionData={};
function renderAcquisition() {
    const d=acquisitionData, gps=d.gps || {}, source=d.acquisition || {};
    const values={fix:gps.fix || "Unavailable",satellites:gps.visible == null ? "Unavailable" : `${gps.used ?? "?"} used / ${gps.visible} visible`,pps:gps.pps ? "Receiving pulses" : "No recent pulses",time:source.selected || "No selected source"};
    for(const [key,value] of Object.entries(values)) document.getElementById("acquisition-"+key).textContent=d.stale ? "Unavailable" : value;
}
function dataTable(headers,rows) {
    const wrap=document.createElement("div");wrap.className="table-scroll";
    const table=document.createElement("table"),head=table.createTHead().insertRow();
    headers.forEach(label=>{const th=document.createElement("th");th.textContent=label;head.append(th);});
    table.className="ui unstackable table";
    const body=table.createTBody();
    rows.forEach(row=>{const tr=body.insertRow();row.forEach(value=>{tr.insertCell().textContent=value ?? "Unavailable";});});
    wrap.append(table);return wrap;
}
function renderServiceDetails(data) {
    const body=document.getElementById("service-details-body");body.replaceChildren();
    document.getElementById("service-action-heading").hidden=!can("admin");
    for(const service of data.services || []) {
        const row=body.insertRow();
        const values=[service.name,service.startup || "Unknown",data.stale ? "Stale" : service.status || service.state,
            !data.stale && Number.isFinite(service.cpu) ? service.cpu.toFixed(2)+"%" : "Sampling…",
            !data.stale && Number.isFinite(service.ram) ? (service.ram/1048576).toFixed(1)+" MiB"+(service.ram_kind === "RSS" ? " (RSS)" : "") : "Unavailable"];
        values.forEach(value=>{row.insertCell().textContent=value;});
        if(can("admin")) {
            const cell=row.insertCell();
            if(service.running===false || (service.state && service.state!=="active")) {
                const button=uiButton("Fix",()=>showServiceRepair(service.name));
                button.classList.add("small","primary");button.setAttribute("aria-label","Fix "+service.name);cell.append(button);
            }
        }
    }
    const checks=Object.entries(data.checks || {}).map(([name,ok])=>{const li=document.createElement("li");li.textContent=name.replaceAll("_"," ")+": "+(data.stale ? "Stale" : ok ? "Passed" : "Needs attention");return li;});
    document.getElementById("health-check-details").replaceChildren(...checks);
}
let repairBusy=false, repairPreview=null;
async function showServiceRepair(unit) {
    if(repairBusy)return;
    repairPreview=null;
    const dialog=document.getElementById("service-repair-dialog"),message=document.getElementById("service-repair-message"),button=document.getElementById("service-repair-confirm");
    document.getElementById("service-repair-unit").textContent=unit;
    message.textContent="Checking current service state…";button.hidden=true;button.disabled=true;dialog.showModal();
    repairBusy=true;
    try {
        repairPreview=await accessRequest("/administration/services/repair?unit="+encodeURIComponent(unit));
        message.textContent=repairPreview.message;button.textContent=repairPreview.label;button.hidden=!repairPreview.action;button.disabled=false;
    } catch(error) {message.textContent=error.message;}
    finally {repairBusy=false;}
}
async function confirmServiceRepair() {
    if(repairBusy || !repairPreview?.action)return;
    repairBusy=true;
    const button=document.getElementById("service-repair-confirm"),message=document.getElementById("service-repair-message");
    button.disabled=true;message.textContent="Applying service action and checking current health…";
    try {
        const {unit,action,config_version}=repairPreview;
        const result=await accessRequest("/administration/services/repair","POST",{unit,action,config_version});
        message.textContent=result.message;document.getElementById("service-action-feedback").textContent=result.message;button.hidden=true;
        while(refreshing)await new Promise(resolve=>setTimeout(resolve,50));
        await refreshServer();
    } catch(error) {message.textContent=error.message;button.hidden=true;await refreshServer();}
    finally {repairBusy=false;repairPreview=null;}
}
function showAcquisition(key) {
    const gps=acquisitionData.gps || {},acq=acquisitionData.acquisition || {};
    const dialog=document.getElementById("acquisition-dialog"),content=document.getElementById("acquisition-content");
    const titles={fix:"GPS Fix Details",satellites:"Satellite Details",pps:"PPS Details",time:"Time Acquisition Details"};
    document.getElementById("acquisition-title").textContent=titles[key];content.replaceChildren();
    if(acquisitionData.stale){content.textContent="Monitoring data is stale.";dialog.showModal();return;}
    if(key==="satellites") {
        content.append(dataTable(["Satellite ID","GNSS ID","Elevation °","Azimuth °","Signal strength","Used in fix"],(gps.satellites || []).map(s=>[s.svid ?? s.PRN,s.gnssid,s.el,s.az,s.ss,s.used ? "Yes":"No"])));
        content.append(dataTable(["Dilution of precision","Value"],Object.entries(gps.dop || {})));
    } else if(key==="fix") {
        const names={time:"GPS time (UTC)",mode:"Fix mode",eph:"Horizontal error (m)",epv:"Vertical error (m)",ept:"Time error (s)"};
        content.append(dataTable(["Measurement","Value"],Object.entries(gps.fix_details || {}).map(([name,value])=>[names[name] || name,value])));
    } else if(key==="pps") {
        content.append(dataTable(["GPSD PPS field","Value"],Object.entries(gps.pps_details || {})));
    } else {
        content.append(dataTable(["Source","State","Stratum","Reach","Last RX","Measured offset (s)"],(acq.sources || []).map(s=>[s.name,s.state==="*" ? "Selected":s.state,s.stratum,s.reach,s.last_rx,s.measured_offset])));
    }
    if(!content.querySelector("tbody tr"))content.textContent="No detailed reports available yet.";
    const histories={fix:["gps_mode","gps_hdop"],satellites:["gps_used","gps_visible","gps_hdop","gps_tdop"],pps:["gps_pps"],time:["last_offset","rms_offset","ntp_rtt"]};
    const controls=document.createElement("div");controls.className="acquisition-history-controls";
    for(const metric of histories[key]) {const button=document.createElement("button");button.type="button";button.textContent=GRAPH_METRICS[metric][0]+" history";button.addEventListener("click",()=>showGraph(metric));controls.append(button);}
    content.append(controls);
    dialog.showModal();
}
function configureAcquisition() {
    document.getElementById("service-repair-confirm").addEventListener("click",confirmServiceRepair);
    document.getElementById("service-details-button").addEventListener("click",()=>document.getElementById("service-details-dialog").showModal());
    document.querySelectorAll("[data-acquisition]").forEach(card=>card.addEventListener("click",()=>showAcquisition(card.dataset.acquisition)));
}

let sharedVersion=0, sharedConfigVersion=0;
function applySharedSettings(payload) {
    sharedVersion=payload.version;sharedConfigVersion=payload.config_version || 0;
    settings={location:payload.settings.location,latitude:payload.settings.latitude,longitude:payload.settings.longitude,clock_backgrounds:payload.settings.clock_backgrounds};
    TIMEZONES=payload.settings.clocks;
    buildClocks();updateClocks();configureTheme();renderClockSettings();
}
async function loadSharedSettings() {
    try {const payload=await fetchJson("/dashboard/settings");if(payload.version!==sharedVersion || (payload.config_version || 0)!==sharedConfigVersion)applySharedSettings(payload);}
    catch(error) {showError("Shared settings unavailable: "+error.message);}
}
async function saveSharedSettings(changes,version=sharedVersion) {
    if(!version)throw new Error("Shared settings have not loaded. Reload and try again.");
    const response=await fetch("/dashboard/settings",{method:"PATCH",headers:{"Content-Type":"application/json","X-Dashboard-Settings":"1"},body:JSON.stringify({version,...changes}),signal:AbortSignal.timeout(15000)});
    if(!response.ok) {if(response.status===409) {await loadSharedSettings();throw new Error("Settings changed in another browser. Review and save again.");}throw new Error("Settings could not be saved. Please try again.");}
    applySharedSettings(await response.json());
}
