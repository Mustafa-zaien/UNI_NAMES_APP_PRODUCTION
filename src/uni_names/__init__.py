"""
uni_names: High-performance name matching and deduplication toolkit.

Simplified version that works with the current doctor_cleaner setup.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Setup logger
logger = logging.getLogger(__name__)

# ✅ إضافة مسار doctor_cleaner
try:
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    doctor_cleaner_path = project_root / "doctor_cleaner"
    
    if str(doctor_cleaner_path) not in sys.path:
        sys.path.insert(0, str(doctor_cleaner_path))
    
    from cli import process_file as _cli_process_file
    from cli import clean_name, normalize_specialty
    DOCTOR_CLEANER_AVAILABLE = True
    logger.info(f"✅ Doctor cleaner loaded from: {doctor_cleaner_path}")
    
except ImportError as e:
    logger.warning(f"⚠️ Doctor cleaner not available: {e}")
    DOCTOR_CLEANER_AVAILABLE = False

# ✅ Import GUI component
try:
    from .clean_names_app_qt import UniNameWidget
    GUI_AVAILABLE = True
    logger.info("✅ GUI component loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ GUI component not available: {e}")
    UniNameWidget = None
    GUI_AVAILABLE = False

# ✅ Facade functions للتوافق العكسي
def process_file(input_path: str, output_path: str, 
                auto_threshold: float = 0.95,
                manual_threshold: float = 0.7,
                progress_callback: Optional[callable] = None,
                **kwargs) -> Dict[str, Any]:
    """Process file with medical names - main facade function."""
    
    if not DOCTOR_CLEANER_AVAILABLE:
        return {"success": False, "error": "Doctor cleaner module not available"}
    
    try:
        _cli_process_file(
            input_path=input_path,
            output_path=output_path,
            golden_path=kwargs.get('golden_path'),
            new_aliases_out=kwargs.get('new_aliases_out'),
            threshold=manual_threshold,
        )
        return {"success": True, "message": "Processing completed successfully"}
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        return {"success": False, "error": str(e)}

def compare_names(name1: str, name2: str) -> float:
    """Compare two medical names and return similarity score."""
    if not DOCTOR_CLEANER_AVAILABLE:
        return 1.0 if name1.lower().strip() == name2.lower().strip() else 0.0
    
    try:
        # استخدام الـ fuzzy matching من doctor_cleaner
        from cli import fuzz, ADVANCED_MODE
        if ADVANCED_MODE and hasattr(fuzz, 'ratio'):
            return fuzz.ratio(name1, name2) / 100.0
        else:
            return 1.0 if name1.lower().strip() == name2.lower().strip() else 0.0
    except Exception as e:
        logger.debug(f"Fuzzy matching failed, using exact match: {e}")
        return 1.0 if name1.lower().strip() == name2.lower().strip() else 0.0

def normalize_name(name: str, is_person: bool = True) -> str:
    """Normalize a medical name."""
    if not DOCTOR_CLEANER_AVAILABLE:
        return name.strip().title()
    
    try:
        return clean_name(name, is_person=is_person)
    except Exception as e:
        logger.debug(f"Name cleaning failed, using basic normalization: {e}")
        return name.strip().title()

# ✅ Processor class للتوافق
class Processor:
    """High-level processor for medical name processing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        logger.info("🔧 Processor initialized")
    
    def process_file(self, input_path: str, output_path: str, **kwargs) -> Dict[str, Any]:
        return process_file(input_path, output_path, **kwargs)

# ✅ Exports
__all__ = [
    "process_file",
    "compare_names",
    "normalize_name", 
    "Processor",
    "DOCTOR_CLEANER_AVAILABLE",
    "GUI_AVAILABLE",
]

# إضافة UniNameWidget لو متاح
if GUI_AVAILABLE:
    __all__.append("UniNameWidget")

__version__ = "2.0.0"

# Module info
def get_info() -> Dict[str, Any]:
    """Get module information and status."""
    return {
        "version": __version__,
        "doctor_cleaner_available": DOCTOR_CLEANER_AVAILABLE,
        "gui_available": GUI_AVAILABLE,
        "components": __all__
    }
