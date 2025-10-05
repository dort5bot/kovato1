# handlers/pdf_handler.py
"""
PDF İşleme Handler'ı
/pdf komutu - PDF dosyalarını gruplara göre işler ve mailleri gönderir
"""
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Dict, List, Set
import tempfile
import zipfile
from pathlib import Path

from config import config
from utils.group_manager import group_manager
from utils.mailer import send_email_with_attachment
from utils.logger import logger

router = Router()

class PdfProcessingStates(StatesGroup):
    waiting_for_pdfs = State()

@router.message(Command("pdf"))
async def cmd_pdf(message: Message, state: FSMContext):
    """PDF işleme komutu"""
    await state.set_state(PdfProcessingStates.waiting_for_pdfs)
    await message.answer(
        "📄 **PDF İŞLEME MODU**\n\n"
        "Lütfen işlemek istediğiniz PDF dosyalarını gönderin.\n\n"
        "📋 **İşlem Adımları:**\n"
        "1. PDF dosya isimleri şehir adlarıyla eşleştirilir\n"
        "2. Her grup için ilgili PDF'ler birleştirilir\n"
        "3. Grupların email listelerine gönderilir\n\n"
        "Örnek: 'manisa.pdf', 'izmir.pdf' dosyaları\n"
        "→ Manisa ve İzmir şehirleriyle eşleşen gruplara gönderilir"
    )

@router.message(PdfProcessingStates.waiting_for_pdfs, F.document)
async def handle_pdf_upload(message: Message, state: FSMContext):
    """PDF dosyalarını işler"""
    try:
        if not message.document.file_name.endswith('.pdf'):
            await message.answer("❌ Lütfen PDF dosyası gönderin.")
            return
        
        # Mevcut state'deki dosyaları al veya yeni liste oluştur
        current_data = await state.get_data()
        pdf_files = current_data.get('pdf_files', [])
        
        # Dosyayı indir
        file_id = message.document.file_id
        file_name = message.document.file_name
        
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = config.INPUT_DIR / file_name
        
        await bot.download_file(file.file_path, file_path)
        
        # Dosya bilgisini kaydet
        pdf_files.append({
            'path': file_path,
            'filename': file_name,
            'city_name': Path(file_name).stem.lower()  # Dosya adından şehir adını çıkar
        })
        
        await state.update_data(pdf_files=pdf_files)
        
        await message.answer(
            f"✅ PDF eklendi: {file_name}\n"
            f"📁 Toplam PDF: {len(pdf_files)}\n\n"
            "Başka PDF göndermek için bekliyorum...\n"
            "İşlemi başlatmak için '/tamam' yazın."
        )
        
    except Exception as e:
        logger.error(f"PDF yükleme hatası: {e}")
        await message.answer("❌ PDF işlenirken hata oluştu.")

@router.message(PdfProcessingStates.waiting_for_pdfs, F.text == "/tamam")
async def handle_process_pdfs(message: Message, state: FSMContext):
    """PDF işlemini başlat"""
    try:
        data = await state.get_data()
        pdf_files = data.get('pdf_files', [])
        
        if not pdf_files:
            await message.answer("❌ İşlenecek PDF dosyası yok.")
            await state.clear()
            return
        
        await message.answer("⏳ PDF'ler gruplara ayrılıyor ve mailler hazırlanıyor...")
        
        # PDF'leri gruplara göre işle
        result = await process_pdfs_to_groups(pdf_files, message.from_user.id)
        
        if result["success"]:
            # Rapor oluştur
            report = generate_pdf_report(result)
            await message.answer(report)
        else:
            await message.answer(f"❌ İşlem başarısız: {result.get('error', 'Bilinmeyen hata')}")
        
    except Exception as e:
        logger.error(f"PDF işleme hatası: {e}")
        await message.answer("❌ PDF işleme sırasında hata oluştu.")
    finally:
        await state.clear()

@router.message(PdfProcessingStates.waiting_for_pdfs)
async def handle_wrong_input(message: Message):
    """Yanlış giriş"""
    await message.answer(
        "❌ Lütfen PDF dosyası gönderin veya işlemi başlatmak için '/tamam' yazın.\n"
        "İptal etmek için '/iptal' komutunu kullanın."
    )

async def process_pdfs_to_groups(pdf_files: List[Dict], user_id: int) -> Dict:
    """PDF'leri gruplara ayırır ve mailleri gönderir"""
    try:
        # 1. PDF'leri şehirlere göre gruplandır
        city_to_pdfs = {}
        for pdf_file in pdf_files:
            city_name = pdf_file['city_name']
            if city_name not in city_to_pdfs:
                city_to_pdfs[city_name] = []
            city_to_pdfs[city_name].append(pdf_file)
        
        # 2. Her şehir için ilgili grupları bul
        group_to_pdfs = {}
        email_results = []
        
        for city_name, pdf_list in city_to_pdfs.items():
            # Şehir adını normalize et
            normalized_city = group_manager.normalize_city_name(city_name)
            
            # Bu şehirle eşleşen grupları bul
            group_ids = group_manager.get_groups_for_city(normalized_city)
            
            for group_id in group_ids:
                if group_id not in group_to_pdfs:
                    group_to_pdfs[group_id] = []
                
                # Bu gruba tüm PDF'leri ekle
                group_to_pdfs[group_id].extend(pdf_list)
        
        # 3. Her grup için PDF'leri birleştir ve mail gönder
        for group_id, pdf_list in group_to_pdfs.items():
            if not pdf_list:
                continue
                
            group_info = group_manager.get_group_info(group_id)
            recipients = group_info.get("email_recipients", [])
            
            if not recipients:
                logger.warning(f"Grup {group_id} için email alıcısı tanımlı değil")
                continue
            
            # PDF'leri ZIP yap
            zip_path = await create_pdf_zip(pdf_list, group_info)
            if not zip_path:
                continue
            
            # Mail gönder
            subject = f"📄 {group_info.get('group_name', group_id)} - PDF Dosyaları"
            body = (
                f"Merhaba,\n\n"
                f"{group_info.get('group_name', group_id)} grubu için {len(pdf_list)} adet PDF dosyası ektedir.\n\n"
                f"İyi çalışmalar,\nData_listesi_Hıdır"
            )
            
            success = await send_email_with_attachment(
                recipients,
                subject,
                body,
                zip_path
            )
            
            # Sonuçları kaydet
            for recipient in recipients:
                email_results.append({
                    "success": success,
                    "group_id": group_id,
                    "recipient": recipient,
                    "pdf_count": len(pdf_list),
                    "error": None if success else "Mail gönderilemedi"
                })
            
            # Geçici ZIP'i sil
            zip_path.unlink(missing_ok=True)
        
        # 4. Geçici PDF dosyalarını temizle
        for pdf_file in pdf_files:
            try:
                pdf_file['path'].unlink(missing_ok=True)
            except:
                pass
        
        return {
            "success": True,
            "processed_pdfs": len(pdf_files),
            "groups_processed": len(group_to_pdfs),
            "email_results": email_results,
            "group_details": group_to_pdfs
        }
        
    except Exception as e:
        logger.error(f"PDF gruplama hatası: {e}")
        return {"success": False, "error": str(e)}

async def create_pdf_zip(pdf_files: List[Dict], group_info: Dict) -> Path:
    """PDF'leri ZIP dosyası olarak paketler"""
    try:
        # ZIP dosyası için isim oluştur
        group_name = group_info.get("group_name", group_info.get("group_id", "pdfs"))
        zip_name = f"{group_name}_pdfs.zip"
        zip_path = Path(tempfile.gettempdir()) / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_file in pdf_files:
                if pdf_file['path'].exists():
                    zipf.write(pdf_file['path'], pdf_file['filename'])
        
        return zip_path
        
    except Exception as e:
        logger.error(f"PDF ZIP oluşturma hatası: {e}")
        return None

def generate_pdf_report(result: Dict) -> str:
    """PDF işleme raporu oluşturur"""
    if not result.get("success", False):
        return f"❌ PDF işleme başarısız: {result.get('error', 'Bilinmeyen hata')}"
    
    processed_pdfs = result.get("processed_pdfs", 0)
    groups_processed = result.get("groups_processed", 0)
    email_results = result.get("email_results", [])
    
    successful_emails = sum(1 for res in email_results if res.get("success", False))
    failed_emails = len(email_results) - successful_emails
    
    report_lines = [
        "✅ **PDF İŞLEME RAPORU**",
        f"📄 İşlenen PDF: {processed_pdfs}",
        f"👥 İşlem yapılan grup: {groups_processed}",
        f"📧 Başarılı mail: {successful_emails}",
        f"❌ Başarısız mail: {failed_emails}",
        "",
        "📋 **GRUP DETAYLARI:**"
    ]
    
    # Grup bazlı detaylar
    group_details = result.get("group_details", {})
    for group_id, pdf_list in group_details.items():
        group_info = group_manager.get_group_info(group_id)
        group_name = group_info.get("group_name", group_id)
        report_lines.append(f"• {group_name}: {len(pdf_list)} PDF")
    
    # Hata detayları
    if failed_emails > 0:
        report_lines.extend([
            "",
            "⚠️ **HATALAR:**"
        ])
        for error in email_results[:3]:
            if not error.get("success", False):
                report_lines.append(f"• {error.get('recipient', 'Bilinmeyen')}")
    
    return "\n".join(report_lines)