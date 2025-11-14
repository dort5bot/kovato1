# handlers/pex_handler.py
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Dict, List
import tempfile
import zipfile
from pathlib import Path

from config import config
from utils.group_manager import group_manager
from utils.mailer import send_email_with_attachment
from utils.logger import logger

router = Router()

class PexProcessingStates(StatesGroup):
    waiting_for_files = State()

@router.message(Command("pex"))
async def cmd_pex(message: Message, state: FSMContext):
    """PEX - Dosya adı bazlı dağıtım komutu"""
    await state.set_state(PexProcessingStates.waiting_for_files)
    await message.answer(
        "📁 **PEX MODU - DOSYA ADI BAZLI DAĞITIM**\n\n"
        "Lütfen dağıtmak istediğiniz dosyaları gönderin.\n\n"
        "📋 **KURALLAR:**\n"
        "• Dosya adı şehir adı olmalı: 'ankara.pdf', 'van.xlsx' gibi\n"
        "• Desteklenen formatlar: PDF, Excel (.xls, .xlsx)\n"
        "• Aynı anda birden fazla dosya gönderebilirsiniz\n\n"
        "🔄 **İŞLEM:**\n"
        "1. Dosya adındaki şehir gruplarda aranır\n"
        "2. Eşleşen tüm gruplara dosya gönderilir\n"
        "3. Her grup kendi email listesine ulaşır\n\n"
        "İşlemi başlatmak için '/tamam' yazın"
    )

@router.message(PexProcessingStates.waiting_for_files, F.document)
async def handle_pex_file_upload(message: Message, state: FSMContext):
    """PEX dosyalarını işler"""
    try:
        # Dosya kontrolü
        valid_extensions = ['.pdf', '.xls', '.xlsx']
        file_ext = Path(message.document.file_name).suffix.lower()
        
        if file_ext not in valid_extensions:
            await message.answer("❌ Desteklenmeyen dosya formatı. PDF veya Excel gönderin.")
            return
        
        # Dosya adından şehir adını çıkar
        city_name = Path(message.document.file_name).stem.lower()
        
        # Mevcut state'deki dosyaları al
        current_data = await state.get_data()
        pex_files = current_data.get('pex_files', [])
        
        # Dosyayı indir
        file_id = message.document.file_id
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = config.INPUT_DIR / message.document.file_name
        
        await bot.download_file(file.file_path, file_path)
        
        # Dosya bilgisini kaydet
        pex_files.append({
            'path': file_path,
            'filename': message.document.file_name,
            'city_name': city_name,
            'extension': file_ext
        })
        
        await state.update_data(pex_files=pex_files)
        
        await message.answer(
            f"✅ Dosya eklendi: {message.document.file_name}\n"
            f"🏙️  Algılanan şehir: {city_name.upper()}\n"
            f"📁 Toplam dosya: {len(pex_files)}\n\n"
            "Başka dosya göndermek için bekliyorum...\n"
            "İşlemi başlatmak için '/tamam' yazın."
        )
        
    except Exception as e:
        logger.error(f"PEX dosya yükleme hatası: {e}")
        await message.answer("❌ Dosya işlenirken hata oluştu.")

@router.message(PexProcessingStates.waiting_for_files, F.text == "/tamam")
async def handle_process_pex(message: Message, state: FSMContext):
    """PEX işlemini başlat"""
    try:
        data = await state.get_data()
        pex_files = data.get('pex_files', [])
        
        if not pex_files:
            await message.answer("❌ İşlenecek dosya yok.")
            await state.clear()
            return
        
        await message.answer("⏳ Dosyalar gruplara dağıtılıyor ve mailler hazırlanıyor...")
        
        # Dosyaları gruplara göre işle
        result = await process_pex_files(pex_files, message.from_user.id)
        
        if result["success"]:
            # Rapor oluştur
            report = generate_pex_report(result)
            await message.answer(report)
        else:
            await message.answer(f"❌ İşlem başarısız: {result.get('error', 'Bilinmeyen hata')}")
        
    except Exception as e:
        logger.error(f"PEX işleme hatası: {e}")
        await message.answer("❌ PEX işleme sırasında hata oluştu.")
    finally:
        await state.clear()

async def process_pex_files(pex_files: List[Dict], user_id: int) -> Dict:
    """PEX dosyalarını gruplara dağıtır"""
    try:
        # 1. Dosyaları şehirlere göre gruplandır
        city_to_files = {}
        for file_info in pex_files:
            city_name = file_info['city_name']
            if city_name not in city_to_files:
                city_to_files[city_name] = []
            city_to_files[city_name].append(file_info)
        
        # 2. Her şehir için ilgili grupları bul
        group_to_files = {}
        email_results = []
        
        for city_name, file_list in city_to_files.items():
            # Şehir adını normalize et
            normalized_city = group_manager.normalize_city_name(city_name)
            
            # Bu şehirle eşleşen grupları bul
            group_ids = group_manager.get_groups_for_city(normalized_city)
            
            for group_id in group_ids:
                if group_id not in group_to_files:
                    group_to_files[group_id] = []
                
                # Bu gruba tüm dosyaları ekle
                group_to_files[group_id].extend(file_list)
        
        # 3. Her grup için dosyaları birleştir ve mail gönder
        for group_id, file_list in group_to_files.items():
            if not file_list:
                continue
                
            group_info = group_manager.get_group_info(group_id)
            recipients = group_info.get("email_recipients", [])
            
            if not recipients:
                logger.warning(f"Grup {group_id} için email alıcısı tanımlı değil")
                continue
            
            # Dosyaları ZIP yap
            zip_path = await create_pex_zip(file_list, group_info)
            if not zip_path:
                continue
            
            # Mail gönder
            file_types = list(set(f['extension'] for f in file_list))
            subject = f"📎 {group_info.get('group_name', group_id)} - {len(file_list)} Dosya"
            body = (
                f"Merhaba,\n\n"
                f"{group_info.get('group_name', group_id)} grubu için {len(file_list)} adet dosya ektedir.\n"
                f"Dosya türleri: {', '.join(file_types)}\n"
                f"İlgili şehirler: {', '.join(set(f['city_name'].upper() for f in file_list))}\n\n"
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
                    "file_count": len(file_list),
                    "cities": list(set(f['city_name'] for f in file_list)),
                    "error": None if success else "Mail gönderilemedi"
                })
            
            # Geçici ZIP'i sil
            zip_path.unlink(missing_ok=True)
        
        # 4. Geçici dosyaları temizle
        for file_info in pex_files:
            try:
                file_info['path'].unlink(missing_ok=True)
            except:
                pass
        
        return {
            "success": True,
            "processed_files": len(pex_files),
            "groups_processed": len(group_to_files),
            "email_results": email_results,
            "group_details": group_to_files
        }
        
    except Exception as e:
        logger.error(f"PEX dosya işleme hatası: {e}")
        return {"success": False, "error": str(e)}

async def create_pex_zip(file_list: List[Dict], group_info: Dict) -> Path:
    """Dosyaları ZIP olarak paketler"""
    try:
        group_name = group_info.get("group_name", group_info.get("group_id", "dosyalar"))
        zip_name = f"{group_name}_dosyalar.zip"
        zip_path = Path(tempfile.gettempdir()) / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_info in file_list:
                if file_info['path'].exists():
                    zipf.write(file_info['path'], file_info['filename'])
        
        return zip_path
        
    except Exception as e:
        logger.error(f"PEX ZIP oluşturma hatası: {e}")
        return None

def generate_pex_report(result: Dict) -> str:
    """PEX işleme raporu oluşturur"""
    if not result.get("success", False):
        return f"❌ PEX işleme başarısız: {result.get('error', 'Bilinmeyen hata')}"
    
    processed_files = result.get("processed_files", 0)
    groups_processed = result.get("groups_processed", 0)
    email_results = result.get("email_results", [])
    
    successful_emails = sum(1 for res in email_results if res.get("success", False))
    failed_emails = len(email_results) - successful_emails
    
    report_lines = [
        "✅ **PEX DAĞITIM RAPORU**",
        f"📁 İşlenen dosya: {processed_files}",
        f"👥 İşlem yapılan grup: {groups_processed}",
        f"📧 Başarılı mail: {successful_emails}",
        f"❌ Başarısız mail: {failed_emails}",
        "",
        "📋 **GRUP DETAYLARI:**"
    ]
    
    # Grup bazlı detaylar
    group_details = result.get("group_details", {})
    for group_id, file_list in group_details.items():
        group_info = group_manager.get_group_info(group_id)
        group_name = group_info.get("group_name", group_id)
        cities = list(set(f['city_name'].upper() for f in file_list))
        report_lines.append(f"• {group_name}: {len(file_list)} dosya ({', '.join(cities)})")
    
    return "\n".join(report_lines)

@router.message(PexProcessingStates.waiting_for_files)
async def handle_wrong_pex_input(message: Message):
    """Yanlış PEX girişi"""
    await message.answer(
        "❌ Lütfen PDF veya Excel dosyası gönderin veya işlemi başlatmak için '/tamam' yazın.\n"
        "İptal etmek için '/iptal' komutunu kullanın."
    )