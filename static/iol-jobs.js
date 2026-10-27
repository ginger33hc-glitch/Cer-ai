/* Original image bytes are uploaded in retryable chunks; reading survives request loss. */
(() => {
  const CHUNK = 512 * 1024;
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  const message = (en, tr) => document.documentElement.lang === 'tr' ? tr : en;
  async function extract({files, patientName, requestId, onProgress = () => {}}) {
    async function request(url, options = {}) {
      for (let attempt = 0; attempt < 8; attempt++) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 30000);
        try {
          const response = await fetch(url, {...options, credentials: 'same-origin', signal: controller.signal});
          const data = await response.json();
          if (!response.ok) {
            const error = new Error(typeof data.detail === 'string' ? data.detail : message('The request could not be completed.', 'İstek tamamlanamadı.'));
            error.permanent = response.status < 500;
            error.restartRequired = response.status === 410;
            throw error;
          }
          return data;
        } catch (error) {
          if (error.permanent) throw error;
          if (attempt === 7) throw new Error(message('Connection could not be restored. Keep these images selected and press Read and evaluate images again to resume.', 'Bağlantı yeniden kurulamadı. Görüntüleri seçili tutup devam etmek için Görüntüleri oku ve değerlendir düğmesine tekrar basın.'));
          onProgress(message('Connection interrupted. Reconnecting…', 'Bağlantı kesildi. Yeniden bağlanılıyor…'));
        } finally { clearTimeout(timer); }
        await pause(Math.min(1000 * 2 ** attempt, 8000));
      }
    }
    onProgress(message('Preparing images…', 'Görüntüler hazırlanıyor…'));
    const manifest = [];
    for (const file of files) {
      const hash = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
      manifest.push({name:file.name, size:file.size, type:file.type || 'image/jpeg', sha256:[...new Uint8Array(hash)].map(b => b.toString(16).padStart(2,'0')).join('')});
    }
    let job = await request('/iol/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({request_id:requestId,patient_name:patientName,files:manifest})});
    const base = '/iol/jobs/' + encodeURIComponent(job.job_id);
    if (job.status === 'UPLOADING') {
      const total = files.reduce((sum, file) => sum + file.size, 0);
      const offsets = job.offsets.slice();
      for (let index = 0; index < files.length; index++) {
        while (offsets[index] < files[index].size) {
          onProgress(message('Uploading images', 'Görüntüler yükleniyor') + `: ${Math.floor(offsets.reduce((a,b) => a+b,0) * 100 / total)}%`);
          const offset = offsets[index];
          const answer = await request(`${base}/images/${index}?offset=${offset}`, {method:'PUT',headers:{'Content-Type':'application/octet-stream'},body:files[index].slice(offset,offset+CHUNK)});
          if (!Number.isInteger(answer.offset) || answer.offset <= offset || answer.offset > files[index].size) throw new Error(message('Invalid upload response.', 'Geçersiz yükleme yanıtı.'));
          offsets[index] = answer.offset;
        }
      }
      job = await request(base + '/start', {method:'POST'});
    }
    const deadline = Date.now() + 20 * 60 * 1000;
    while (true) {
      if (job.status === 'COMPLETED') return job.result;
      if (job.status === 'FAILED') {
        const error = new Error(typeof job.detail === 'string' ? job.detail : message('Image reading failed.', 'Görüntüler okunamadı.'));
        error.restartRequired = true;
        throw error;
      }
      if (Date.now() > deadline) throw new Error(message('Processing is still pending. Press Read and evaluate images again to check the same assessment.', 'İşlem henüz tamamlanmadı. Aynı değerlendirmeyi kontrol etmek için Görüntüleri oku ve değerlendir düğmesine tekrar basın.'));
      onProgress(job.status === 'ARCHIVING' ? message('Saving assessment…', 'Değerlendirme kaydediliyor…') : message('Reading images', 'Görüntüler okunuyor') + `: ${job.completed}/${job.total}`);
      await pause(2000);
      job = await request(base);
    }
  }
  window.CERAI_IOL_JOBS = {extract};
})();
