/* Presentation-only bilingual layer. Clinical decision values remain unchanged. */
(() => {
  const stored = (localStorage.getItem("cerai-language") || "en").toLowerCase();
  const locale = stored === "tr" ? "tr" : "en";
  const TR = {
    "Please wait, connecting…":"Lütfen bekleyin, bağlanıyor…",
    "Pupil below 2.00 mm: surgeon review required; multifocal is not automatically excluded.":"Pupilla 2,00 mm'nin altında: cerrah değerlendirmesi gerekir; multifokal otomatik dışlanmaz.",
    "Pupil above 4.00 mm: surgeon review required; multifocal is not automatically excluded.":"Pupilla 4,00 mm'nin üzerinde: cerrah değerlendirmesi gerekir; multifokal otomatik dışlanmaz.",
    "Pupil diameter is outside the 2–4 mm target. Visual performance may be affected. Do you still want a multifocal lens?":"Pupilla çapı 2–4 mm hedef aralığı dışında. Görsel performans etkilenebilir. Yine de multifokal lens ister misiniz?",
    "Select surgeon decision":"Cerrah kararını seçin",
    "Yes — allow multifocal selection":"Evet — multifokal seçmek istiyorum",
    "No — continue with other eligible lenses":"Hayır — diğer uygun lenslerle devam et",
    "Multifocal selection outside the 2–4 mm pupil target requires surgeon confirmation.":"2–4 mm pupilla hedefi dışında multifokal seçimi için cerrah onayı gerekir.",
    "Selected lens is excluded by the clinical assessment.":"Seçilen lens klinik değerlendirmede dışlanmıştır.",
    "Open ESCRS with all values — no installation":"ESCRS’yi tüm değerlerle aç — kurulum gerekmez",
    "Transfer biometry only to ESCRS":"ESCRS’ye yalnızca biyometri aktar",
    "Verified ESCRS cloud session opened. Review the form before calculating. Session limit: two minutes.":"Doğrulanmış ESCRS bulut oturumu açıldı. Hesaplamadan önce formu kontrol edin. Oturum sınırı: iki dakika.",
    "This transfer sends patient initials, age, biological sex, eye measurements, previous corneal surgery, selected lens, target refraction and the signed-in surgeon name to Browserless cloud browsers and the ESCRS IOL Calculator. These data remain potentially identifiable. Full patient names and source images are not sent. Continue only if authorized to disclose these data to both services.":"Bu aktarım hasta baş harflerini, yaşını, biyolojik cinsiyetini, göz ölçümlerini, önceki kornea cerrahisini, seçilen lensi, hedef refraksiyonu ve oturum açmış cerrahın adını Browserless bulut tarayıcılarına ve ESCRS IOL Calculator hizmetine gönderir. Bu verilerden kimlik belirlenmesi hâlâ mümkün olabilir. Hastanın tam adı ve kaynak görüntüler gönderilmez. Yalnız bu verileri her iki hizmetle paylaşma yetkiniz varsa devam edin.",
    "This page is out of date. Reload CER-AI and accept the current ESCRS data-transfer disclosure.":"Bu sayfa güncel değil. CER-AI sayfasını yenileyin ve güncel ESCRS veri aktarım açıklamasını onaylayın.",
    "Review the patient details and eye measurements before ESCRS transfer. The transfer was not started.":"ESCRS aktarımından önce hasta bilgilerini ve göz ölçümlerini kontrol edin. Aktarım başlatılmadı.",
    "Calculation notes":"Hesaplama notları",
    "Verified ESCRS cloud session opened. Review the form before calculating. The session duration depends on the configured Browserless plan.":"Doğrulanmış ESCRS bulut oturumu açıldı. Hesaplamadan önce formu kontrol edin. Oturum süresi yapılandırılmış Browserless planına bağlıdır.",
    "This transfer sends patient initials, age, biological sex, eye measurements, previous corneal surgery, selected lens, target refraction and the signed-in surgeon name to {provider} cloud browsers and the ESCRS IOL Calculator. These data remain potentially identifiable. Full patient names and source images are not sent. Continue only if authorized to disclose these data to both services.":"Bu aktarım hasta baş harflerini, yaşını, biyolojik cinsiyetini, göz ölçümlerini, önceki kornea cerrahisini, seçilen lensi, hedef refraksiyonu ve oturum açmış cerrahın adını {provider} bulut tarayıcılarına ve ESCRS IOL Calculator hizmetine gönderir. Bu verilerden kimlik belirlenmesi hâlâ mümkün olabilir. Hastanın tam adı ve kaynak görüntüler gönderilmez. Yalnız bu verileri her iki hizmetle paylaşma yetkiniz varsa devam edin.",
    "End session":"Oturumu bitir",
    "Tap an ESCRS field above, then enter text here":"Yukarıdaki ESCRS alanına dokunun, ardından metni buraya girin",
    "Send":"Gönder",
    "Session ended.":"Oturum sona erdi.",
    "Tap an editable ESCRS field first.":"Önce düzenlenebilir bir ESCRS alanına dokunun.",
    "Tap an editable ESCRS field and retry.":"Düzenlenebilir bir ESCRS alanına dokunup tekrar deneyin.",
    "I accept the ESCRS calculator terms for this calculation: https://iolcalculator.escrs.org/Resources/ESCRS_IOL_Calculator_Terms_of_Use.pdf":"Bu hesaplama için ESCRS hesaplayıcısının kullanım koşullarını kabul ediyorum: https://iolcalculator.escrs.org/Resources/ESCRS_IOL_Calculator_Terms_of_Use.pdf",
    "Preparing your ESCRS cloud session. Keep this page open.":"ESCRS bulut oturumunuz hazırlanıyor. Bu sayfayı açık tutun.",
    "ESCRS cloud transfer is unavailable.":"ESCRS bulut aktarımına şu anda erişilemiyor.",
    "ESCRS cloud transfer could not be verified. No completed session was opened.":"ESCRS bulut aktarımı doğrulanamadı. Tamamlanmış bir oturum açılmadı.",
    "An ESCRS cloud session is still active. Wait up to two minutes before retrying.":"Bir ESCRS bulut oturumu hâlâ açık. Tekrar denemeden önce en fazla iki dakika bekleyin.",
    "ESCRS cloud capacity is busy. Try again shortly.":"ESCRS bulut kapasitesi dolu. Kısa süre sonra tekrar deneyin.",

    "Full automatic ESCRS transfer — browser assistant":"ESCRS’ye tam otomatik aktarım — tarayıcı yardımcısı",
    "ESCRS Assistant setup and supported lenses":"ESCRS yardımcısı kurulumu ve desteklenen lensler",
    "ESCRS Assistant opened. Wait for its field verification and review the form before calculating.":"ESCRS yardımcısı açıldı. Alan doğrulamasını bekleyin ve hesaplamadan önce formu kontrol edin.",
    "Install the CER-AI ESCRS Assistant, then reload this page for full automatic transfer.":"Tam otomatik aktarım için CER-AI ESCRS yardımcısını yükleyip bu sayfayı yenileyin.",
    "Review the patient name, age and signed-in doctor before ESCRS transfer.":"ESCRS aktarımından önce hasta adını, yaşını ve oturum açan doktoru kontrol edin.",
    "Calculate both eyes before transferring a bilateral case to ESCRS.":"İki gözlü olguyu ESCRS’ye aktarmadan önce iki gözün de hesabını tamamlayın.",
    "The current patient and eye data differ from the calculation. Recalculate before transfer.":"Güncel hasta ve göz bilgileri hesaplamadan farklı. Aktarımdan önce yeniden hesaplayın.",
    "Select the intended toric lens family and recalculate before automatic transfer.":"Otomatik aktarımdan önce istenen torik lens ailesini seçip yeniden hesaplayın.",
    "This lens has no verified ESCRS model mapping. No substitute will be selected.":"Bu lensin doğrulanmış ESCRS model eşleşmesi yok. Yerine başka model seçilmeyecek.",
    "Review biological sex before transfer.":"Aktarımdan önce biyolojik cinsiyeti kontrol edin.",
    "Invalid eye assignment.":"Göz eşleştirmesi geçersiz.",
    "Sign in again to identify the surgeon for ESCRS.":"ESCRS için cerrahı belirlemek üzere yeniden oturum açın.",
    "ESCRS assistant could not open the transfer.":"ESCRS yardımcısı aktarımı açamadı.",

    "Remove image":"Sil",
    "Replace image":"Değiştir",
    "Could not update images. Please try again.":"Görüntüler güncellenemedi. Lütfen tekrar deneyin.",
    "One-page surgical report":"Tek sayfalık cerrahi rapor",
    "A4 PDF with both loaded eyes, nasal/temporal orientation and calculated toric axes. Existing clinical warnings are retained.":"Yüklenen gözleri, nazal/temporal yönleri ve hesaplanmış torik aksları içeren A4 PDF. Mevcut klinik uyarılar korunur.",
    "Open PDF":"PDF’yi aç",
    "Print":"Yazdır",
    "Share PDF":"PDF’yi paylaş",
    "Download PDF":"PDF’yi indir",
    "Retry report":"Raporu yeniden hazırla",
    "Preparing the one-page PDF…":"Tek sayfalık PDF hazırlanıyor…",
    "One-page PDF ready. Contains patient information.":"Tek sayfalık PDF hazır. Hasta bilgileri içerir.",
    "Report could not be prepared. Review the results and retry.":"Rapor hazırlanamadı. Sonuçları kontrol edip yeniden deneyin.",
    "Allow pop-ups to open the PDF, or download it.":"PDF’yi açmak için açılır pencerelere izin verin veya dosyayı indirin.",
    "PDF opened for printing. If needed, use the PDF viewer's Print command.":"PDF yazdırmak için açıldı. Gerekirse PDF görüntüleyicisinin Yazdır komutunu kullanın.",
    "File sharing is unavailable in this browser. PDF downloaded for sharing.":"Bu tarayıcı dosya paylaşımını desteklemiyor. PDF paylaşmanız için indirildi.",
    "Sharing could not be completed. You can download the PDF.":"Paylaşım tamamlanamadı. PDF’yi indirebilirsiniz.",

    "PAD2 1.00 D is marked available soon in the August 2025 brochure and is excluded. The clinic label TPADC 375 is not a verified manufacturer model alias; results use PAD identifiers.":"Üreticinin Ağustos 2025 broşüründe PAD2 (1,00 D) henüz satışa sunulacak olarak işaretlidir; hesaplamaya dahil edilmedi. Klinik listesindeki TPADC 375 kodunun eşdeğerliği doğrulanamadı; sonuçlar üreticinin PAD kodlarıyla gösterilir.",
    "CNW0T2 1.00 D is documented in the Japanese PMDA labeling; local availability must be confirmed.":"CNW0T2 (1,00 D) Japonya PMDA belgesinde doğrulanmıştır; yerel temin durumu kontrol edilmelidir.",
    "CNWET2 is not in the reviewed model/power table and is excluded. CNWET7-9 are supported by the 2026 FDA extension; local availability is unverified.":"CNWET2 için incelenen üretici tablosunda güç eşleştirmesi bulunamadığından hesaplamaya dahil edilmedi. CNWET7–9, 2026 FDA belgesinde doğrulandı; yerel temin durumu kontrol edilmelidir.",
    "One model with multiple cylinder powers; CYL labels are display descriptors, not separate manufacturer model codes.":"Aynı model farklı silindir güçlerinde üretilir. CYL ifadesi silindir gücünü gösterir; ayrı bir üretici model kodu değildir.",
    "677MT and 677MTY share the listed powers. Confirm the clear/yellow variant and cylinder when ordering.":"677MT ve 677MTY aynı silindir basamaklarını kullanır. Siparişte şeffaf/sarı varyantı ve silindir gücünü doğrulayın.",
    "Confirm regional availability and the product IFU.":"Yerel temin durumunu ve ürünün kullanım talimatını kontrol edin.",
    "Spherical power is outside the documented toric lens range.":"Sferik güç, bu torik lensin belgelenmiş güç aralığının dışında.",

    "Page configuration could not be loaded. Please reload the page.":"Sayfa yapılandırması yüklenemedi. Lütfen sayfayı yenileyin.",
    "Surgeon-classified regularity is required when the active IOLMaster K difference is greater than 1.00 D.":"Aktif IOLMaster K farkı 1,00 D üzerinde olduğunda cerrah astigmatizmayı düzenli veya düzensiz olarak belirtmelidir.",
    "CER-AI sign-in required.":"CER-AI oturumu sona erdi. Lütfen yeniden giriş yapın.",
    "Session service temporarily unavailable. Please retry.":"Oturum hizmetine geçici olarak ulaşılamıyor. Lütfen yeniden deneyin.",
    "Manage Doctors":"Doktor Yönetimi",
    "Upload images — both eyes: 5 / one eye: 3":"Görüntü yükleyin — iki göz: 5 / tek göz: 3",
    "For both eyes, upload 5 images together: OD Pentacam Cataract Pre-Op, OD Pentacam 4 Maps Refractive, OS Pentacam Cataract Pre-Op, OS Pentacam 4 Maps Refractive, and ONE IOLMaster 500 report containing both eyes. Each Pentacam image must clearly show OD or OS. For one eye only, upload its two Pentacam reports and one IOLMaster report (3 images). TCRP is not used.":"İki göz için toplam 5 görüntüyü birlikte yükleyin: sağ göz (OD) Pentacam Cataract Pre-Op ve 4 Maps Refractive, sol göz (OS) Pentacam Cataract Pre-Op ve 4 Maps Refractive, ayrıca her iki gözün ölçümlerini içeren TEK IOLMaster 500 raporu. Her Pentacam görüntüsünde OD veya OS açıkça görünmelidir. Yalnızca tek göz için o göze ait iki Pentacam raporu ve bir IOLMaster raporu yükleyin (3 görüntü). TCRP kullanılmaz.",
    "Upload 3 images for one eye or 5 for both eyes: Cataract Pre-Op and 4 Maps Refractive for each eye, plus one shared IOLMaster 500 report.":"Tek göz için 3, iki göz için 5 görüntü yükleyin: her gözün Cataract Pre-Op ve 4 Maps Refractive raporları ile ortak bir IOLMaster 500 raporu.",
    "Both-eye assessment requires separate OD and OS Pentacam reports; duplicate eyes are not accepted.":"İki göz değerlendirmesi ayrı OD ve OS Pentacam raporları gerektirir; aynı gözün tekrarlanan raporları kabul edilmez.",
    "Patient name must be readable on all source reports before combining their measurements.":"Ölçümler birleştirilmeden önce hasta adı tüm kaynak raporlarda okunabilir olmalıdır.",
    "Patient names differ across the source reports. Check the source images.":"Kaynak raporlardaki hasta adları farklı. Görüntüleri kontrol edin.",
    "Evaluate loaded eyes":"Yüklenen gözleri değerlendir",
    "Calculate both eyes":"İki gözü birlikte hesapla",
    "OD — Right eye":"OD — Sağ göz",
    "OS — Left eye":"OS — Sol göz",
    "Evaluate this eye before calculating its lens power.":"Mercek gücünü hesaplamadan önce bu gözün değerlendirmesini tamamlayın.",
    "Source identity verification failed. Check the source reports.":"Kaynak kimliği doğrulanamadı. Kaynak raporları kontrol edin.",
    "Reports extracted. Review each eye separately before evaluation.":"Raporlar okundu. Değerlendirmeden önce her gözün verilerini ayrı ayrı kontrol edin.",
    "Processing loaded eyes…":"Yüklenen gözler işleniyor…",
    "Completed. Review the separate OD and OS results below.":"Tamamlandı. Aşağıdaki ayrı OD ve OS sonuçlarını inceleyin.",
    "Review each eye's status and complete any missing fields.":"Her gözün işlem durumunu inceleyin ve eksik alanları tamamlayın.",
    "CER-AI Demo Membership Requests":"CER-AI Demo Üyelik Talepleri",
    "Not a member yet? Click here to request a free 10-patient demo membership.":"Henüz üyeliğiniz yoksa 10 hastalık ücretsiz demo üyeliği için tıklayınız.",
    "Demo membership requests":"Demo üyelik talepleri",
    "Case Archive":"Vaka Arşivi",
    "Review a doctor’s request, define the personal username and password, and activate a 10-patient demo account.":"Doktorun talebini inceleyin, kişisel kullanıcı adı ve parolasını belirleyin ve 10 hastalık demo hesabını etkinleştirin.",
    "Pending":"Bekleyenler","All requests":"Tüm talepler","Loading requests…":"Talepler yükleniyor…",
    "No pending demo requests.":"Bekleyen demo talebi yok.","No demo requests.":"Demo talebi yok.",
    "Username":"Kullanıcı adı","New password — minimum 12 characters":"Yeni parola — en az 12 karakter",
    "Approve and activate 10 credits":"Onayla ve 10 krediyi etkinleştir","Reject":"Reddet",
    "The password is hashed before storage and will not be displayed again. Give the credentials to the doctor through a separate secure channel.":"Parola kaydedilmeden önce hash'lenir ve yeniden görüntülenmez. Kullanıcı bilgilerini doktora ayrı ve güvenli bir kanaldan iletin.",
    "Approval saved; check notification status under the doctor name.":"Onay kaydedildi; bildirim durumunu doktor adına tıklayarak kontrol edin.","Not recorded":"Kaydedilmemiş","Accepted by provider; delivery unverified":"Gönderim servisi kabul etti; teslim doğrulanmadı","Sending service not connected":"Gönderim servisi bağlı değil","Sending failed":"Gönderim başarısız","Delivery unconfirmed; not resent automatically":"Teslim durumu belirsiz; otomatik tekrar gönderilmez","Attempt recorded; delivery unconfirmed":"Gönderim denemesi kaydedildi; teslim doğrulanmadı","Open approval message in WhatsApp":"Onay mesajını WhatsApp’ta aç","Open approval email":"Onay e-postasını aç","Compose links open a draft; you send it yourself.":"Bu bağlantılar taslak açar; gönderimi siz yaparsınız.","Send missing approval notifications":"Eksik onay bildirimlerini gönder",
    "Institution":"Kurum","Professional email":"Mesleki e-posta","Phone / WhatsApp":"Telefon / WhatsApp","Country":"Ülke","Specialty":"Uzmanlık alanı","Requested":"Talep tarihi",
    "patient credits used":"hasta kredisi kullanıldı","pending request(s)":"bekleyen talep",
    "Enter a username and a password of at least 12 characters.":"Bir kullanıcı adı ve en az 12 karakterlik parola girin.",
    "Demo account approved and activated with 10 patient credits.":"Demo hesabı onaylandı ve 10 hasta kredisiyle etkinleştirildi.",
    "Reject this demo request?":"Bu demo talebi reddedilsin mi?",
    "Your 10-patient demo credit has been used. To continue using CER-AI, purchase additional credit.":"10 hastalık demo krediniz doldu. CER-AI'yi kullanmaya devam etmek için ek kredi satın alınız.",
    "Demo account":"Demo hesabı","patient credits remaining":"hasta kredisi kaldı",
    "pending demo membership request(s)":"bekleyen demo üyelik talebi","Review demo requests":"Demo taleplerini incele",
    "Owner email notification":"Owner e-posta bildirimi",
    "Owner notification":"Sahibe bildirim",
    "Retry owner notification":"Sahibe bildirimi yeniden dene",
    "Notification provider accepted the alert. Phone delivery remains unverified.":"Bildirim sağlayıcısı uyarıyı kabul etti. Telefona teslim henüz doğrulanmadı.",
    "Owner notification failed":"Sahibe bildirim başarısız oldu",
    "Phone alerts for demo requests":"Demo talepleri için telefon bildirimleri",
    "Install the ntfy Android app, then open the private subscription link on your phone. Keep the topic private; notifications contain no applicant details.":"ntfy Android uygulamasını yükleyin, ardından telefonunuzda özel abonelik bağlantısını açın. Konuyu gizli tutun; bildirimlerde başvuranın bilgileri bulunmaz.",
    "Subscribe to owner alerts":"Sahip bildirimlerine abone ol",
    "Corneal Ectasia Risk Assessment Intelligence":"Kornea Ektazi Risk Değerlendirme Zekâsı",
    "ASSESSMENT":"DEĞERLENDİRMESİ","definition":"Tanım","Applicability":"Uygulanabilirlik",
    "Not applicable to selected non-LASIK procedure":"Seçilen LASIK dışı işlem için uygulanamaz",
    "Points / disposition":"Puan / karar","Displayed component; not recalculated":"Gösterilen bileşen; yeniden hesaplanmadı",
    "Information / QC only":"Yalnızca bilgi / kalite kontrolü",
    "HWTW (mm; 4 Maps Refractive lower-left labeled box)":"HWTW (mm; 4 Maps Refractive sol alt etiketli kutu)",
    "applicable":"Uygulanabilir","assessment_gate":"Değerlendirme sonucu",
    "blade_recommendations":"Bıçak önerileri","primary_hinge":"Birincil menteşe",
    "steep_meridian_axis_deg":"Dik meridyen aksı (°)","hinge_location_preference":"Tercih edilen menteşe konumu",
    "hinge_location_alternative":"İkincil menteşe konumu","alternative_hinge":"Alternatif menteşe",
    "delta_k_d":"Dik-düz K farkı (D)","ring_tzone_clearance_mm":"Halka-geçiş zonu farkı (mm)",
    "alternative_rsb_um":"Alternatif RSB (µm)","alternative_pta_percent":"Alternatif PTA (%)",
    "alternative_safety":"Alternatifin güvenliği","warnings":"Uyarılar","notes":"Notlar",
    "status_independent":"Nihai karardan bağımsız","source":"Kaynak",
    "NOT_APPLICABLE":"Uygulanamaz","ALLOWED":"UYGULANABİLİR","NOT_ALLOWED":"UYGULANAMAZ",
    "English":"English","Turkish":"Türkçe","Language":"Dil",
    "Case inputs":"Vaka girdileri","Report identification":"Rapor kimlik bilgileri",
    "Patient name":"Hasta adı",
    "Reviewer / surgeon":"Değerlendiren / cerrah","Assessment date":"Değerlendirme tarihi",
    "Pentacam/topography and treatment-card images":"Pentacam/topografi ve tedavi kartı görüntüleri",
    "Required image confirmation":"Zorunlu görüntü doğrulaması","Optional treatment card":"İsteğe bağlı tedavi kartı",
    "present":"mevcut","missing":"eksik","not provided":"sağlanmadı",
    "unreadable — enter refraction":"okunamadı — refraksiyonu girin",
    "OD Four Maps Refractive":"OD Four Maps Refractive","OS Four Maps Refractive":"OS Four Maps Refractive",
    "OD Belin/Ambrosio Display":"OD Belin/Ambrosio Ekranı","OS Belin/Ambrosio Display":"OS Belin/Ambrosio Ekranı",
    "Show 2 Exams Topometric":"Show 2 Exams Topometric",
    "Upload each missing required image before assessment.":"Değerlendirmeden önce eksik olan her zorunlu görüntüyü yükleyin.",
    "No treatment card was provided. Enter complete manifest and intended refraction values for both eyes before assessment.":"Tedavi kartı sağlanmadı. Değerlendirmeden önce her iki göz için manifest ve hedeflenen refraksiyon değerlerini eksiksiz girin.",
    "The optional treatment card was unreadable. Enter complete manifest and intended refraction values for both eyes before assessment.":"İsteğe bağlı tedavi kartı okunamadı. Değerlendirmeden önce her iki göz için manifest ve hedeflenen refraksiyon değerlerini eksiksiz girin.",
    "Patient-level clinical modifiers":"Hasta düzeyinde klinik değiştiriciler","Select all that apply":"Uygun olanların tümünü seçin",
    "Select modifiers":"Değiştiricileri seçin","Chronic eye rubbing / repetitive ocular trauma":"Kronik göz ovalama / tekrarlayan oküler travma",
    "Family history of keratoconus":"Ailede keratokonus öyküsü",
    "Pregnancy or nursing":"Gebelik veya emzirme","Collagen / connective-tissue disease":"Kollajen / bağ dokusu hastalığı",
    "Relevant medication / drug usage":"İlgili ilaç kullanımı","Dry-eye disease / unstable ocular surface":"Kuru göz hastalığı / stabil olmayan oküler yüzey",
    "Other relevant systemic disease":"Diğer ilgili sistemik hastalık","None of the listed modifiers":"Listelenen değiştiricilerin hiçbiri",
    "Not documented / unknown":"Belgelenmedi / bilinmiyor",
    "Multiple modifiers may be selected. “None” and “Not documented” are exclusive choices.":"Birden fazla değiştirici seçilebilir. “Hiçbiri” ve “Belgelenmedi” seçenekleri tek başına seçilir.",
    "Contact-lens type at imaging":"Görüntüleme sırasındaki kontakt lens tipi","Days discontinued before Pentacam":"Pentacam öncesi bırakılan gün sayısı",
    "Eye-specific plans":"Göze özgü planlar","Prior corneal refractive surgery?":"Önceki korneal refraktif cerrahi?",
    "Procedure":"Prosedür","Preoperative manifest sphere (D)":"Preoperatif manifest sfer (D)",
    "Preoperative manifest cylinder (D; + or −)":"Preoperatif manifest silindir (D; + veya −)",
    "Intended treatment sphere (D)":"Hedef tedavi sferi (D)","Intended treatment cylinder (D; + or −)":"Hedef tedavi silindiri (D; + veya −)",
    "Cylinder axis (degrees)":"Silindir aksı (derece)","Actual maximum ablation (µm)":"Gerçek maksimum ablasyon (µm)",
    "Laser platform":"Lazer platformu","Planned LASIK flap (µm)":"Planlanan LASIK flebi (µm)",
    "PRK epithelial thickness (µm)":"PRK epitel kalınlığı (µm)","Optical zone (mm)":"Optik zon (mm)","Transition zone (mm)":"Geçiş zonu (mm)",
    "Randleman topography — surgeon confirmation required":"Randleman topografisi — cerrah onayı gerekli",
    "Randleman topography assessment":"Randleman topografi değerlendirmesi",
    "Category":"Kategori","What to look for":"Bakılacak bulgu","ERSS points":"ERSS puanı",
    "Normal / symmetric":"Normal / simetrik","Normal / symmetric bow-tie":"Normal / simetrik bow-tie",
    "Asymmetric bow-tie":"Asimetrik bow-tie","Inferior steepening / SRA":"İnferior dikleşme / SRA",
    "Inferior steepening and/or SRA":"İnferior dikleşme ve/veya SRA","Abnormal / ectatic":"Anormal / ektatik","Abnormal / ectatic pattern":"Anormal / ektatik patern",
    "CER-AI evaluates only the upper-left Axial/Sagittal Curvature (Front) map on the Pentacam 4 Maps Refractive page.":"CER-AI yalnız Pentacam 4 Maps Refractive sayfasındaki sol üst Axial/Sagittal Curvature (Front) haritasını değerlendirir.",
    "Normal or symmetric map":"Normal veya simetrik harita",
    "Mild asymmetric bow-tie: >0.5 D and <1.0 D, with no SRA/SRAX":"Hafif asimetrik bow-tie: >0,5 D ve <1,0 D; SRA/SRAX yok",
    "Inferior point ≥1.0 D steeper than the matching superior point with I-S <1.4 D, or SRAX ≥20°":"İnferior nokta, aynı uzaklıktaki superior noktadan ≥1,0 D daha dik ve I-S <1,4 D; veya SRAX ≥20°",
    "Abnormal or ectatic pattern, or I-S ≥1.4 D":"Anormal veya ektatik patern; ya da I-S ≥1,4 D",
    "If CER-AI cannot read the complete map with HIGH confidence, it asks the surgeon to choose the category. It never guesses a number. Only the highest applicable single category is scored; categories are not added.":"CER-AI tam haritayı YÜKSEK güvenle okuyamazsa kategoriyi cerrahın seçmesini ister. Sayısal değer tahmin etmez. Yalnızca en yüksek uygun tek kategori puanlanır; kategoriler toplanmaz.",
    "Superior steepening alone is not automatically assigned 3 points and requires surgeon review. BAD-D and other tomography indices are not substituted for Randleman topography.":"Yalnız superior dikleşmeye otomatik olarak 3 puan verilmez; cerrah değerlendirmesi gerekir. BAD-D ve diğer tomografi indeksleri Randleman topografisinin yerine kullanılmaz.",
    "Active CER-AI Randleman / ERSS points":"Aktif CER-AI Randleman / ERSS puanları",
    "Use the category table above":"Yukarıdaki kategori tablosunu kullanın",
    "Age — active CER-AI policy":"Yaş — aktif CER-AI politikası",
    "18 / 19–20 / ≥21 years":"18 / 19–20 / ≥21 yaş",
    "Preop corneal thickness — active CER-AI policy":"Preoperatif kornea kalınlığı — aktif CER-AI politikası",
    "Hard stop / 2 / 1 / 0":"Kesin durdurma / 2 / 1 / 0",
    "Randleman/ERSS is calculated from five independent LASIK inputs. BAD-D and NICE remain separate pathways. Overall ERSS disposition: 0–2 PASS if no other concern is present, 3 CAUTION without automatic defer, ≥4 STOP-DEFER.":"Randleman/ERSS beş bağımsız LASIK girdisinden hesaplanır. BAD-D ve NICE ayrı değerlendirme yollarıdır. Genel ERSS kararı: başka bir risk yoksa 0–2 UYGUN, 3 otomatik erteleme olmadan DİKKAT, ≥4 DURDUR-ERTELE.",
    "Source:":"Kaynak:",
    "Surgeon-confirmed I-S (D)":"Cerrah tarafından doğrulanan I-S (D)",
    "Surgeon-confirmed Randleman topography category":"Cerrah tarafından doğrulanan Randleman topografi kategorisi",
    "Select only when requested":"Yalnızca istendiğinde seçin",
    "Clinical eligibility and stability":"Klinik uygunluk ve stabilite","Clinical eligibility and stability — reviewed":"Klinik uygunluk ve stabilite — değerlendirildi",
    "Refraction stable?":"Refraksiyon stabil mi?","Documented progression?":"Belgelenmiş progresyon var mı?",
    "Unexplained CDVA <20/20?":"Açıklanamayan EİDGK <20/20 mi?",
    "Yes":"Evet","No":"Hayır","YES":"EVET","NO":"HAYIR","Unknown":"Bilinmiyor","Select":"Seçin","None":"Yok","Soft":"Yumuşak","Rigid / RGP":"Sert / RGP",
    "PS3 SRAX exception — is enantiomorphism present?":"PS3 SRAX istisnası — enantiyomorfizm mevcut mu?",
    "PS3 PPI exception — are all other tomographic features normal?":"PS3 PPI istisnası — diğer tüm tomografik özellikler normal mi?",
    "4 Maps Refractive / Show 2 Exams Topometric":"4 Maps Refractive / Show 2 Exams Topometric",
    "Axial/Sagittal Curvature (Front) and Cornea Front Astig":"Axial/Sagittal Curvature (Front) ve Cornea Front Astig",
    "Pentacam tomography review":"Pentacam tomografi incelemesi",
    "PPI Average, Cornea Front Astig, and all other tomographic features":"PPI Average, Cornea Front Astig ve diğer tüm tomografik özellikler",
    "The canonical tomographic astigmatism is below 1 D. Choose YES only after confirming enantiomorphism. YES ignores this SRAX factor in PS3 only; ERSS and every other pathway remain unchanged.":"Kanonik tomografik astigmatizma 1 D'nin altındadır. Yalnız enantiyomorfizmi doğruladıktan sonra EVET'i seçin. EVET bu SRAX faktörünü yalnız PS3 içinde yok sayar; ERSS ve diğer tüm yollar değişmeden kalır.",
    "The canonical corneal astigmatism is above 2 D. Choose YES only after confirming all other tomographic features are normal. YES ignores the PPI Average factor in PS3 only; every other pathway remains unchanged.":"Kanonik korneal astigmatizma 2 D'nin üzerindedir. Yalnız diğer tüm tomografik özelliklerin normal olduğunu doğruladıktan sonra EVET'i seçin. EVET, PPI Average faktörünü yalnız PS3 içinde yok sayar; diğer tüm yollar değişmeden kalır.",
    "Assess images and run CER-AI assessment":"Görüntüleri değerlendir ve CER-AI değerlendirmesini çalıştır",
    "ERSS was originally developed for LASIK. CER-AI also applies its risk-assessment principles to PRK, using preoperative manifest refraction for the ERSS MRSE component in both procedures. Intended treatment correction is used for ablation and CER-AI treatment-range gates. Unless a different role-specific value is entered, the treatment card’s Düzeltme Miktarı auto-fills both manifest and intended correction. Every refraction field accepts positive or negative values; use the +/− buttons when a phone keyboard has no sign key. Equivalent plus-cylinder entries are safely transposed to minus-cylinder notation for calculation and disclosed in the report.":"ERSS başlangıçta LASIK için geliştirilmiştir. CER-AI, risk değerlendirme ilkelerini PRK için de uygular ve her iki işlemde ERSS MRSE bileşeni için preoperatif manifest refraksiyonu kullanır. Hedef tedavi düzeltmesi ablasyon ve CER-AI tedavi aralığı geçitlerinde kullanılır. Role özgü farklı bir değer girilmedikçe tedavi kartındaki Düzeltme Miktarı hem manifest hem hedef düzeltmeyi otomatik doldurur. Tüm refraksiyon alanları pozitif veya negatif değer kabul eder; telefon klavyesinde işaret tuşu yoksa +/− düğmelerini kullanın. Eşdeğer artı silindir girişleri hesaplama için güvenle eksi silindir gösterimine transpoze edilir ve raporda belirtilir.",
    "Download PDF":"PDF indir","Download Word":"Word indir","Open / Print one-page conclusion":"Tek sayfalık sonuç raporunu aç / yazdır","Share one-page PDF file":"Tek sayfalık PDF dosyasını paylaş","Print report":"Raporu yazdır",
    "CER-AI Clinical Decision Support":"CER-AI Klinik Karar Desteği","PREOPERATIVE ECTASIA RISK ASSESSMENT":"PREOPERATİF EKTAZİ RİSK DEĞERLENDİRMESİ",
    "Corneal refractive surgery assessment report":"Korneal refraktif cerrahi değerlendirme raporu","Eye-specific assessment":"Göze özgü değerlendirme",
    "Patient":"Hasta","Age":"Yaş","Date":"Tarih","Reviewer":"Değerlendiren","Eyes":"Gözler",
    "Not documented":"Belgelenmedi","Overall disposition":"Genel karar","PATIENT NAME NOT DOCUMENTED":"HASTA ADI BELGELENMEDİ","NOT ASSESSED":"DEĞERLENDİRİLMEDİ",
    "Automatically extracted source data":"Otomatik çıkarılan kaynak verileri","Complete machine-readable decision record":"Makine tarafından okunabilir tam karar kaydı",
    "Generated under the CER-AI Preoperative Ectasia Risk Assessment Protocol for corneal refractive surgery. CAUTION requires explicit surgeon review but does not automatically defer surgery. STOP-DEFER means surgery must not proceed unless the stated stop/defer condition is resolved. DATA INSUFFICIENT / NOT ASSESSED does not permit PASS. This clinical decision-support report does not replace independent surgeon review.":"Bu rapor, korneal refraktif cerrahi için CER-AI Preoperatif Ektazi Risk Değerlendirme Protokolü kapsamında oluşturulmuştur. DİKKAT açık cerrah değerlendirmesi gerektirir ancak cerrahiyi otomatik olarak ertelemez. DURDUR-ERTELE, belirtilen durdurma/erteleme koşulu giderilmeden cerrahiye devam edilmemesi anlamına gelir. VERİ YETERSİZ / DEĞERLENDİRİLMEDİ sonucu UYGUN kararına izin vermez. Bu klinik karar destek raporu cerrahın bağımsız değerlendirmesinin yerini almaz.",
    "Prior refractive surgery":"Önceki refraktif cerrahi","Score / category":"Puan / kategori","Randleman ERSS / category":"Randleman ERSS / kategori",
    "Final BAD-D / class":"Final BAD-D / sınıf","CER-AI-adapted NICE / class":"CER-AI uyarlanmış NICE / sınıf",
    "NICE (Navarro Index for Corneal Ectasia) combines K2, central pachymetry, posterior elevation and signed I-S. Each component contributes 1-3 points; total 4-12. CER-AI adaptation: posterior elevation <=15.5 um = 1, >15.5 to <18 um = 2, >=18 um = 3. The published table leaves 15 um unspecified. CER-AI uses only the explicitly labeled B. Ele.Th value on the Pentacam BAD Display page; no map or calculated substitute is accepted. Central pachymetry uses the plus-marked Pupil Center field (not Pachy Vertex N. or thinnest pachymetry), or a surgeon-confirmed central measurement. CER-AI disposition for LASIK and PRK: 4 = no NICE-specific escalation, 5-8 = CAUTION without automatic defer, >=9 = STOP-DEFER hard stop. NICE 4 does not establish surgical safety or override ERSS, BAD or other CER-AI stops. No individual absolute ectasia probability is inferred. Source: Navarro-Naranjo et al., Clin Ophthalmol 2024;18:881-883. DOI: 10.2147/OPTH.S464217.":"NICE (Navarro Korneal Ektazi İndeksi), K2, santral pakimetri, posterior elevasyon ve işaretli I-S değerini birleştirir. Her bileşen 1-3 puan verir; toplam 4-12'dir. CER-AI uyarlaması: posterior elevasyon ≤15,5 µm = 1, >15,5 ile <18 µm = 2, ≥18 µm = 3. Yayımlanmış tabloda 15 µm belirtilmemiştir. CER-AI yalnızca Pentacam BAD Display sayfasındaki açıkça etiketlenmiş B. Ele.Th değerini kullanır; harita veya hesaplanmış başka bir değer kabul edilmez. Santral pakimetri yalnızca artı işaretli Pupil Center alanından (Pachy Vertex N. veya en ince pakimetri değil) ya da cerrah doğrulamasından alınır. LASIK ve PRK için CER-AI kararı: 4 = NICE'a özgü artırım yok, 5-8 = otomatik erteleme olmadan DİKKAT, ≥9 = DURDUR-ERTELE kesin durdurma. NICE 4 cerrahi güvenliği kanıtlamaz ve ERSS, BAD veya diğer CER-AI durdurma kurallarını geçersiz kılmaz. Bireysel mutlak ektazi olasılığı çıkarımı yapılmaz. Kaynak: Navarro-Naranjo ve ark., Clin Ophthalmol 2024;18:881-883. DOI: 10.2147/OPTH.S464217.",
    "Stability / progression / CDVA flag":"Stabilite / progresyon / EİDGK uyarısı","Manifest entered notation":"Girilen manifest gösterim",
    "Manifest normalized (minus-cylinder)":"Normalize manifest (eksi silindir)","Intended entered notation":"Girilen hedef düzeltme gösterimi",
    "Intended normalized (minus-cylinder)":"Normalize hedef düzeltme (eksi silindir)","Correction source":"Düzeltme kaynağı",
    "Thinnest pachymetry":"En ince pakimetri","Intended MRSE":"Hedef MRSE","Preoperative Kmean":"Preoperatif Kort",
    "Manifest / intended pattern":"Manifest / hedef patern","Intended principal meridians":"Hedef ana meridyenler","Estimated final Kmean":"Tahmini final Kort",
    "Corneal effect factor":"Korneal etki katsayısı","Maximum ablation":"Maksimum ablasyon","PRK epithelium":"PRK epiteli",
    "Selected LASIK plan":"Seçilen LASIK planı","Selected plan parameters":"Seçilen plan parametreleri","Plan-selection priority":"Plan seçim önceliği","Optical / transition zone":"Optik / geçiş zonu","Tomography review":"Tomografi değerlendirmesi","Morphology category":"Morfoloji kategorisi",
    "Randleman I-S / source":"Randleman I-S / kaynak","Validated Randleman topography":"Doğrulanmış Randleman topografisi","Anterior-map read confidence":"Anterior harita okuma güveni",
    "Parameter":"Parametre","Result":"Sonuç","Value":"Değer","Clinical action:":"Klinik eylem:","Instrument/source:":"Cihaz/kaynak:",
    "NICE component audit":"NICE bileşen denetimi","NICE interpretation note":"NICE yorum notu","Reasons":"Nedenler","Hard stops":"Kesin durdurma nedenleri",
    "Missing / unresolved":"Eksik / çözümlenmemiş","Surgeon attention — hyperopic/mixed pathway":"Cerrahın dikkatine — hipermetropik/karma yol",
    "Tomography concern flags":"Tomografi endişe uyarıları","BAD display interpretation":"BAD ekran yorumu","Surgical-load evidence flags":"Cerrahi yük kanıt uyarıları",
    "Clinical modifiers":"Klinik değiştiriciler","Warnings":"Uyarılar","PRK Mitomycin-C guidance":"PRK Mitomycin-C rehberi","Extracted tomography":"Çıkarılan tomografi verileri",
    "Global clinical / source blockers":"Genel klinik / kaynak engelleri","Post-assessment ML7 microkeratome planning":"Değerlendirme sonrası ML7 mikrokeratom planlaması",
    "PENTACAM ACQUISITION QUALITY — SURGEON ATTENTION":"PENTACAM ÇEKİM KALİTESİ — CERRAHIN DİKKATİNE",
    "Planning warnings":"Planlama uyarıları","Planning notes":"Planlama notları","Assessment gate":"Değerlendirme geçidi","Vacuum ring":"Vakum halkası",
    "Vacuum pressure":"Vakum basıncı","Blade recommendation(s)":"Bıçak önerisi/önerileri","Primary hinge":"Birincil menteşe","Conditional alternative":"Koşullu alternatif","Steep meridian axis":"Dik meridyen aksı","Preferred hinge location":"Tercih edilen menteşe konumu","Secondary hinge location":"İkincil menteşe konumu","Horizontal white-to-white (HWTW)":"Horizontal white-to-white (HWTW)",
    "Alternative projected RSB / PTA":"Alternatif tahmini RSB / PTA","Alternative safety":"Alternatif güvenliği","Ring-zone clearance":"Halka-zon açıklığı","Source":"Kaynak",
    "Recommendation":"Öneri","Surgeon-review recommendation only; this module does not alter the ectasia disposition.":"Yalnızca cerrah değerlendirme önerisidir; bu modül ektazi kararını değiştirmez.",
    "PASS":"UYGUN","PASS WITH CAUTION":"DİKKATLE UYGUN","CAUTION":"DİKKAT","STOP-DEFER":"DURDUR-ERTELE",
    "DATA INSUFFICIENT":"VERİ YETERSİZ","ERROR":"HATA","ASSESSING...":"DEĞERLENDİRİLİYOR...",
    "Required information — no report has been generated":"Gerekli bilgiler — henüz rapor oluşturulmadı",
    "Pentacam examination-date conflict — surgeon review required":"Pentacam muayene tarihi çelişkisi — cerrah değerlendirmesi gerekli",
    "APPROVE_CONTINUE":"İnceledim — onayla ve devam et",
    "Source-date consistency":"Kaynak tarihi tutarlılığı",
    "4 Maps Refractive — OD and OS headers":"4 Maps Refractive — OD ve OS başlıkları",
    "Examination date":"Muayene tarihi",
    "PATIENT":"Hasta","Patient age (years)":"Hasta yaşı (yıl)",
    "Intended treatment initially follows manifest refraction. Edit intended values only when the planned treatment differs.":"Hedeflenen tedavi başlangıçta manifest refraksiyonu izler. Yalnızca planlanan tedavi farklıysa hedeflenen değerleri değiştirin.",
    "Intended treatment initially follows manifest refraction. An explicit zero cylinder also sets the intended cylinder and axis to zero; a nonzero cylinder requires an axis.":"Hedeflenen tedavi başlangıçta manifest refraksiyonu izler. Açıkça girilmiş sıfır silindir, hedef silindiri ve aksı da sıfıra ayarlar; sıfır olmayan silindir için aks gereklidir.",
    "Complete all items below, then continue. Existing inputs and image readings are retained. No calculation is required from the surgeon.":"Aşağıdaki tüm alanları tamamlayıp devam edin. Mevcut girdiler ve görüntü okumaları korunur. Cerrahın hesaplama yapması gerekmez.",
    "This cannot be completed by typing. Upload a source image that visibly shows QS: OK.":"Bu madde yazılarak tamamlanamaz. QS: OK ifadesini açıkça gösteren kaynak görüntüyü yükleyin.",
    "Explicit Pentacam QS: OK is required from the source image":"Kaynak görüntüde açıkça Pentacam QS: OK bulunması gerekir",
    "Explicitly printed Pentacam QS":"Açıkça basılı Pentacam QS",
    "Replace source images to continue":"Devam etmek için kaynak görüntüleri değiştirin",
    "A clearer/correct Pentacam or topography source image is required":"Daha net/doğru bir Pentacam veya topografi kaynak görüntüsü gereklidir",
    "This cannot be completed by typing. Replace the displayed limited/inadequate source image.":"Bu madde yazılarak tamamlanamaz. Gösterilen sınırlı/yetersiz kaynak görüntüyü değiştirin.",
    "Continue with completed information":"Tamamlanan bilgilerle devam et","Preparing...":"Hazırlanıyor...","This browser cannot share PDF files directly. Open the one-page conclusion, download the PDF, and attach that file in WhatsApp.":"Bu tarayıcı PDF dosyalarını doğrudan paylaşamıyor. Tek sayfalık sonuç raporunu açın, PDF'yi indirin ve dosyayı WhatsApp'ta ek olarak gönderin.",
    "Loading unread Pentacam/topography region...":"Pentacam/topografide okunamayan bölge yükleniyor...",
    "Pentacam/topography region the application could not read":"Uygulamanın okuyamadığı Pentacam/topografi bölgesi",
    "The unread source region could not be displayed. Enter the value from the original Pentacam/topography image.":"Okunamayan kaynak bölge gösterilemedi. Değeri özgün Pentacam/topografi görüntüsünden girin.",
    "Eye rubbing / ocular trauma":"Göz ovalama / oküler travma","Family history":"Aile öyküsü",
    "Pregnancy / nursing":"Gebelik / emzirme","Collagen-tissue disease":"Kollajen doku hastalığı","Medication / drug usage":"İlaç kullanımı",
    "Dry-eye disease":"Kuru göz hastalığı","Systemic disease":"Sistemik hastalık","Not documented":"Belgelenmedi",
    "Developed by Hüseyin Cengiz, MD. All rights reserved. Final responsibility rests with the surgeon at all times and under all circumstances.":"Hüseyin Cengiz, MD tarafından geliştirilmiştir. Tüm hakları saklıdır. Nihai sorumluluk her zaman ve her koşulda cerraha aittir.",
    "The final surgical decision and all associated responsibility and liability rest with the surgeon. This application is a clinical decision-support aid only.":"Nihai cerrahi karar ile buna bağlı tüm sorumluluk ve yükümlülük cerraha aittir. Bu uygulama yalnızca klinik karar destek aracıdır.",
    "No silent assumptions.":"Sessiz varsayım yoktur.",
    "Missing, conflicting or unreadable decision-critical data must be completed before any clinical report. OD and OS are assessed independently and are never averaged.":"Eksik, çelişkili veya okunamayan karar-kritik veriler herhangi bir klinik rapor oluşturulmadan önce tamamlanmalıdır. OD ve OS bağımsız değerlendirilir; değerlerin ortalaması alınmaz.",
    "The final surgical decision and all associated responsibility and liability rest with the surgeon.":"Nihai cerrahi karar ile buna bağlı tüm sorumluluk ve yükümlülük cerraha aittir.",
    "This application is a clinical decision-support aid only.":"Bu uygulama yalnızca klinik karar destek aracıdır.",
    "CER-AI BAD-D reference points":"CER-AI BAD-D referans puanları","CER-AI interpretation / action":"CER-AI yorumu / eylemi",
    "Variable":"Değişken","Finding":"Bulgu","Points":"Puan","Anterior topography":"Ön topografi","Normal / symmetrical":"Normal / simetrik",
    "Preop corneal thickness":"Preoperatif kornea kalınlığı","Residual stromal bed":"Rezidüel stromal yatak","MRSE":"MRSE",
    "yes":"evet","no":"hayır","unknown":"bilinmiyor","REASSURING":"RAHATLATICI","ADEQUATE":"YETERLİ","CONFIDENT":"GÜVENİLİR",
    "NORMAL_SYMMETRIC":"NORMAL_SİMETRİK","LOWER_FLAGGED_BURDEN":"DÜŞÜK UYARI YÜKÜ","MYOPIC":"MİYOPİK","HYPEROPIC":"HİPERMETROPİK","MIXED":"KARMA",
    "CER-AI Sign in":"CER-AI Girişi","Secure clinical workspace":"Güvenli klinik çalışma alanı",
    "Username":"Kullanıcı adı","Password":"Parola","Sign in":"Giriş yap","Sign-in failed.":"Giriş başarısız.",
    "Credentials are sent only to this CER-AI server over the active HTTPS session. The password is not stored in browser storage.":"Kimlik bilgileri yalnızca etkin HTTPS oturumu üzerinden bu CER-AI sunucusuna gönderilir. Parola tarayıcı depolamasında saklanmaz.",
    "IOL Calculation Surgery · Secure sign-in":"IOL Hesaplama Cerrahisi · Güvenli giriş",
    "Refractive Surgery · Secure sign-in":"Refraktif Cerrahi · Güvenli giriş",
    "CER-AI Clinical Modules":"CER-AI Klinik Modülleri","Choose a clinical module":"Bir klinik modül seçin",
    "You are signed in. Choose the surgical workflow to continue.":"Giriş yaptınız. Devam etmek için cerrahi iş akışını seçin.",
    "Refractive Surgery":"Refraktif Cerrahi","Corneal ectasia risk assessment and refractive-surgery planning.":"Korneal ektazi risk değerlendirmesi ve refraktif cerrahi planlaması.",
    "IOL Calculation Surgery":"IOL Hesaplama Cerrahisi","Pentacam, surgeon-defined parameters, and IOL category recommendation.":"Pentacam, cerrah tarafından tanımlanan parametreler ve IOL kategori önerisi.",
    "Open module →":"Modülü aç →","CER-AI provides clinical decision support only. Final treatment and lens selection remain the evaluating surgeon’s responsibility.":"CER-AI yalnızca klinik karar desteği sağlar. Nihai tedavi ve lens seçimi değerlendiren cerrahın sorumluluğundadır.",
    "CER-AI IOL Calculation Surgery":"CER-AI IOL Hesaplama Cerrahisi","Change clinical module":"Klinik modülü değiştir",
    "IOL Decision Assistant — Advanced Mode":"IOL Karar Asistanı — Gelişmiş Mod",
    "Stage 1 selects the eligible lens category. Stage 2 calculates spherical power with Cooke K6, then shows an embedded toric model and axis for surgeon testing when same-eye posterior corneal data are available. The manufacturer's toric calculator remains a separate optional comparison. The patient name entered by the surgeon is authoritative; OCR name differences across source reports do not block the case.":"Aşama 1 uygun mercek kategorisini belirler. Aşama 2 sferik mercek gücünü Cooke K6 ile hesaplar; aynı göze ait arka kornea verileri mevcutsa cerrahın test etmesi için uygulama içindeki torik modeli ve aksı gösterir. Üreticinin torik hesaplayıcısı ayrı bir isteğe bağlı karşılaştırma seçeneğidir. Cerrahın girdiği hasta adı esas alınır; kaynak raporlardaki optik karakter tanıma (OCR) kaynaklı isim farklılıkları vakayı engellemez.",
    "1. Patient and source reports":"1. Hasta ve kaynak raporları","Age":"Yaş","Biological sex":"Biyolojik cinsiyet","Select manually":"Manuel seçin","Male":"Erkek","Female":"Kadın","Selected by the surgeon; never inferred from the patient name.":"Cerrah tarafından seçilir; hasta adından asla çıkarılmaz.","Eye":"Göz","OD — Right":"OD — Sağ","OS — Left":"OS — Sol",
    "Pentacam Cataract Pre-Op":"Pentacam Katarakt Pre-Op","Optical-quality fields plus Pachy Vertex, HWTW, and ACD (Int.). TCRP is not used.":"Optik kalite alanlarına ek olarak Pachy Vertex, HWTW ve ACD (Int.) kullanılır. TCRP kullanılmaz.",
    "Upload images (3)":"Görüntüleri yükleyin (3)","Select together: Pentacam Cataract Pre-Op, Pentacam 4 Maps Refractive for the same eye, and IOLMaster 500. The application identifies each report automatically. TCRP is not used.":"Üçünü birlikte seçin: Pentacam Cataract Pre-Op, aynı göze ait Pentacam 4 Maps Refractive ve IOLMaster 500. Uygulama her raporu otomatik tanır. TCRP kullanılmaz.",
    "Select exactly three images: Pentacam Cataract Pre-Op, same-eye 4 Maps Refractive, and IOLMaster 500.":"Tam üç görüntü seçin: Pentacam Cataract Pre-Op, aynı göze ait 4 Maps Refractive ve IOLMaster 500.",
    "Source identity verification failed. Check all three reports.":"Kaynak kimliği doğrulanamadı. Üç raporu da kontrol edin.",
    "Operative eye verification failed. Check all three reports.":"Ameliyat edilecek göz doğrulanamadı. Üç raporu da kontrol edin.",
    "Patient names differ across the three reports. Check the source images.":"Üç rapordaki hasta adları farklı. Kaynak görüntüleri kontrol edin.",
    "Patient name must be readable on all three reports before combining their measurements.":"Ölçümler birleştirilmeden önce üç raporda da hasta adı okunabilmelidir.",
    "The patient name entered by the surgeon is authoritative; OCR name differences across source reports do not block the case.":"Cerrahın girdiği hasta adı esas alınır; kaynak raporlardaki OCR isim farklılıkları vakayı engellemez.",
    "Authoritative surgeon entry. OCR name differences in uploaded reports will not create a patient-mismatch error.":"Cerrahın girişi esas alınır. Yüklenen raporlardaki OCR isim farklılıkları hasta uyumsuzluğu hatası oluşturmaz.",
    "Enter the patient name before extracting source images.":"Kaynak görüntüleri işlemeden önce hasta adını girin.",
    " The surgeon-entered patient name was retained. Check the patient names printed on the source reports.":" Cerrahın girdiği hasta adı korundu. Kaynak tetkiklerde yazan hasta adlarını kontrol edin.",
    "The three images must contain one Pentacam Cataract Pre-Op, one 4 Maps Refractive, and one IOLMaster 500 report. Check the selected files.":"Üç görüntüde birer Pentacam Cataract Pre-Op, 4 Maps Refractive ve IOLMaster 500 raporu bulunmalıdır. Seçilen dosyaları kontrol edin.",
    "4 Maps Refractive Cornea Back could not be assigned to the operative eye.":"4 Maps Refractive Cornea Back, ameliyat edilecek gözle eşleştirilemedi.",
    "IOLMaster 500 report":"IOLMaster 500 raporu","Upper biometry block only: AL, K1/K2 and axes. K difference ≥1.00 D triggers toric evaluation.":"Yalnızca üst biyometri bloğu: AL, K1/K2 ve aksları. K farkı ≥1,00 D ise torik değerlendirme tetiklenir.",
    "Read from Pentacam":"Pentacam'dan oku","Operative-eye laterality is read only from the Pentacam Cataract Pre-Op report. IOLMaster is bilateral.":"Ameliyat edilecek gözün lateralitesi yalnızca Pentacam Cataract Pre-Op raporundan okunur. IOLMaster iki taraflıdır.",
    "Pentacam laterality was not read. Upload a readable Pentacam Cataract Pre-Op report showing OD or OS.":"Pentacam lateralitesi okunamadı. OD veya OS bilgisini gösteren okunabilir bir Pentacam Cataract Pre-Op raporu yükleyin.",
    "Conflicting Pentacam laterality was detected. Upload the Cataract Pre-Op report for one operative eye only.":"Çelişkili Pentacam lateralitesi saptandı. Yalnızca ameliyat edilecek tek göze ait Cataract Pre-Op raporunu yükleyin.",
    "The operative eye must come from a readable Pentacam Cataract Pre-Op report.":"Ameliyat edilecek göz bilgisi okunabilir bir Pentacam Cataract Pre-Op raporundan alınmalıdır.",
    "Image evaluation and lens recommendation":"Görüntü değerlendirmesi ve lens önerisi","Images read. Complete any missing fields, then continue to lens recommendation.":"Görüntüler okundu. Eksik alan varsa tamamlayın, ardından lens önerisine geçin.","Recalculate":"Yeniden hesapla","Read and evaluate images":"Görüntüleri oku ve değerlendir","Select regular or irregular":"Düzenli veya düzensiz seçin","Lens selection":"Lens seçimi","Incision adjustment is recommended for astigmatism management.":"Astigmatizma yönetimi için kesi düzenlemesi önerilir.","Toric evaluation: >1.00 D and regular astigmatism.":"Torik değerlendirme: >1,00 D ve düzenli astigmatizma.","Read images":"Görüntüleri oku","Evaluate uploaded images":"Yüklenen görüntüleri değerlendir","Recommend a lens":"Lens önerisi ver","Calculate":"Hesapla","Images evaluated. Continue to lens recommendation.":"Görüntüler değerlendirildi. Lens önerisi adımına geçin.","2. Lifestyle and visual goals":"2. Yaşam tarzı ve görsel hedefler",
    "Near-vision demand":"Yakın görme gereksinimi","Night driving":"Gece araç kullanımı","Halo/glare tolerance":"Halo/kamaşma toleransı",
    "Low":"Düşük","Moderate":"Orta","High":"Yüksek","Occasional":"Ara sıra","Frequent":"Sık",
    "3. Pentacam optical and complementary values":"3. Pentacam optik ve tamamlayıcı değerleri",
    "Total Corneal HOA (4 mm), µm":"Total Korneal HOA (4 mm), µm","Chord µ / kappa, mm":"Chord µ / kappa, mm","Chord α, mm":"Chord α, mm",
    "Pupil Dia (3D), mm":"Pupil Dia (3D), mm","Pachy Vertex / CCT, µm":"Pachy Vertex / CCT, µm","HWTW, mm":"HWTW, mm","ACD (Int.), mm":"ACD (Int.), mm",
    "IOLMaster ACD, mm":"IOLMaster ön kamara derinliği (ACD), mm",
    "ACD from the same-eye IOLMaster measurement. If unreadable, enter the printed value manually.":"Aynı gözün IOLMaster ölçümündeki ACD değeri kullanılır. Okunamazsa raporda yazan değeri elle girin.",
    "Internal ACD excludes corneal thickness; ACD (Ext.) is never substituted.":"İnternal ACD kornea kalınlığını içermez; ACD (Ext.) hiçbir zaman yerine kullanılmaz.",
    "4. IOLMaster 500 biometry":"4. IOLMaster 500 biyometrisi","Axial length, mm":"Aksiyel uzunluk, mm","K1, D":"K1, D","K1 axis, degrees":"K1 aksı, derece","K2, D":"K2, D","K2 axis, degrees":"K2 aksı, derece",
    "Surgeon-editable; extracted original retained.":"Cerrah tarafından düzenlenebilir; çıkarılan özgün değer korunur.",
    "K difference":"K farkı","Toric trigger: ≥1.00 D and regular astigmatism.":"Torik tetikleyici: ≥1,00 D ve düzenli astigmatizma.",
    "Lens thickness, mm (if printed)":"Lens kalınlığı, mm (basılıysa)","Never estimated. Optional for standard IOLMaster cases, including AL below 22 mm.":"Asla tahmin edilmez. AL 22 mm altında olanlar dahil, standart IOLMaster vakalarında isteğe bağlıdır.",
    "Astigmatism regularity":"Astigmatizma düzenliliği","Not required below 1.00 D":"1,00 D altında gerekli değil","Regular":"Düzenli","Irregular":"Düzensiz",
    "5. Surgeon-defined ocular findings":"5. Cerrah tarafından tanımlanan oküler bulgular","Retinal disease":"Retina hastalığı","Mild":"Hafif","Significant":"Belirgin",
    "Macular pathology":"Maküler patoloji","Absent":"Yok","Present":"Var","Glaucoma":"Glokom","Suspect":"Şüpheli","Definite":"Kesin",
    "Ocular surface":"Oküler yüzey","Resolved after treatment":"Tedavi sonrası düzeldi","Repeat measurements":"Tekrarlanan ölçümler","Not stable":"Stabil değil","Stable":"Stabil",
    "Generate IOL recommendation":"IOL önerisi oluştur","Stage 1 — category decision":"Aşama 1 — kategori kararı",
    "Stage 2 — lens and power route":"Aşama 2 — lens ve güç yolu","Clinic lens":"Klinik lensi","Clinic lens family":"Klinik lens ailesi","Select an eligible lens":"Uygun bir lens seçin",
    "Pentacam 4 Maps Refractive (toric)":"Pentacam 4 Maps Refractive (torik)","Same operative eye. Cornea Back K1/K2 and a principal axis are transcribed. Embedded toric results are unvalidated and for surgeon testing only.":"Ameliyat edilecek aynı göze ait Cornea Back K1/K2 ve bir ana meridyen aksı aktarılır. Uygulama içindeki torik sonuçlar doğrulanmamıştır; yalnızca cerrah testi içindir.",
    "PDF ready and archived. Contains patient information.":"PDF hazır ve arşivlendi. Hasta bilgileri içerir.",
    "Incision axis, degrees (steep K2)":"İnsizyon aksı, derece (dik K2)","SIA axis, degrees (steep K2)":"SIA aksı, derece (dik K2)",
    "TEST ONLY":"YALNIZCA TEST","TEST ONLY — unvalidated toric optical prototype.":"YALNIZCA TEST — doğrulanmamış torik optik prototip.",
    "Independently check the source readings, model availability, implantation axis, and residual with the manufacturer's calculator before any clinical use.":"Herhangi bir klinik kullanımdan önce kaynak ölçümlerini, model bulunabilirliğini, yerleştirme aksını ve rezidüeli üreticinin hesaplayıcısıyla bağımsız olarak doğrulayın.",
    "Model":"Model","IOL cylinder":"IOL silindiri","Marker axis":"İşaretleme aksı","Predicted residual cylinder":"Tahmini rezidüel silindir",
    "No embedded toric model or axis available.":"Uygulama içinde torik model veya aks sonucu yok.","Upload the same-eye Pentacam 4 Maps Refractive image and verify Pachy Vertex.":"Aynı göze ait Pentacam 4 Maps Refractive görüntüsünü yükleyin ve Pachy Vertex değerini doğrulayın.","Review source measurements and the selected lens family.":"Kaynak ölçümlerini ve seçili lens ailesini gözden geçirin.",
    "Stage 1 — Cooke K6 spherical power":"Aşama 1 — Cooke K6 sferik güç","Cooke K6 power":"Cooke K6 gücü","K6 best option":"K6 en uygun seçenek","Optional manufacturer toric calculator comparison":"İsteğe bağlı üretici torik hesaplayıcısı karşılaştırması",
    "ACD target":"ACD hedefi","locked":"sabit","Second modern formula verification required":"İkinci bir modern formülle doğrulama gerekli","Use ESCRS where available and verify all values manually.":"Uygunsa ESCRS kullanın ve tüm değerleri elle doğrulayın.",
    "Embedded toric model, marker axis and predicted residual are shown for surgeon testing. This hybrid optical model is not clinically validated.":"Torik model, işaretleme aksı ve tahmini rezidüel cerrah testi için gösterilir. Bu birleşik optik model klinik olarak doğrulanmamıştır.",
    "Same-eye Pentacam 4 Maps Cornea Back K1/K2, a principal axis and Pachy Vertex are required for the embedded toric calculation.":"Uygulama içindeki torik hesap için aynı göze ait Pentacam 4 Maps Cornea Back K1/K2, bir ana meridyen aksı ve Pachy Vertex gereklidir.",
    "Target refraction, D":"Hedef refraksiyon, D","Prior corneal surgery":"Önceki korneal cerrahi","Myopic LASIK/PRK":"Miyopik LASIK/PRK","Hyperopic LASIK/PRK":"Hipermetropik LASIK/PRK","RK":"RK",
    "Historical data":"Geçmiş veriler","Unavailable — no-history":"Mevcut değil — geçmiş verisiz","Available — history":"Mevcut — geçmiş verili",
    "Incision axis, degrees":"İnsizyon aksı, derece","Surgeon-specific SIA, D":"Cerraha özgü SIA, D","SIA axis, degrees (optional)":"SIA aksı, derece (isteğe bağlı)",
    "Continue to calculation":"Hesaplamaya devam et","Open Cooke K6":"Cooke K6'yı aç","Transfer values to ESCRS":"Değerleri ESCRS'ye aktar",
    "IOL power":"IOL gücü","Predicted refraction":"Tahmini refraksiyon","Selection":"Seçim","Best option":"En iyi seçenek",
    "CER-AI · Case Archive":"CER-AI · Vaka Arşivi","Loading…":"Yükleniyor…","Clinical workspace":"Klinik çalışma alanı","Sign out":"Çıkış yap",
    "Archived cases":"Arşivlenmiş vakalar","Search archived case revisions.":"Arşivlenmiş vaka revizyonlarını arayın.","Report date":"Rapor tarihi","Decision":"Karar","Reviewer":"Değerlendiren","Maximum results":"Azami sonuç sayısı",
    "Search":"Ara","Clear":"Temizle","Results":"Sonuçlar","Created by":"Oluşturan","Revision":"Revizyon","Reports":"Raporlar","Pentacam sources":"Pentacam kaynakları",
    "Run a search to list cases.":"Vakaları listelemek için arama yapın.","Owner tools":"Sahip araçları","Research export is pseudonymized and excludes direct identifiers. Audit records remain encrypted in the clinical archive.":"Araştırma dışa aktarımı takma adlıdır ve doğrudan tanımlayıcıları içermez. Denetim kayıtları klinik arşivde şifreli kalır.",
    "Research CSV · latest revisions":"Araştırma CSV · son revizyonlar","Research CSV · all revisions":"Araştırma CSV · tüm revizyonlar","Load recent audit events":"Son denetim olaylarını yükle","Archive status":"Arşiv durumu","Verify archive storage":"Arşiv depolamasını doğrula",
    "Archived Pentacam source images":"Arşivlenmiş Pentacam kaynak görüntüleri","Close":"Kapat","Archived CER-AI case":"Arşivlenmiş CER-AI vakası",
    "Modules":"Modüller","Case Archive":"Vaka Arşivi","Log out":"Çıkış yap","Return to CER-AI website":"CER-AI web sitesine dön",
    "Report attribution is bound to the authenticated CER-AI user.":"Rapor kaydı, kimliği doğrulanmış CER-AI kullanıcısına bağlıdır.",
    "CER-AI session expired. Sign in again.":"CER-AI oturumu sona erdi. Yeniden giriş yapın.","Logout failed":"Çıkış başarısız","Could not log out. Please try again.":"Çıkış yapılamadı. Lütfen yeniden deneyin.",
    "CER-AI Trial Access":"CER-AI Deneme Erişimi","Trial access":"Deneme erişimi","Doctor name":"Doktor adı","Continue":"Devam et",
    "No password is required during the trial. The name you enter is used as the doctor attribution for assessments you create.":"Deneme süresince parola gerekmez. Girdiğiniz ad, oluşturduğunuz değerlendirmelerde doktor kaydı olarak kullanılır.",
    "IOL Surgery":"IOL Cerrahisi","· IOL Surgery":"· IOL Cerrahisi","CER-AI Case Archive":"CER-AI Vaka Arşivi","Developed by Hüseyin Cengiz, MD. All rights reserved. Final responsibility rests with the surgeon at all times and under all circumstances.":"Hüseyin Cengiz, MD tarafından geliştirilmiştir. Tüm hakları saklıdır. Nihai sorumluluk her zaman ve her koşulda cerraha aittir.",
    "Required information is incomplete or invalid.":"Gerekli bilgiler eksik veya geçersiz.","Upload the Pentacam and IOLMaster 500 reports.":"Pentacam ve IOLMaster 500 raporlarını yükleyin.",
    "Transcribing source-locked fields…":"Kaynağa bağlı alanlar aktarılıyor…","Three reports extracted. Review values before evaluation.":"Üç rapor okundu. Değerlendirme öncesinde değerleri gözden geçirin.",
    "Image transcription failed.":"Görüntü aktarımı başarısız oldu.","Applying canonical IOL rules…":"Kanonik IOL kuralları uygulanıyor…","Recommendation generated. Select the lens for Stage 2.":"Öneri oluşturuldu. Aşama 2 için lensi seçin.",
    "Recommendation could not be generated.":"Öneri oluşturulamadı.","Select a clinic lens.":"Bir klinik lensi seçin.","Determining the canonical calculation route…":"Kanonik hesaplama yolu belirleniyor…","Power route could not be completed.":"Güç hesaplama yolu tamamlanamadı.",
    "IOLMaster printed an edited-value (*) marker; retained for visibility.":"IOLMaster düzenlenmiş değer (*) işareti yazdırdı; görünürlük için korundu.",
    "MULTIFOCAL":"MULTİFOKAL","MONOFOCAL":"MONOFOKAL","TORIC":"TORİK","NON_TORIC":"TORİK OLMAYAN","EDOF":"EDOF","Best option":"En iyi seçenek",
    "Session expired.":"Oturum sona erdi.","Date":"Tarih","De-identified":"Kimliksizleştirilmiş","Original":"Özgün",
    "Open case":"Vakayı aç","View source images":"Kaynak görüntüleri göster","Restricted to case creator":"Yalnızca vakayı oluşturan kullanıcı erişebilir","No matching archived cases.":"Eşleşen arşivlenmiş vaka yok.",
    "Searching…":"Aranıyor…","Secure archive is not enabled yet.":"Güvenli arşiv henüz etkin değil.","Archive search failed.":"Arşiv araması başarısız oldu.",
    "Retrieving authenticated archive file…":"Kimliği doğrulanmış arşiv dosyası alınıyor…","Archive file retrieved.":"Arşiv dosyası alındı.","Unable to retrieve archive file.":"Arşiv dosyası alınamadı.",
    "Opening authenticated archived case…":"Kimliği doğrulanmış arşiv vakası açılıyor…","Unable to reopen archived case.":"Arşivlenmiş vaka yeniden açılamadı.",
    "Loading encrypted source inventory…":"Şifrelenmiş kaynak envanteri yükleniyor…","No source images are archived for this case.":"Bu vaka için arşivlenmiş kaynak görüntüsü yok.","Unable to load archived source images.":"Arşivlenmiş kaynak görüntüleri yüklenemedi.",
    "Preview unavailable for this file type.":"Bu dosya türü için önizleme kullanılamıyor.","Open full size":"Tam boyutu aç","Download":"İndir","Download all source images (ZIP)":"Tüm kaynak görüntülerini indir (ZIP)",
    "Surgeon / reviewer":"Cerrah / değerlendiren","Archived by":"Arşivleyen","Overall decision":"Genel karar","Eye decisions":"Göz kararları","Legacy / unassigned":"Eski kayıt / atanmamış",
    "This application provides clinical decision support only. Final responsibility rests with the surgeon at all times and under all circumstances.":"Bu uygulama yalnızca klinik karar desteği sağlar. Nihai sorumluluk her zaman ve her koşulda cerraha aittir.",
    "Prior RK requires the external post-RK calculation pathway.":"Önceki RK, harici post-RK hesaplama yolunu gerektirir.",
    "Regular IOLMaster K difference is at least 1.00 D. Continue in the selected lens manufacturer's official toric calculator.":"Düzenli IOLMaster K farkı en az 1,00 D'dir. Seçilen lens üreticisinin resmi torik hesaplayıcısında devam edin.",
    "No verified official toric calculator is configured for this manufacturer; calculation is unavailable.":"Bu üretici için doğrulanmış resmi torik hesaplayıcı yapılandırılmamıştır; hesaplama kullanılamıyor.",
    "Incision axis, degrees (default: 180°; surgeon-editable)":"Kesi aksı, derece (varsayılan: 180°; cerrah değiştirebilir)",
    "SIA axis, degrees (follows incision)":"SIA aksı, derece (kesi aksını takip eder)",
    "SIA axis must coincide with the incision axis.":"SIA aksı kesi aksıyla aynı olmalıdır.",
    "Cornea Back — complete unreadable values":"Arka kornea — okunamayan değerleri tamamlayın",
    "Cornea Back K1, D":"Arka kornea K1, D",
    "Cornea Back K2, D":"Arka kornea K2, D",
    "Cornea Back K1 axis, degrees":"Arka kornea K1 aksı, derece",
    "Cornea Back K2 axis, degrees":"Arka kornea K2 aksı, derece",
    "Cornea Back Rh, mm":"Arka kornea Rh, mm",
    "Cornea Back Rv, mm":"Arka kornea Rv, mm",
    "Conflicting OD/OS labels on a single-eye Pentacam page. Check the indicated image and upload the correctly labeled page again.":"Tek göze ait Pentacam sayfasında OD/OS etiketleri çelişiyor. Belirtilen görüntüyü kontrol edip doğru göz etiketli sayfayı yeniden yükleyin.",
    "Go to ESCRS Calculator":"ESCRS Hesaplayıcısına Git",
    "I do not have this data — continue at ESCRS":"Bu veri elimde yok — ESCRS’de devam et",
    "Opens ESCRS in a new tab. Enter the available measurements there; this link does not transfer values automatically.":"ESCRS yeni sekmede açılır. Mevcut ölçümleri orada girin; bu bağlantı değerleri otomatik aktarmaz.",
    "T2 calculation completed.":"T2 hesaplaması tamamlandı.",
    "T2 spherical power":"T2 sferik güç",
    "Stage 1 — T2 spherical power":"Aşama 1 — T2 sferik güç",
    "T2 power":"T2 gücü",
    "spherical equivalent":"sferik eşdeğer",
    "Closest to target":"Hedefe en yakın",
    "Cooke K6 unavailable. Calculated locally with T2. You may transfer values to ESCRS for comparison.":"Cooke K6 kullanılamıyor. Hesaplama yerel T2 formülüyle yapıldı. Karşılaştırma için değerleri ESCRS’ye aktarabilirsiniz.",
    "Cooke K6 calculation completed.":"Cooke K6 hesaplaması tamamlandı.",
    "Cooke K6 requires measured lens thickness for this calculation. Enter LT or continue at ESCRS if unavailable.":"Cooke K6 bu hesaplama için ölçülmüş lens kalınlığı istiyor. LT değerini girin; ölçüm yoksa ESCRS ile devam edin.",
    "Cooke K6 request limit reached (HTTP 429). Wait before retrying or continue at ESCRS. This is not a missing LT error.":"Cooke K6 istek sınırına ulaşıldı (HTTP 429). Tekrar denemeden önce bekleyin veya ESCRS ile devam edin. Bu hata LT eksikliği değildir.",
    "No validated embedded model series for this lens. Use the manufacturer calculator and ESCRS for independent verification.":"Bu lens için uygulama içinde doğrulanmış model serisi bulunmuyor. Bağımsız kontrol için üretici hesaplayıcısını ve ESCRS’yi kullanın.",
    "No verified cylinder model series exists for this lens family in CER-AI. Use the manufacturer calculator and ESCRS.":"Bu lens ailesi için CER-AI içinde doğrulanmış torik silindir model serisi bulunmuyor. Üretici hesaplayıcısını ve ESCRS’yi kullanın.",
    "Calculate loaded eyes":"Yüklenen gözleri hesapla",
    "Lens thickness, mm":"Lens kalınlığı, mm",
    "Cooke K6 requested measured lens thickness. If unavailable, use Transfer values to ESCRS below.":"Cooke K6 ölçülmüş lens kalınlığı istedi. Ölçüm yoksa aşağıdaki Değerleri ESCRS’ye aktar düğmesini kullanın.",
    "Cooke K6 service timed out.":"Cooke K6 hizmeti zaman aşımına uğradı.",
    "Cooke K6 service could not be reached.":"Cooke K6 hizmetine ulaşılamadı.",
    "Cooke K6 service returned an invalid response.":"Cooke K6 hizmeti geçersiz yanıt döndürdü.",
    "Cooke K6 returned no eye result.":"Cooke K6 göz sonucu döndürmedi.",
    "Cooke K6 returned no power predictions.":"Cooke K6 güç tahmini döndürmedi.",
    "Cooke K6 returned invalid power predictions.":"Cooke K6 geçersiz güç tahminleri döndürdü.",
    "Cooke K6 calculation completed. The ESCRS calculator is provided as the external comparison route.":"Cooke K6 hesaplaması tamamlandı. ESCRS hesaplayıcısı harici karşılaştırma yolu olarak sunulmuştur.",
    "ACD target":"Ön kamara derinliğine göre hedef","locked":"kilitli",
    "Second modern formula verification required":"İkinci modern formülle doğrulama gerekli",
    "Use ESCRS where available and verify all values manually.":"Uygun olduğunda ESCRS kullanın ve tüm değerleri elle doğrulayın.",
    "Creating a secure, de-identified ESCRS transfer…":"Güvenli, kimliksizleştirilmiş ESCRS aktarımı oluşturuluyor…",
    "Biometry transferred to ESCRS. Verify every imported value before calculation.":"Biyometri ESCRS'ye aktarıldı. Hesaplamadan önce içe aktarılan her değeri doğrulayın.",
    "ESCRS transfer link opened. Verify imported measurements. Select the IOL and check target refraction, toric mode, SIA and incision axis in ESCRS; these settings are not transferred.":"ESCRS aktarım bağlantısı açıldı. İçe aktarılan ölçümleri doğrulayın. ESCRS’de lensi seçin; hedef refraksiyon, torik modu, SIA ve kesi aksını kontrol edin. Bu tercihler aktarılmaz.",
    "Calculate both eyes before transferring a bilateral case to ESCRS.":"İki gözlü olguyu ESCRS’ye aktarmadan önce her iki gözün hesaplamasını tamamlayın.",
    "ESCRS transfer requires whole-degree K axes. Review the source axes.":"ESCRS aktarımı tam derece K aksları gerektirir. Kaynak akslarını kontrol edin.",
    "ESCRS transfer requires K axes exactly 90 degrees apart. Review the source axes.":"ESCRS aktarımında K aksları arasında tam 90 derece olmalıdır. Kaynak akslarını kontrol edin.",
    "ESCRS transfer requires CCT in whole micrometers. Review the source value.":"ESCRS aktarımı tam mikrometre CCT değeri gerektirir. Kaynak değeri kontrol edin.",
    "ESCRS transfer requires K1 to be no greater than K2.":"ESCRS aktarımında K1, K2’den büyük olamaz.",
    "ESCRS transfer could not be completed.":"ESCRS aktarımı tamamlanamadı.",
    "Selected lens is not in the clinic-approved catalog.":"Seçilen lens, klinik tarafından onaylanmış katalogda bulunmuyor.",
    "Astigmatism regularity is required for toric routing.":"Torik yönlendirme için astigmatizma düzenliliği gereklidir.","Incision axis and surgeon-specific SIA are required for toric routing.":"Torik yönlendirme için insizyon aksı ve cerraha özgü SIA gereklidir.",
    "Research export is not enabled.":"Araştırma dışa aktarımı etkin değil.","Preparing research CSV…":"Araştırma CSV'si hazırlanıyor…","Research CSV generated.":"Araştırma CSV'si oluşturuldu.","Research export failed.":"Araştırma dışa aktarımı başarısız oldu.",
    "Audit review is not enabled.":"Denetim incelemesi etkin değil.","Loading audit records…":"Denetim kayıtları yükleniyor…","No audit records.":"Denetim kaydı yok.","Audit search failed.":"Denetim araması başarısız oldu.",
    "Loading protected archive status…":"Korunan arşiv durumu yükleniyor…","Protected archive status loaded.":"Korunan arşiv durumu yüklendi.","Unable to load archive status.":"Arşiv durumu yüklenemedi.",
    "Run the encrypted non-patient archive storage verification now?":"Şifrelenmiş, hasta verisi içermeyen arşiv depolama doğrulaması şimdi çalıştırılsın mı?","Writing and reading the encrypted non-patient canary…":"Şifrelenmiş, hasta verisi içermeyen doğrulama kaydı yazılıyor ve okunuyor…",
    "Archive storage verification passed. No patient data was used.":"Arşiv depolama doğrulaması başarılı. Hasta verisi kullanılmadı.","Archive storage verification failed.":"Arşiv depolama doğrulaması başarısız oldu.",
    "OWNER scope: cases created under your account retain original identity, reports, and source images; other doctors’ cases remain masked and de-identified.":"SAHİP kapsamı: hesabınız altında oluşturulan vakalar özgün kimlik, rapor ve kaynak görüntülerini korur; diğer doktorların vakaları maskeli ve kimliksizleştirilmiş kalır.",
    "DOCTOR scope: only cases created under your account, with original identity and source material.":"DOKTOR kapsamı: yalnızca hesabınız altında oluşturulan, özgün kimlik ve kaynak materyali içeren vakalar.",
    "Search your own identifiable cases":"Kimliği görülebilen kendi vakalarınızda arayın","Secure archive is configured off. No patient data will be listed until archive activation is verified.":"Güvenli arşiv kapalı olarak yapılandırılmıştır. Arşiv etkinleştirmesi doğrulanana kadar hasta verileri listelenmez.","Unable to load archive workspace.":"Arşiv çalışma alanı yüklenemedi.",
    "CER-AI — Corneal Ectasia Risk Assessment Intelligence v2.0":"CER-AI — Kornea Ektazi Risk Değerlendirme Zekâsı v2.0","Corneal Ectasia Risk":"Kornea Ektazi Riski","Open / Download PDF":"PDF'yi aç / indir","Software v2.0":"Yazılım v2.0",
    "Make manifest sphere positive":"Manifest sferi pozitif yap","Make manifest sphere negative":"Manifest sferi negatif yap","Make manifest cylinder positive":"Manifest silindiri pozitif yap","Make manifest cylinder negative":"Manifest silindiri negatif yap",
    "Make intended sphere positive":"Hedef sferi pozitif yap","Make intended sphere negative":"Hedef sferi negatif yap","Make intended cylinder positive":"Hedef silindiri pozitif yap","Make intended cylinder negative":"Hedef silindiri negatif yap","Make I-S positive":"I-S değerini pozitif yap","Make I-S negative":"I-S değerini negatif yap",
    "Decision trigger":"Karar tetikleyicisi","Total":"Toplam","Topography category":"Topografi kategorisi","Disposition":"Karar","Classification":"Sınıflandırma","Moderate / High":"Orta / Yüksek","Procedure disposition":"İşleme göre karar","Parameter":"Parametre","Canonical result":"Kanonik sonuç","Planning item":"Planlama maddesi","Canonical decision driver":"Kanonik karar nedeni","Field":"Alan","Original":"Özgün","Surgeon-entered value":"Cerrah tarafından girilen değer","Provenance":"Köken",
    "Please complete the required field highlighted by the browser.":"Lütfen tarayıcının işaretlediği zorunlu alanı tamamlayın.","Select or share at least one image.":"En az bir görüntü seçin veya paylaşın.","Assessing images... Please wait":"Görüntüler değerlendiriliyor... Lütfen bekleyin","Assessing images... Please wait.":"Görüntüler değerlendiriliyor... Lütfen bekleyin.",
    "The mobile connection was interrupted. CER-AI is restoring this assessment automatically; please wait.":"Mobil bağlantı kesildi. CER-AI bu değerlendirmeyi otomatik olarak geri yüklüyor; lütfen bekleyin.","A definitive hard stop is present. Complete the requested values for the full report.":"Kesin bir durdurma nedeni mevcut. Tam rapor için istenen değerleri tamamlayın.","CONTACT-LENS WASHOUT REQUIRED":"KONTAKT LENS BIRAKMA SÜRESİ GEREKLİ","REQUIRED INFORMATION":"GEREKLİ BİLGİLER",
    "Server did not return a complete report-ready assessment.":"Sunucu rapora hazır, eksiksiz bir değerlendirme döndürmedi.","Patient age could not be read from the Pentacam image. Enter the age, then run the assessment again.":"Hasta yaşı Pentacam görüntüsünden okunamadı. Yaşı girip değerlendirmeyi yeniden çalıştırın.","The mobile connection could not be restored automatically. The five images remain available.":"Mobil bağlantı otomatik olarak geri yüklenemedi. Beş görüntü kullanılabilir durumda tutuluyor.","Add/replace source image to continue":"Devam etmek için kaynak görüntü ekleyin/değiştirin","Review the required action":"Gerekli işlemi gözden geçirin",
    "Shared images were not loaded.":"Paylaşılan görüntüler yüklenemedi.","Open the image picker and select the Pentacam images.":"Görüntü seçiciyi açın ve Pentacam görüntülerini seçin.",
    "Select exactly three images: Pentacam Cataract Pre-Op, same-eye 4 Maps Refractive, and IOLMaster 500.":"Tam olarak üç görüntü seçin: Pentacam Cataract Pre-Op, aynı göze ait 4 Maps Refractive ve IOLMaster 500.","Source identity verification failed. Check all three reports.":"Kaynak kimliği doğrulanamadı. Üç raporu da kontrol edin.",
    "The three images must contain one Pentacam Cataract Pre-Op, one 4 Maps Refractive, and one IOLMaster 500 report. Check the selected files.":"Üç görüntü; bir Pentacam Cataract Pre-Op, bir 4 Maps Refractive ve bir IOLMaster 500 raporu içermelidir. Seçilen dosyaları kontrol edin.","Pentacam laterality was not read. Upload a readable Pentacam Cataract Pre-Op report showing OD or OS.":"Pentacam göz tarafı okunamadı. OD veya OS bilgisini gösteren okunabilir bir Pentacam Cataract Pre-Op raporu yükleyin.",
    "Conflicting Pentacam laterality was detected. Upload the Cataract Pre-Op report for one operative eye only.":"Çelişkili Pentacam göz tarafı saptandı. Yalnız ameliyat edilecek tek göze ait Cataract Pre-Op raporunu yükleyin.","Operative eye verification failed. Check all three reports.":"Ameliyat edilecek göz doğrulanamadı. Üç raporu da kontrol edin.","4 Maps Refractive Cornea Back could not be assigned to the operative eye.":"4 Maps Refractive Cornea Back verisi ameliyat edilecek gözle eşleştirilemedi.","The operative eye must come from a readable Pentacam Cataract Pre-Op report.":"Ameliyat edilecek göz, okunabilir Pentacam Cataract Pre-Op raporundan belirlenmelidir.",
    "Exactly three IOL source images are required.":"Tam olarak üç IOL kaynak görüntüsü gereklidir.","Upload exactly one Cataract Pre-Op, one same-eye 4 Maps Refractive, and one IOLMaster 500 report.":"Tam olarak bir Cataract Pre-Op, aynı göze ait bir 4 Maps Refractive ve bir IOLMaster 500 raporu yükleyin.","The operative eye must be readable on the Pentacam Cataract Pre-Op report.":"Ameliyat edilecek göz Pentacam Cataract Pre-Op raporunda okunabilir olmalıdır.","The 4 Maps Refractive report must show the same operative eye.":"4 Maps Refractive raporu aynı ameliyat gözünü göstermelidir.","The IOLMaster report must include biometry for the operative eye.":"IOLMaster raporu ameliyat edilecek gözün biyometrisini içermelidir.",
    "No verified cylinder model series exists for the selected lens family.":"Seçilen lens ailesi için doğrulanmış silindir model serisi yoktur.","Cooke K6 did not identify one finite best spherical-equivalent power and predicted refraction.":"Cooke K6 tek bir sonlu en uygun sferik eşdeğer güç ve tahmini refraksiyon belirleyemedi.","Cooke K6 spherical power":"Cooke K6 sferik güç","ASCRS post-refractive / Barrett True-K":"ASCRS post-refraktif / Barrett True-K","ASCRS post-RK calculator":"ASCRS post-RK hesaplayıcısı",
    "CALCULATION UNAVAILABLE":"HESAPLAMA KULLANILAMIYOR","EXTERNAL REQUIRED":"HARİCİ HESAPLAMA GEREKLİ","COMPLETED":"TAMAMLANDI","TEST ONLY":"YALNIZCA TEST","INPUTS INCOMPLETE":"GİRDİLER EKSİK","UNSUPPORTED":"DESTEKLENMİYOR",
    "Significant retinal disease: multifocal IOL excluded.":"Belirgin retina hastalığı: multifokal IOL uygun değildir.","Mild retinal disease requires surgeon review.":"Hafif retina hastalığı cerrah değerlendirmesi gerektirir.","Macular pathology: multifocal IOL excluded.":"Maküler patoloji: multifokal IOL uygun değildir.","Definite glaucoma: multifocal IOL excluded.":"Kesin glokom: multifokal IOL uygun değildir.","Glaucoma suspect: multifocal IOL requires caution.":"Glokom şüphesi: multifokal IOL için dikkat gerekir.",
    "Moderate active ocular-surface disease: multifocal IOL excluded.":"Orta derecede aktif oküler yüzey hastalığı: multifokal IOL uygun değildir.","Significant active ocular-surface disease: multifocal IOL excluded.":"Belirgin aktif oküler yüzey hastalığı: multifokal IOL uygun değildir.","Mild ocular-surface disease requires optimization and review.":"Hafif oküler yüzey hastalığı optimizasyon ve değerlendirme gerektirir.","High total corneal HOA: multifocal IOL excluded.":"Yüksek total korneal HOA: multifokal IOL uygun değildir.","Moderate total corneal HOA requires caution.":"Orta düzey total korneal HOA dikkat gerektirir.",
    "High angle kappa: multifocal IOL excluded.":"Yüksek kappa açısı: multifokal IOL uygun değildir.","High angle alpha: multifocal IOL excluded.":"Yüksek alfa açısı: multifokal IOL uygun değildir.","Pupil diameter below 2.00 mm: multifocal IOL excluded.":"Pupil çapı 2,00 mm'nin altında: multifokal IOL uygun değildir.","Pupil diameter above 4.00 mm: multifocal IOL excluded.":"Pupil çapı 4,00 mm'nin üzerinde: multifokal IOL uygun değildir.","Irregular astigmatism: multifocal IOL excluded.":"Düzensiz astigmatizma: multifokal IOL uygun değildir.",
    "De-identified archived assessment reopened. Patient identity and source filenames are masked; no clinical score was recalculated.":"Kimliksizleştirilmiş arşiv değerlendirmesi yeniden açıldı. Hasta kimliği ve kaynak dosya adları maskelidir; klinik skor yeniden hesaplanmadı.","Archived canonical assessment reopened. Values are displayed from the saved snapshot; no clinical score was recalculated.":"Arşivlenmiş kanonik değerlendirme yeniden açıldı. Değerler kaydedilmiş anlık görüntüden gösteriliyor; klinik skor yeniden hesaplanmadı.",
    "Not yet verified":"Henüz doğrulanmadı","Not available":"Mevcut değil","Unavailable":"Kullanılamıyor","Current production":"Güncel üretim","Archive":"Arşiv","Software":"Yazılım","Deployment":"Dağıtım","Canary":"Doğrulama kaydı","Verified":"Doğrulandı","Checksum":"Sağlama toplamı",
    "Open Original PDF EN":"Özgün İngilizce PDF'yi aç","Open Original PDF TR":"Özgün Türkçe PDF'yi aç","Download Original DOCX EN":"Özgün İngilizce DOCX'i indir","Download Original DOCX TR":"Özgün Türkçe DOCX'i indir","Open De-identified PDF EN":"Kimliksizleştirilmiş İngilizce PDF'yi aç","Open De-identified PDF TR":"Kimliksizleştirilmiş Türkçe PDF'yi aç","Download De-identified DOCX EN":"Kimliksizleştirilmiş İngilizce DOCX'i indir","Download De-identified DOCX TR":"Kimliksizleştirilmiş Türkçe DOCX'i indir",
    "Regenerate PDF EN":"İngilizce PDF'yi yeniden oluştur","Regenerate PDF TR":"Türkçe PDF'yi yeniden oluştur","Regenerate DOCX EN":"İngilizce DOCX'i yeniden oluştur","Regenerate DOCX TR":"Türkçe DOCX'i yeniden oluştur",
    "PATIENT IDENTITY NOT VERIFIED — SURGEON CONFIRMATION REQUIRED":"HASTA KİMLİĞİ DOĞRULANMADI — CERRAH DOĞRULAMASI GEREKLİ",
    "Actual maximum ablation must be zero or greater.":"Gerçek maksimum ablasyon sıfır veya daha büyük olmalıdır.",
    "Select patient-level modifiers, None, or Not documented.":"Hasta düzeyindeki değiştiricileri, Yok veya Belgelenmedi seçeneğini belirleyin.",
    "A maximum of six images can be shared for one CER-AI assessment.":"Bir CER-AI değerlendirmesi için en fazla altı görüntü paylaşılabilir.",
    "One shared image exceeds the 20 MB limit.":"Paylaşılan görüntülerden biri 20 MB sınırını aşıyor.",
    "The shared images exceed the 80 MB total limit.":"Paylaşılan görüntüler toplam 80 MB sınırını aşıyor.",
    "No readable image was received. Please share the photos again.":"Okunabilir görüntü alınmadı. Lütfen fotoğrafları yeniden paylaşın.",
    "No readable image was received. Share the Pentacam images again.":"Okunabilir görüntü alınmadı. Pentacam görüntülerini yeniden paylaşın.",
    "The shared images could not be found. Please share them again.":"Paylaşılan görüntüler bulunamadı. Lütfen yeniden paylaşın.",
    "Shared-image storage is unavailable.":"Paylaşılan görüntü depolama alanı kullanılamıyor.",
    "Canonical Pentacam values and provenance":"Kanonik Pentacam değerleri ve kökeni",
    "Canonical field":"Kanonik alan","Decision basis":"Karar dayanağı","Exact finding":"Kesin bulgu",
    "Procedural safety":"Prosedür güvenliği","Procedure planning":"Prosedür planlaması","Surgeon-completed values":"Cerrah tarafından tamamlanan değerler",
    "ML7 Preferred hinge location":"ML7 tercih edilen menteşe konumu","ML7 Vacuum pressure":"ML7 vakum basıncı","ML7 Vacuum ring":"ML7 vakum halkası","MMC guidance":"MMC yönlendirmesi",
  };
  const CLINICAL = {
    "Temporal hinge (default)":"Temporal menteşe (varsayılan)",
    "Plano/standard blade unless another rule or clinical factor applies":"Başka bir kural veya klinik faktör yoksa plano/standart bıçak",
    "Recommendation only; surgeon must verify anatomy, device setup, and the active ML7 manual before use.":"Yalnızca öneridir; cerrah kullanımdan önce anatomiyi, cihaz ayarlarını ve güncel ML7 kılavuzunu doğrulamalıdır.",
    "If the selected ring leaks, does not hold vacuum, or is too large, the active ML7 reference directs selection of one smaller ring.":"Seçilen halka kaçırıyor, vakumu tutmuyor veya fazla büyükse güncel ML7 referansı bir küçük halka seçilmesini belirtir.",
    "Hyperopic W2W xx.60+ rounded upward under the active ML7 reference.":"Hipermetropik W2W xx.60+ güncel ML7 referansına göre yukarı yuvarlandı.",
    "Steepest K is outside the supplied nomogram range; no ring is inferred.":"En dik K, sağlanan nomogram aralığının dışındadır; halka seçimi yapılmamıştır.",
    "Canonical K1/K2 unavailable: confirm the missing Cornea Front values; no ML7 vacuum-ring recommendation was generated.":"Kanonik K1/K2 mevcut değil: eksik Cornea Front değerlerini doğrulayın; ML7 vakum halkası önerisi oluşturulmadı.",
    "Verified horizontal white-to-white (HWTW) unavailable: enter HWTW from the 4 Maps Refractive lower-left labeled box; no vacuum-ring recommendation was generated.":"Doğrulanmış yatay beyazdan beyaza mesafe (HWTW) mevcut değil: HWTW değerini 4 Maps Refractive ekranının sol alt etiketli kutusundan girin; vakum halkası önerisi oluşturulmadı.",
    "Active ML7 reference advises 580-590 mmHg when pachymetry is <530 µm, with corneal K taking priority.":"Güncel ML7 referansı, pakimetri <530 µm olduğunda korneal K öncelikli olmak üzere 580-590 mmHg önerir.",
    "Pachymetry <=500 µm: active ML7 reference recommends -10 blade when seeking a thinner flap/more residual stroma.":"Pakimetri <=500 µm: güncel ML7 referansı daha ince flep / daha fazla rezidüel stroma hedefleniyorsa -10 bıçak önerir.",
    "K <=39 D: active ML7 reference recommends +10 or +20 blade.":"K <=39 D: güncel ML7 referansı +10 veya +20 bıçak önerir.",
    "Ablation/transition zone is not 0.4-0.5 mm smaller than the selected ring (active ML7 reference optimum).":"Ablasyon / geçiş zonu seçilen halkadan 0,4-0,5 mm daha küçük değildir (güncel ML7 referansının ideal farkı).",
    "MED-LOGICS ML7 Rev. 22 active Turkish reference + CER-AI hinge amendment":"MED-LOGICS ML7 Rev. 22 güncel Türkçe referans + CER-AI menteşe değişikliği",
    "STOP-DEFER; do not proceed with elective corneal refractive surgery.":"DURDUR-ERTELE; elektif korneal refraktif cerrahiye devam etmeyin.",
    "STOP/DEFER; repeat relevant ectasia screening and reassess after at least 6 months.":"DURDURUN/ERTELEYİN; ilgili ektazi taramasını tekrarlayın ve en az 6 ay sonra yeniden değerlendirin.",
    "CER-AI assessment PASS; this is not a guarantee of zero ectasia risk.":"CER-AI değerlendirmesi UYGUN; bu sonuç ektazi riskinin sıfır olduğunu garanti etmez.",
    "Decision-critical or required clinical data are missing/unresolved; PASS is prohibited.":"Karar için kritik veya zorunlu klinik veriler eksik/çözümlenmemiştir; UYGUN kararı verilemez.",
    "No surgical clearance; resolve the stated review/data requirement.":"Cerrahi onay yoktur; belirtilen değerlendirme/veri gereksinimini giderin.",
    "Overall result reflects the least favorable eye. Each eye remains independently scored; values are never averaged.":"Genel sonuç daha olumsuz olan gözü yansıtır. Her göz bağımsız puanlanır; değerlerin ortalaması alınmaz.",
    "CER-AI operational hard stop: thinnest preoperative cornea <480 µm.":"CER-AI kesin durdurma kuralı: preoperatif en ince kornea <480 µm.",
    "CER-AI operational LASIK RSB hard stop: RSB <300 µm.":"CER-AI LASIK kesin durdurma kuralı: RSB <300 µm.",
    "CER-AI operational PRK RST hard stop: RST <310 µm.":"CER-AI PRK kesin durdurma kuralı: RST <310 µm.",
    "Mitomycin-C use is REQUIRED for hyperopic PRK.":"Hipermetropik PRK'de Mitomycin-C kullanımı ZORUNLUDUR.",
    "Mitomycin-C use is REQUIRED for myopic PRK with intended MRSE magnitude 4.00 D or greater (for example, -4.00 D or -5.00 D).":"Hedef MRSE miyopi büyüklüğü 4,00 D veya daha fazla olan PRK'de Mitomycin-C kullanımı ZORUNLUDUR (örneğin -4,00 D veya -5,00 D).",
    "Mitomycin-C use is RECOMMENDED for myopic PRK with intended MRSE magnitude below 4.00 D (for example, -3.99 D).":"Hedef MRSE miyopi büyüklüğü 4,00 D'nin altında olan PRK'de Mitomycin-C kullanımı ÖNERİLİR (örneğin -3,99 D).",
    "The myopic and hyperopic PRK Mitomycin-C rules do not classify mixed astigmatism; surgeon review is required.":"Miyopik ve hipermetropik PRK Mitomycin-C kuralları karma astigmatizmayı sınıflandırmaz; cerrah değerlendirmesi gerekir.",
    "Refractive instability or documented progression: defer and re-evaluate after >=6 months.":"Refraktif instabilite veya belgelenmiş progresyon: erteleyin ve ≥6 ay sonra yeniden değerlendirin.",
    "Unexplained preoperative CDVA <20/20 requires investigation.":"Açıklanamayan preoperatif EİDGK <20/20 araştırılmalıdır.",
    "Prior PRK/LASIK/SMILE or other corneal refractive surgery requires a separate pathway.":"Önceki PRK/LASIK/SMILE veya başka korneal refraktif cerrahi ayrı bir değerlendirme yolu gerektirir.",
    "Pregnancy or nursing reported; separate refractive-surgery eligibility review required.":"Gebelik veya emzirme bildirildi; ayrı refraktif cerrahi uygunluk değerlendirmesi gerekir.",
    "Collagen/connective-tissue disease reported; separate clinical eligibility review required.":"Kollajen/bağ dokusu hastalığı bildirildi; ayrı klinik uygunluk değerlendirmesi gerekir.",
    "Relevant medication/drug usage reported; medication-specific clinical review required.":"İlgili ilaç kullanımı bildirildi; ilaca özgü klinik değerlendirme gerekir.",
    "Dry-eye disease reported; ocular-surface optimization and eligibility review required.":"Kuru göz hastalığı bildirildi; oküler yüzey optimizasyonu ve uygunluk değerlendirmesi gerekir.",
    "Systemic disease reported; disease-specific refractive-surgery eligibility review required.":"Sistemik hastalık bildirildi; hastalığa özgü refraktif cerrahi uygunluk değerlendirmesi gerekir.",
    "Override gate negative; procedure-specific score and required tomography/clinical review are reassuring.":"Öncelikli dışlama ölçütü yoktur; prosedüre özgü puan ile zorunlu tomografi/klinik değerlendirme rahatlatıcıdır.",
    "Inter-eye tomography concern: NO MAJOR INTER-EYE DISCORDANCE DETECTED. No major categorical inter-eye tomography discordance detected. This is not a clearance criterion and does not change the CER-AI score or final disposition.":"Gözler arası tomografi değerlendirmesi: BELİRGİN GÖZLER ARASI UYUMSUZLUK SAPTANMADI. Belirgin kategorik gözler arası tomografi uyumsuzluğu saptanmadı. Bu bir cerrahi onay ölçütü değildir ve CER-AI puanını veya nihai kararı değiştirmez.",
    "Plan A — flap 100 µm; optical zone 6.5 mm; transition zone 9.0 mm":"Plan A — flep 100 µm; optik zon 6,5 mm; geçiş zonu 9,0 mm",
    "Plan B — flap 100 µm; optical zone 6.0 mm; transition zone 8.5 mm":"Plan B — flep 100 µm; optik zon 6,0 mm; geçiş zonu 8,5 mm",
    "Plan C — flap 90 µm; optical zone 6.0 mm; transition zone 8.5 mm":"Plan C — flep 90 µm; optik zon 6,0 mm; geçiş zonu 8,5 mm",
    "Select the first safe plan only: Plan A → Plan B → Plan C":"Yalnızca ilk güvenli planı seçin: Plan A → Plan B → Plan C",
    "NICE interpretation: no NICE escalation. NICE is an independent screening pathway and is not added to the CER-AI numeric score.":"NICE yorumu: NICE artırımı yoktur. NICE bağımsız bir tarama yoludur ve CER-AI sayısal puanına eklenmez.",
    "CER-AI SCORE — SOURCE & BREAKDOWN: PRK-EWSS v1.0 provisional evidence-weighted triage score (not validated); CER-AI-modified age bands. morphology: +0 (morphology NORMAL_SYMMETRIC); pachymetry: +0 (thinnest pachymetry 560 µm); age: +0 (age 35 years). TOTAL: 0 (LOWER_FLAGGED_BURDEN). Hard stops are independent of this numeric score and are not counted as score points.":"CER-AI PUANI — KAYNAK VE DÖKÜM: PRK-EWSS v1.0 geçici kanıt ağırlıklı triyaj puanı (doğrulanmamıştır); CER-AI'ye uyarlanmış yaş aralıkları. morfoloji: +0 (NORMAL_SİMETRİK); pakimetri: +0 (en ince pakimetri 560 µm); yaş: +0 (35 yaş). TOPLAM: 0 (DÜŞÜK UYARI YÜKÜ). Kesin durdurma kuralları bu sayısal puandan bağımsızdır ve puana eklenmez.",
    "ECTASIA RISK INTERPRETATION: In the cited post-PRK ectasia series with complete ERSS data, 77% of ectasia eyes had cumulative ERSS >=4, 9% had score 3, and 14% had score <=2. The surgical cohort incidence reported in that study was 9/31,045 eyes (0.029%). ABSOLUTE PROBABILITY: Not established for an individual PRK score. LIMITATION: These are distributions among ectasia cases and an overall cohort incidence, not score-specific patient probabilities. The LASIK ERSS is not validated as an absolute-risk calculator for PRK; the 0.029% cohort incidence must not be assigned to an individual score. SOURCE: Risk Assessment for Corneal Ectasia following Photorefractive Keratectomy.":"EKTAZİ RİSK YORUMU: Tam ERSS verisi bulunan atıf yapılan PRK sonrası ektazi serisinde ektazili gözlerin %77'sinde toplam ERSS ≥4, %9'unda puan 3 ve %14'ünde puan ≤2 idi. Çalışmadaki cerrahi kohort insidansı 9/31.045 göz (%0,029) olarak bildirildi. MUTLAK OLASILIK: Tek bir PRK puanı için belirlenmemiştir. SINIRLAMA: Bunlar ektazi vakaları arasındaki dağılımlar ve genel kohort insidansıdır; puana özgü hasta olasılıkları değildir. LASIK ERSS, PRK için mutlak risk hesaplayıcısı olarak doğrulanmamıştır; %0,029 kohort insidansı bireysel bir puana atanamaz. KAYNAK: Fotorefraktif keratektomi sonrası korneal ektazi risk değerlendirmesi."
  };
  const translate = value => {
    const text = String(value ?? "");
    if (locale !== "tr" || !text) return text;
    if (CLINICAL[text]) return CLINICAL[text];
    if (TR[text]) return TR[text];
    if (text.startsWith("ML7 ") && TR[text.slice(4)]) return `ML7 ${TR[text.slice(4)]}`;
    return text
      .replace(/^CER-AI SCORE — SOURCE & BREAKDOWN:/,"CER-AI PUANI — KAYNAK VE DÖKÜM:")
      .replace(/^ECTASIA RISK INTERPRETATION:/,"EKTAZİ RİSK YORUMU:")
      .replace(/^ABSOLUTE PROBABILITY:/,"MUTLAK OLASILIK:")
      .replace(/^LIMITATION:/,"SINIRLAMA:")
      .replace(/^Inter-eye tomography concern:/,"Gözler arası tomografi değerlendirmesi:")
      .replace(/^Recommended IOL:\s*/,"Önerilen IOL: ")
      .replace(/^Selected images \((\d+)\): /,"Seçilen görüntüler ($1): ")
      .replace(/^Embedded toric calculation — ([\d.]+) D K6 spherical equivalent$/,"Uygulama içi torik hesap — $1 D K6 sferik eşdeğer")
      .replace(/^([A-Z0-9]+) · ([\d.]+)° marker axis$/,"$1 · $2° işaretleme aksı")
      .replace(/^Predicted residual cylinder: ([\d.]+) D at ([\d.]+)° \(prototype estimate\)\.$/,"Tahmini rezidüel silindir: $1 D, $2° (prototip tahmini).")
      .replace(/^Eligible:\s*/,"Uygun: ")
      .replace(/\bToric Multifocal\b/g,"Torik Multifokal")
      .replace(/\bToric Monofocal\b/g,"Torik Monofokal")
      .replace(/\bToric EDOF\b/g,"Torik EDOF")
      .replace(/^Age: (\d+) years \(([^)]+)\)\.$/,"Yaş: $1 yıl ($2).")
      .replace(/^Near-vision demand is (\w+) and halo\/glare tolerance is (\w+)\.$/,"Yakın görme gereksinimi $1 ve halo/kamaşma toleransı $2.")
      .replace(/^Night-driving requirement is (\w+)\.$/,"Gece araç kullanma gereksinimi $1.")
      .replace(/^Total Corneal HOA \(4 mm\) is ([\d.]+) µm \((\w+)\)\.$/,"Total Korneal HOA (4 mm) $1 µm ($2).")
      .replace(/^Pentacam Pupil Dia \(3D\) is ([\d.]+) mm; the target range is 2\.00–4\.00 mm inclusive\. Outside this range, multifocal selection requires surgeon confirmation, not automatic exclusion\.$/,"Pentacam Pupil Dia (3D) $1 mm'dir; hedef aralık 2,00–4,00 mm'dir (sınırlar dahil). Aralık dışında multifokal otomatik dışlanmaz; seçim için cerrah onayı gerekir.")
      .replace(/^Angle kappa is ([\d.]+) mm and angle alpha is ([\d.]+) mm\.$/,"Kappa açısı $1 mm ve alfa açısı $2 mm'dir.")
      .replace(/^Retinal status is ([^;]+); macular pathology is ([^;]+); glaucoma status is ([^.]+)\.$/,"Retina durumu $1; maküler patoloji $2; glokom durumu $3.")
      .replace(/^Ocular-surface status is ([^.]+)\.$/,"Oküler yüzey durumu $1.")
      .replace(/^Active IOLMaster 500 K difference is ([\d.]+) D \(([^)]+)\); toric evaluation requires more than 1\.00 D\.$/,"Aktif IOLMaster 500 K farkı $1 D'dir ($2); torik değerlendirme için 1,00 D'nin üzerinde olmalıdır.")
      .replace(/^Prior LASIK\/PRK overrides the standard route\. Use the Barrett True-K (history|no-history) pathway externally\.$/,"Önceki LASIK/PRK standart yolu geçersiz kılar. Barrett True-K $1 yolunu harici olarak kullanın.")
      .replace(/^Cooke K6 service returned HTTP (\d+)\.$/,"Cooke K6 hizmeti HTTP $1 hatası döndürdü.")
      .replace(/^Cooke K6 could not complete the calculation\. No substitute was used \(([^)]+)\)\.$/,"Cooke K6 hesaplamayı tamamlayamadı. Yerine başka bir yöntem kullanılmadı ($1).")
      .replace(/^Cooke K6 spherical calculation was unavailable \(([^)]+)\)\. No toric power or axis was selected\.$/,"Cooke K6 sferik hesaplaması kullanılamadı ($1). Torik güç veya aks seçilmedi.")
      .replace(/^Embedded toric calculation rejected these measurements \(([^)]+)\)\.$/,"Uygulama içi torik hesaplama bu ölçümleri reddetti ($1).")
      .replace(/^Unable to transcribe (.+)\.$/,"$1 dosyası aktarılamadı.")
      .replace(/^Server returned a non-JSON response: /,"Sunucu JSON olmayan bir yanıt döndürdü: ")
      .replace(/^Request failed \((\d+)\)\.$/,"İstek başarısız oldu ($1).")
      .replace(/^(\d+) source image\(s\)\. Original filenames are shown only to the account that created this case\.$/,"$1 kaynak görüntüsü. Özgün dosya adları yalnızca bu vakayı oluşturan hesaba gösterilir.")
      .replace(/^(\d+) audit event\(s\) loaded\.$/,"$1 denetim olayı yüklendi.")
      .replace(/\b(not required at or below threshold|resolved after treatment|occasional|frequent|moderate|significant|suspect|definite|regular|irregular|present|absent|mild|high|low|none)\b/gi,word=>({"not required at or below threshold":"eşikte ve altında gerekli değil","resolved after treatment":"tedavi sonrası düzeldi","occasional":"ara sıra","frequent":"sık","moderate":"orta","significant":"belirgin","suspect":"şüpheli","definite":"kesin","regular":"düzenli","irregular":"düzensiz","present":"var","absent":"yok","mild":"hafif","high":"yüksek","low":"düşük","none":"yok"})[word.toLowerCase()]||word)
      .replace(/^Open (.+)$/,(_,name)=>`${name} aracını aç`)
      .replace(/^(\d+) archived revision\(s\) found\.$/,"$1 arşivlenmiş revizyon bulundu.")
      .replace(/^(\d+) source image\(s\)\./,"$1 kaynak görüntüsü.")
      .replace(/^Extraction completed\. Surgeon entry is required only for unreadable fields: (.+)\.$/,"Çıkarma tamamlandı. Yalnızca okunamayan alanlar için cerrah girişi gereklidir: $1.")
      .replace(/NO MAJOR INTER-EYE DISCORDANCE DETECTED/g,"BELİRGİN GÖZLER ARASI UYUMSUZLUK SAPTANMADI")
      .replace(/No major categorical inter-eye tomography discordance detected\./g,"Belirgin kategorik gözler arası tomografi uyumsuzluğu saptanmadı.")
      .replace(/This is not a clearance criterion and does not change the CER-AI score or final disposition\./g,"Bu bir cerrahi onay ölçütü değildir ve CER-AI puanını veya nihai kararı değiştirmez.")
      .replace(/device QS is NOT_OK/g,"cihaz QS değeri NOT_OK")
      .replace(/explicit QS: OK was not confirmed/g,"açık QS: OK doğrulanmadı")
      .replace(/source image quality is LIMITED/g,"kaynak görüntü kalitesi SINIRLI")
      .replace(/source image quality is INADEQUATE/g,"kaynak görüntü kalitesi YETERSİZ")
      .replace(/The assessment was generated from the readable data, but acquisition quality is not confirmed as OK\. The surgeon must review the source images and interpret all findings with caution\./g,"Değerlendirme okunabilen verilerden oluşturuldu; ancak çekim kalitesinin uygun olduğu doğrulanmadı. Cerrah kaynak görüntüleri incelemeli ve tüm bulguları dikkatle yorumlamalıdır.")
      .replace(/Hard stops are independent of this numeric score and are not counted as score points\./g,"Kesin durdurma kuralları bu sayısal puandan bağımsızdır ve puana eklenmez.")
      .replace(/NICE is an independent screening pathway and is not added to the CER-AI numeric score\./g,"NICE bağımsız bir tarama yoludur ve CER-AI sayısal puanına eklenmez.")
      .replace(/Superior hinge at the vertical steep meridian/g,"Dikey dik meridyende superior menteşe")
      .replace(/Temporal hinge preferred at the horizontal steep meridian/g,"Yatay dik meridyende temporal menteşe tercih edilir")
      .replace(/surgeon determines the anatomical hinge location/g,"cerrah anatomik menteşe konumunu belirler")
      .replace(/Astigmatic disparity within validation thresholds: magnitude difference ([\d.]+) D; axis difference ([\d.]+)°; no PS3 consequence\./g,"Astigmatik uyumsuzluk doğrulama sınırları içindedir: büyüklük farkı $1 D; aks farkı $2°; PS3 sonucu etkilenmez.")
      .replace(/\bdefinition:/g,"Tanım:")
      .replace(/Temporal hinge \(default\)/g,"Temporal menteşe (varsayılan)")
      .replace(/^Superior$/,"Superior")
      .replace(/^Temporal$/,"Temporal")
      .replace(/^Nasal$/,"Nazal")
      .replace(/\bNot documented\b/gi,"Belgelenmedi")
      .replace(/\bNot applicable\b/gi,"Uygulanamaz")
      .replace(/\baxis unavailable\b/gi,"aks mevcut değil")
      .replace(/\bLOWER_FLAGGED_BURDEN\b/g,"DÜŞÜK UYARI YÜKÜ")
      .replace(/\bNORMAL_SYMMETRIC\b/g,"NORMAL_SİMETRİK")
      .replace(/\bREASSURING\b/g,"RAHATLATICI")
      .replace(/\bADEQUATE\b/g,"YETERLİ")
      .replace(/\bMYOPIC\b/g,"MİYOPİK")
      .replace(/\bHYPEROPIC\b/g,"HİPERMETROPİK")
      .replace(/\bMIXED\b/g,"KARMA")
      .replace(/\bNO_NICE_ESCALATION\b/g,"NICE ARTIRIMI YOK")
      .replace(/\bPENTACAM_PRINTED\b/g,"PENTACAM YAZILI DEĞER")
      .replace(/\bPENTACAM_LABELED_K2\b/g,"PENTACAM ETİKETLİ K2")
      .replace(/\bPENTACAM_LABELED_IS\b/g,"PENTACAM ETİKETLİ I-S")
      .replace(/\byes\b/gi,"evet")
      .replace(/\bno\b/gi,"hayır")
      .replace(/\bunknown\b/gi,"bilinmiyor")
      .replace(/point\(s\)/gi,"puan")
      .replace(/\bcentral_pachymetry\b/gi,"santral pakimetri")
      .replace(/\bposterior_elevation\b/gi,"posterior elevasyon")
      .replace(/\bB_Ele_Th\b/g,"B. Ele.Th")
      .replace(/\bcentral_pachy\b/gi,"santral pakimetri")
      .replace(/\bB_Ele_Th_um\b/g,"B. Ele.Th (µm)")
      .replace(/\bcentral_pachy_um\b/gi,"santral pakimetri (µm)")
      .replace(/\bI_S\b/g,"I-S")
      .replace(/\bK2_D\b/g,"K2 (D)")
      .replace(/\bI_S_D\b/g,"I-S (D)")
      .replace(/\bsource\b/gi,"kaynak");
  };
  const translateDOM = root => {
    if (locale !== "tr" || !root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      if (!root.parentElement?.closest("script,style,pre")) {
        const raw=root.nodeValue, trimmed=raw.trim();
        if(trimmed){const translated=translate(trimmed);if(translated!==trimmed)root.nodeValue=raw.replace(trimmed,translated);}
      }
      return;
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
    for(const node of nodes){
      if(node.parentElement?.closest("script,style,pre")) continue;
      const raw=node.nodeValue, trimmed=raw.trim(); if(!trimmed)continue;
      const translated=translate(trimmed); if(translated!==trimmed)node.nodeValue=raw.replace(trimmed,translated);
    }
    const attributed=[...(root.matches?.("[aria-label],[title],[placeholder]")?[root]:[]),...(root.querySelectorAll?.("[aria-label],[title],[placeholder]")||[])];
    attributed.forEach(el=>{
      for(const attr of ["aria-label","title","placeholder"]){const raw=el.getAttribute(attr),translated=raw?translate(raw):raw;if(raw&&translated!==raw)el.setAttribute(attr,translated);}
    });
  };
  const setLocale = next => { localStorage.setItem("cerai-language", next === "tr" ? "tr" : "en"); location.reload(); };
  window.CERAI_I18N={locale,translate,clinical:translate,translateDOM,setLocale};
  document.documentElement.lang=locale;
  const initialize = () => {
    document.title=translate(document.title);
    translateDOM(document.body);
    if(!document.querySelector("[data-language]")){
      const switcher=document.createElement("div");
      switcher.id="cerai-language-switch";
      switcher.setAttribute("aria-label",translate("Language"));
      switcher.style.cssText="position:fixed;right:12px;bottom:12px;z-index:10000;display:flex;gap:4px;padding:4px;border:1px solid #8ca2b2;border-radius:8px;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.16)";
      for(const code of ["en","tr"]){
        const button=document.createElement("button");
        button.type="button";button.dataset.language=code;button.textContent=code.toUpperCase();
        button.setAttribute("aria-pressed",String(locale===code));
        button.style.cssText=`width:auto;margin:0;padding:6px 9px;border:0;border-radius:5px;cursor:pointer;font:700 12px Arial,sans-serif;color:${locale===code?"#fff":"#173b57"};background:${locale===code?"#173b57":"#eef3f6"}`;
        button.addEventListener("click",()=>setLocale(code));switcher.appendChild(button);
      }
      document.body.appendChild(switcher);
    }
    document.querySelectorAll("[data-language]").forEach(button=>{
      button.setAttribute("aria-pressed",String(button.dataset.language===locale));
      if(!button.dataset.ceraiLanguageBound){button.addEventListener("click",()=>setLocale(button.dataset.language));button.dataset.ceraiLanguageBound="true";}
    });
    if(locale==="tr"){
      const observer=new MutationObserver(records=>records.forEach(record=>{
        record.addedNodes.forEach(node=>translateDOM(node));
        if(record.type==="attributes")translateDOM(record.target);
      }));
      observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["aria-label","title","placeholder"]});
    }
  };
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initialize,{once:true});else initialize();
})();
