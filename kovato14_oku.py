🎯 REPLY KEYBOARD BUTONLARI
1. oku → Menüyü göster
2. Temizle → /clear komutu
3. Kova → /process komutu

4. TEK → /tek komutu
-gerksiz-
revize 
Excel dosyasını gruplara ayırır
Tüm çıktıları tek kişisel maile gönderir (ZIP olarak)



5. stop → İptal komutu
6. JSON yap → /js komutu
revize 
(makro/xls vb > js > grup değiştir)

7. Komutlar → Komut listesi
8. Pdf → /pdf komutu
PDF dosyalarını gruplara göre işler
Şehir bazlı mail gönderimi yapar

/pex komutu oluşturulacak,
komutun görevi şu olacak
dosya içeriği ile ilgilenmeyecek,
dosyaadı=iladı olacak
dosya tipi: pdf, excel
il.pdf, il.xls, il.xlsx
örnek: ankara.pdf, van.xlsx, kars.xls

dosya adı referans alınacak,
grup listesinde eşleşen gruplara gönderilecek,

ankara.pdf ili eşleşen şu gruplara gönderilecek,

grup_1	grup_8	grup_9	grup_10
antalya_sube	eskişehir_sube	kütahya_sube	corum_sube
Afyon	Afyon	Afyon	Amasya
Ankara	Ankara	Ankara	Ankara












TEMEL KOMUTLAR
1. /start
Botu başlatır ve hoş geldin mesajı gösterir
2. /oku, /r, /klavye
Reply keyboard menüsünü gösterir
Kullanıcı dostu buton arayüzü sunar
3. /process
Excel dosyası işleme modunu başlatır
Gruplara ayırır ve ilgili emaillere gönderir
4. /tek
Excel dosyasını gruplara ayırır
Tüm çıktıları tek kişisel maile gönderir (ZIP olarak)
5. /cancel, /iptal, /stop
Mevcut işlemi iptal eder
State'i temizler

📧 MAIL İŞLEMLERİ
6. /toplumaile, /toplumail, /tmail
Input ve Output'taki tüm dosyaları ZIP yapar
PERSONAL_EMAIL'e gönderir
7. /send_test_email
Adminler için test maili gönderir

📁 DOSYA YÖNETİMİ
8. /files o
Output dosyalarını ZIP olarak indirir
9. /files l
Log dosyalarını ZIP olarak indirir
10. /clear
Input, Output ve temp dosyalarını temizler
11. /clear log
Sadece log dosyalarını temizler
12. /dosyalarıgöster, /dosyalar
Input ve Output'taki dosyaları listeler
🔧 SİSTEM KOMUTLARI
13. /status
Sistem durumunu ve istatistikleri gösterir
14. /logs
Son logları gösterir
15. /admin
Admin panelini açar (sadece adminler)
İstatistikler, log görüntüleme, grup yönetimi vb.
16. /id
Kullanıcı ID'sini ve admin listesini gösterir
📊 VERİ İŞLEME
17. /js
Excel'den JSON grupları oluşturur
Grup yapılandırması için
18. /pdf
PDF dosyalarını gruplara göre işler
Şehir bazlı mail gönderimi yapar
🔍 GELİŞTİRİCİ KOMUTLARI
19. /dar - Proje analiz araçları:
/dar → Proje ağaç yapısı
/dar k → Tüm komutları listeler
/dar t → Tüm dosya içeriklerini gösterir
/dar t [dosya] → Belirli dosyanın içeriği
/dar t [klasör] → Klasördeki dosyalar
/dar Z → Tüm projeyi ZIP olarak indirir
20. /get_logfile
Log dosyasını indirir (adminler)
🎯 REPLY KEYBOARD BUTONLARI
1. oku → Menüyü göster
2. Temizle → /clear komutu
3. Kova → /process komutu
4. TEK → /tek komutu
5. stop → İptal komutu
6. JSON yap → /js komutu
7. Komutlar → Komut listesi
8. Pdf → /pdf komutu
📦 ANA İŞLEVSELLİKLER
Excel İşleme: TARİH ve İL sütunlarına göre gruplama
Grup Yönetimi: JSON tabanlı şehir-grup eşleştirmesi
Mail Gönderimi: Grup bazlı otomatik mail dağıtımı
PDF İşleme: Şehir bazlı PDF dağıtımı
Admin Panel: Sistem yönetimi ve izleme
Otomatik Yedekleme: Input/Output dosyalarının otomatik maili
Log Yönetimi: Kapsamlı loglama ve hata takibi
Bu komutlar, kapsamlı bir veri işleme ve dağıtım sistemi oluşturuyor. Özellikle Excel dosyalarını şehir bazlı gruplara ayırıp ilgili ekiplere otomatik mail gönderme konusunda oldukça gelişmiş bir yapı sunuyor.
