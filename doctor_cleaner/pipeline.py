from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import sys
import logging

# Ensure proper path setup
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Try advanced facade first, fallback to enhanced CLI
try:
    from uni_names import process_file as _facade_process_file
except Exception:
    _facade_process_file = None

# Enhanced CLI with smart extraction
from cli import (
    process_file as _enhanced_process_file,
    update_golden_from_review as _update_golden_from_review,
    UNSURE_THRESHOLD_DEFAULT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@dataclass
class ProcessRequest:
    input_path: Path
    output_path: Path
    golden_path: Optional[Path]
    new_aliases_out: Optional[Path]
    threshold: float = UNSURE_THRESHOLD_DEFAULT

def run_processing(req: ProcessRequest) -> None:
    """تشغيل المعالجة باستخدام النظام المحسن"""
    
    logging.info(f"🚀 PIPELINE: Starting enhanced processing")
    logging.info(f"📁 Input: {req.input_path}")
    logging.info(f"📁 Output: {req.output_path}")
    logging.info(f"🏆 Golden: {req.golden_path or 'auto-detect'}")
    logging.info(f"🎯 Threshold: {req.threshold}")
    
    # ✅ تحديد مسار المرجع الذهبي بذكاء
    golden_path_to_use = None
    
    if req.golden_path and req.golden_path.exists():
        golden_path_to_use = str(req.golden_path)
        logging.info(f"✅ Using custom golden reference: {req.golden_path}")
    else:
        # ✅ البحث الذكي عن أفضل مرجع
        try:
            from config import get_best_golden_reference
            base_path = Path(__file__).parent  
            best_ref = get_best_golden_reference(base_path)
            
            if best_ref:
                golden_path_to_use = str(best_ref)
                logging.info(f"🔍 Auto-detected golden reference: {best_ref}")
            else:
                logging.warning(f"⚠️ No golden reference available anywhere")
        except ImportError:
            logging.warning(f"⚠️ Config module not available, using CLI auto-detection")

    # محاولة استخدام facade المتقدم أولاً
    if _facade_process_file is not None:
        try:
            logging.info("🔄 Trying advanced facade...")
            res = _facade_process_file(
                str(req.input_path),
                str(req.output_path),
                auto_threshold=0.95,
                manual_threshold=float(req.threshold),
                progress_callback=None,
            )
            if isinstance(res, dict) and not res.get("success", True):
                raise RuntimeError(res.get("error", "Facade processing failed"))
            
            logging.info("✅ Advanced facade completed successfully")
            return
            
        except Exception as e:
            logging.warning(f"⚠️ Advanced facade failed: {e}")
            logging.info("🔄 Falling back to enhanced CLI...")

    # استخدام النظام المحسن
    try:
        logging.info("🚀 Using ENHANCED CLI with smart golden detection...")
        
        # ✅ مرر None للـ golden_path عشان CLI يبحث بنفسه
        _enhanced_process_file(
            str(req.input_path),
            str(req.output_path),
            golden_path=golden_path_to_use,  # يمكن يكون None للبحث التلقائي
            new_aliases_out=str(req.new_aliases_out) if req.new_aliases_out else None,
            threshold=req.threshold,
        )
        
        logging.info("✅ Enhanced processing completed successfully!")
        
    except Exception as e:
        logging.error(f"❌ Enhanced processing failed: {e}")
        raise RuntimeError(f"All processing methods failed. Error: {e}")

def learn_from_review(golden_path: Path, reviewed_path: Path, out_path: Optional[Path] = None) -> Path:
    """تحديث المرجع الذهبي من البيانات المراجعة"""
    logging.info("📚 Learning from reviewed data...")
    
    result = _update_golden_from_review(
        base_golden_path=str(golden_path),
        reviewed_path=str(reviewed_path),
        out_path=str(out_path) if out_path else None
    )
    
    logging.info("✅ Golden reference updated successfully")
    return Path(result)
