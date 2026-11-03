/* Input completion only. Clinical completeness and scores are owned by the server. */
(function installSourceImageRetention(){
  if(typeof window==='undefined'||typeof document==='undefined')return;
  const imageInput=document.getElementById('imageInput');
  if(!imageInput||typeof DataTransfer==='undefined')return;
  const MAX_IMAGES=6;
  let retained=[];
  let replaying=false;

  const sameFile=(a,b)=>a&&b&&a.name===b.name&&a.size===b.size&&a.lastModified===b.lastModified;
  const setFiles=files=>{
    const transfer=new DataTransfer();
    files.slice(0,MAX_IMAGES).forEach(file=>transfer.items.add(file));
    imageInput.files=transfer.files;
    retained=[...imageInput.files];
  };
  const ageSnapshot=()=>{
    const input=document.getElementById('age');
    const row=document.getElementById('manualAgeRow');
    if(!input)return null;
    return {value:input.value,readOnly:input.readOnly,required:input.required,rowHidden:row?row.hidden:null};
  };
  const restoreAge=snapshot=>{
    if(!snapshot)return;
    queueMicrotask(()=>{
      const input=document.getElementById('age');
      const row=document.getElementById('manualAgeRow');
      if(!input)return;
      input.value=snapshot.value;input.readOnly=snapshot.readOnly;input.required=snapshot.required;
      if(row&&snapshot.rowHidden!==null)row.hidden=snapshot.rowHidden;
    });
  };
  const chooseReplacementIndex=files=>{
    const list=files.map((file,index)=>`${index+1}. ${file.name}`).join('\n');
    const locale=window.CERAI_I18N?.locale;
    const promptText=locale==='tr'
      ?`Altı görüntü zaten yüklü. Değiştirilecek görüntünün numarasını girin:\n${list}`
      :`Six images are already loaded. Enter the number of the image to replace:\n${list}`;
    const value=window.prompt(promptText,'');
    if(value===null)return null;
    const index=Number.parseInt(value,10)-1;
    return Number.isInteger(index)&&index>=0&&index<files.length?index:null;
  };
  const sharedFilesFromRenderedLinks=async()=>{
    if(!window.caches)return [];
    const links=[...document.querySelectorAll('#selectedFiles a.selected-file')]
      .map(link=>({url:link.getAttribute('href')||'',name:(link.textContent||'shared-image.jpg').trim()}))
      .filter(item=>item.url.includes('/__hc_share__/'));
    if(!links.length)return [];
    const files=[];
    for(const item of links){
      const response=await fetch(item.url,{cache:"no-store"});
      if(!response.ok)continue;
      const blob=await response.blob();
      files.push(new File([blob],item.name,{type:blob.type||'image/jpeg',lastModified:Date.now()}));
    }
    return files;
  };
  const mergeFiles=(base,selected)=>{
    const next=[...base];
    for(const file of selected){
      const exact=next.findIndex(existing=>sameFile(existing,file));
      if(exact>=0){next[exact]=file;continue;}
      const sameName=next.findIndex(existing=>existing.name===file.name);
      if(sameName>=0){next[sameName]=file;continue;}
      if(next.length<MAX_IMAGES){next.push(file);continue;}
      const replaceIndex=chooseReplacementIndex(next);
      if(replaceIndex===null)return null;
      next[replaceIndex]=file;
    }
    return next;
  };

  imageInput.addEventListener('change',event=>{
    if(replaying)return;
    const selected=[...imageInput.files];
    if(!selected.length)return;
    if(!retained.length){
      const sharedLinks=document.querySelectorAll('#selectedFiles a.selected-file[href*="/__hc_share__/"]');
      if(sharedLinks.length){
        event.stopImmediatePropagation();
        const snapshot=ageSnapshot();
        sharedFilesFromRenderedLinks().then(shared=>{
          const merged=mergeFiles(shared,selected);
          if(!merged){setFiles(shared);restoreAge(snapshot);return;}
          setFiles(merged);replaying=true;imageInput.dispatchEvent(new Event('change',{bubbles:true}));replaying=false;restoreAge(snapshot);
        }).catch(()=>{
          setFiles(selected);replaying=true;imageInput.dispatchEvent(new Event('change',{bubbles:true}));replaying=false;restoreAge(snapshot);
        });
        return;
      }
      retained=[...selected];
      return;
    }
    const snapshot=ageSnapshot();
    const merged=selected.length>=5?selected.slice(0,MAX_IMAGES):mergeFiles(retained,selected);
    if(!merged){event.stopImmediatePropagation();setFiles(retained);restoreAge(snapshot);return;}
    setFiles(merged);restoreAge(snapshot);
  },true);

  const wrapper=imageInput.closest('.file-picker-wrap')||imageInput.parentElement;
  if(wrapper&&!document.getElementById('source-image-retention-note')){
    const note=document.createElement('p');note.id='source-image-retention-note';note.className='note';
    note.textContent=window.CERAI_I18N?.locale==='tr'
      ?'Eksik veya okunamayan bir kaynak görüntü istenirse yalnızca yeni görüntüyü seçin. Mevcut hasta bilgileri ve seçilmiş görüntüler korunur.'
      :'If a source image is missing or unreadable, select only the new/replacement image. Existing patient information and selected images are retained.';
    wrapper.append(note);
  }
  window.CER_AI_SourceImageRetention={
    openPicker:()=>imageInput.click(),
    files:()=>[...retained],
    adopt:files=>setFiles([...files]),
    replaceAll:files=>{
      setFiles([...files]);
      replaying=true;
      try{imageInput.dispatchEvent(new Event('change',{bubbles:true}));}
      finally{replaying=false;}
    }
  };
})();

window.HCReadiness = class {
  constructor(panel) { this.panel=panel; this.regionUrls=[]; this.reset(); }
  reset() {
    if(this.validationPanel){this.validationPanel.hidden=true;this.validationPanel.replaceChildren();}
    for(const url of this.regionUrls||[])URL.revokeObjectURL(url);
    this.regionUrls=[];this.token=null;this.overrides={};this.sourceConfirmations={};this.hasCompletableInputs=false;this.requiresSourceReplacement=false;this.panel.hidden=true;this.panel.replaceChildren();
  }
  async loadSourceRegion(container,item,index=0) {
    const tr=value=>window.CERAI_I18N?.translate(value)??value;
    const status=document.createElement('span');status.textContent=tr('Loading unread Pentacam/topography region...');container.append(status);
    try{
      const request=window.ceraiFetch||window.fetch.bind(window);
      const response=await request('/assessment/source-region',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({assessment_token:this.token,eye:item.eye,key:item.key,index})
      });
      if(!response.ok)throw new Error('source region unavailable');
      const url=URL.createObjectURL(await response.blob());this.regionUrls.push(url);
      const image=document.createElement('img');image.src=url;image.alt=tr('Pentacam/topography region the application could not read');
      image.addEventListener('load',()=>status.remove());container.prepend(image);
    }catch(error){status.textContent=tr('The unread source region could not be displayed. Enter the value from the original Pentacam/topography image.');}
  }
  collect() {
    const current={};
    for(const input of this.panel.querySelectorAll('[data-source-form]')) {
      if(!input.dataset.sourceForm)continue;
      const original=document.getElementById(input.dataset.sourceForm);
      if(original){original.value=input.value;original.setCustomValidity('');}
    }
    for(const input of this.panel.querySelectorAll('[data-measurement]')) {
      if(!input.value.trim()) continue;
      let value=input.value;
      if(input.tagName!=='SELECT') {
        const raw=value.trim().replace(/\s+/g,'').replace(/[−–—﹣－]/g,'-').replace(/[＋﹢]/g,'+').replace(',','.');
        if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw)||!Number.isFinite(Number(raw))){
          const reason=window.CERAI_I18N?.locale==='tr'?'Geçerli bir sayı girin.':'Enter a valid number.';
          input.setCustomValidity?.(reason);
          if(input.form)this.validateForm(input.form);
          throw new Error(`${this.fieldLabel(input)} — ${reason}`);
        }
        value=Number(raw);
      }
      (current[input.dataset.eye]??={})[input.dataset.measurement]=value;
    }
    this.overrides=current;
    return current;
  }
  fieldLabel(field) {
    const tr=value=>window.CERAI_I18N?.translate(value)??value;
    const eye=field.dataset.eye||/^(od|os)_/i.exec(field.dataset.sourceForm||field.id||'')?.[1]?.toUpperCase();
    const label=field.dataset.completionLabel||field.labels?.[0]?.textContent||field.closest?.('.row')?.querySelector('label')?.textContent||field.dataset.measurement||field.id;
    const side=window.CERAI_I18N?.locale==='tr'?{OD:'OD (Sağ göz)',OS:'OS (Sol göz)'}:{OD:'OD (Right eye)',OS:'OS (Left eye)'};
    return [side[eye]||eye,tr(label.trim())].filter(Boolean).join(' — ');
  }
  validateForm(form,focus=true) {
    const turkish=window.CERAI_I18N?.locale==='tr';
    if(!this.validationPanel){
      this.validationPanel=document.createElement('div');
      this.validationPanel.className='note';this.validationPanel.setAttribute('role','alert');
      this.panel.before(this.validationPanel);
      for(const event of ['input','change'])form.addEventListener(event,()=>{
        if(!this.validationPanel.hidden)this.validateForm(form,false);
      });
    }
    const copies=new Map([...form.querySelectorAll('[data-source-form]')].map(field=>[field.dataset.sourceForm,field]));
    const errors=new Map();
    for(const field of form.elements){
      const target=copies.get(field.id)||field;
      if(!field.willValidate||field.validity.valid){
        if(target.dataset.validationMarked){target.removeAttribute('aria-invalid');delete target.dataset.validationMarked;}
        continue;
      }
      const v=field.validity;
      // badInput precedes valueMissing: browsers expose malformed numeric input as an empty value.
      const reason=v.badInput||v.typeMismatch
        ?(turkish?'Geçerli bir sayı girin.':'Enter a valid number.')
        :v.customError?field.validationMessage
        :v.valueMissing?(turkish?'Bu zorunlu alan boş.':'This required field is empty.')
        :v.rangeUnderflow?(turkish?`Değer en az ${field.min} olmalı.`:`Value must be at least ${field.min}.`)
        :v.rangeOverflow?(turkish?`Değer en fazla ${field.max} olmalı.`:`Value must be at most ${field.max}.`)
        :v.stepMismatch?(turkish?`Sayısal hassasiyet uygun değil: ${field.step||'1'} adımlarında bir değer girin.`:`Invalid numeric precision: enter a value in steps of ${field.step||'1'}.`)
        :field.validationMessage;
      errors.set(target,`${this.fieldLabel(target)} — ${reason}`);
    }
    this.validationPanel.replaceChildren();this.validationPanel.hidden=!errors.size;
    for(const [field,message] of errors){
      field.setAttribute('aria-invalid','true');field.dataset.validationMarked='true';
      const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=message;
      button.addEventListener('click',()=>this.focusField(field));
      const row=document.createElement('p');row.append(button);this.validationPanel.append(row);
    }
    if(errors.size&&focus)this.focusField(errors.keys().next().value);
    return [...errors.values()].join('\n');
  }
  focusField(field) {
    for(let parent=field.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
    field.scrollIntoView({block:'center',behavior:'instant'});field.focus({preventScroll:true});
  }
  collectSourceConfirmations() {
    const current={};
    for(const input of this.panel.querySelectorAll('[data-source-confirmation]')) {
      if(input.value)current[input.dataset.sourceConfirmation]=input.value;
    }
    this.sourceConfirmations=current;
    return current;
  }
  show(response) {
    for(const url of this.regionUrls||[])URL.revokeObjectURL(url);
    this.regionUrls=[];
    this.token=response.assessment_token;
    this.hasCompletableInputs=false;
    this.requiresSourceReplacement=false;
    this.panel.replaceChildren();
    this.panel.hidden=response.workflow_status==='READY';
    if(this.panel.hidden)return false;
    const tr=value=>window.CERAI_I18N?.translate(value)??value;
    const heading=document.createElement('h3'); heading.textContent=tr('Required information — no report has been generated');
    this.panel.append(heading);
    const note=document.createElement('p');note.textContent=tr('Complete all items below, then continue. Existing inputs and image readings are retained. No calculation is required from the surgeon.');this.panel.append(note);
    const seen=new Set();
    const activeMeasurements=new Set();
    const activeSourceConfirmations=new Set();
    for(const item of response.input_requests||[]) {
      const identity=[item.eye,item.form_id||item.key,item.kind].join(':');
      if(seen.has(identity))continue;seen.add(identity);
      const row=document.createElement('div');row.className='row';
      const label=document.createElement('label');
      const required=(item.required_for||[]).map(tr).join('/');
      label.textContent=[tr(item.eye),tr(item.label),required?`${tr('Required for')} ${required}`:'',item.source_screen?tr(item.source_screen):'',item.source_box?tr(item.source_box):''].filter(Boolean).join(' — ');
      row.append(label);
      if(item.source_region){
        row.classList.add('completion-with-source');
        const region=document.createElement('div');region.className='completion-source-region';
        row.append(region);
        const count=Math.max(1,Number(item.source_region_count)||1);
        for(let index=0;index<count;index++)this.loadSourceRegion(region,item,index);
      }
      let input;
      if(item.kind==='form') {
        const original=document.getElementById(item.form_id);
        if(original){
          input=original.cloneNode(true);input.removeAttribute('id');input.removeAttribute('name');input.removeAttribute('required');
          input.readOnly=false;input.value=original.value;input.dataset.sourceForm=item.form_id;input.required=true;
          if(item.form_id==='age'){
            const originalRow=original.closest('.row');if(originalRow)originalRow.hidden=true;
            original.required=false;input.required=true;
          }
          input.addEventListener('input',()=>{original.value=input.value;original.setCustomValidity('');original.dispatchEvent(new Event('input',{bubbles:true}));});
          input.addEventListener('change',()=>{original.value=input.value;original.dispatchEvent(new Event('change',{bubbles:true}));});
        }
      }else if(item.kind==='number'||item.kind==='select'||item.kind==='confirmation') {
        input=document.createElement(item.kind==='number'?'input':'select');
        if(item.kind!=='number')for(const value of ['',...(item.options||[])]){const option=document.createElement('option');option.value=value;option.textContent=tr(value||'Select');input.append(option);}
        else {input.type='text';input.inputMode='decimal';input.autocomplete='off';}
        if(item.destination==='source_confirmation'){
          activeSourceConfirmations.add(item.key);
          input.dataset.sourceConfirmation=item.key;
          input.value=this.sourceConfirmations[item.key]??'';
        }else{
          activeMeasurements.add(`${item.eye}:${item.key}`);
          input.dataset.measurement=item.key;input.dataset.eye=item.eye;
          input.value=this.overrides[item.eye]?.[item.key]??'';
        }
      }
      if(input&&item.help&&item.kind==='form'){
        const help=document.createElement('p');help.className='note';help.textContent=tr(item.help);row.append(help);
      }
      if(input){this.hasCompletableInputs=true;input.required=true;input.id=`completion_${seen.size}`;input.dataset.eye=item.eye;input.dataset.completionLabel=item.label;label.htmlFor=input.id;row.append(input);
        input.addEventListener('input',()=>input.setCustomValidity(''));
      }
      else {
        row.classList.add('completion-blocker');
        const help=document.createElement('span');help.textContent=tr(item.help);row.append(help);
        if(item.destination!=='separate_pathway'){
          this.requiresSourceReplacement=true;
          const replace=document.createElement('button');replace.type='button';replace.className='secondary';
          replace.textContent=window.CERAI_I18N?.locale==='tr'?'Kaynak görüntü ekle/değiştir':'Add/replace source image';
          replace.addEventListener('click',()=>window.CER_AI_SourceImageRetention?.openPicker());
          row.append(replace);
        }
      }
      if(item.destination==='source_confirmation'){
        this.requiresSourceReplacement=true;
        const replace=document.createElement('button');replace.type='button';replace.className='secondary';
        replace.textContent=window.CERAI_I18N?.locale==='tr'?'Görüntüleri kontrol et / ekle':'Check/add images';
        replace.addEventListener('click',()=>window.CER_AI_SourceImageRetention?.openPicker());
        row.append(replace);
        const help=document.createElement('span');help.textContent=tr(item.help);row.append(help);
      }
      this.panel.append(row);
    }
    for(const [eye,values] of Object.entries(this.overrides)){
      for(const key of Object.keys(values))if(!activeMeasurements.has(`${eye}:${key}`))delete values[key];
      if(!Object.keys(values).length)delete this.overrides[eye];
    }
    for(const key of Object.keys(this.sourceConfirmations))if(!activeSourceConfirmations.has(key))delete this.sourceConfirmations[key];
    this.panel.scrollIntoView({behavior:'smooth',block:'start'});
    return true;
  }
};

