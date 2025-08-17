from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass(frozen=True)
class Paths:
    """مسارات النظام المحسن"""
    base_dir: Path
    default_input: Path
    default_output: Path
    golden_reference: Path
    reference_golden: Path  # ✅ إضافة المرجع من مجلد reference
    new_aliases_out: Path
    
    # مسارات إضافية للنظام المحسن
    enhanced_output: Optional[Path] = None
    specialty_mapping: Optional[Path] = None
    debug_log: Optional[Path] = None

    @staticmethod
    def from_script(script_path: str | Path) -> "Paths":
        """إنشاء مسارات من موقع السكريبت"""
        base = Path(script_path).resolve().parent
        
        return Paths(
            base_dir=base,
            default_input=base / "Doctor List.xlsx",
            default_output=base / "Doctor_List_ML.xlsx",
            golden_reference=base / "golden_reference.xlsx",
            reference_golden=base / "reference" / "golden_doctors.xlsx",  # ✅ المرجع الجديد
            new_aliases_out=base / "Doctor_List_Final_Names.xlsx",
            enhanced_output=base / "Doctor_List_Enhanced.xlsx",
            specialty_mapping=base / "specialty_mapping.xlsx",
            debug_log=base / "processing_debug.log",
        )

@dataclass(frozen=True)
class ProcessingConfig:
    """إعدادات المعالجة المحسنة"""
    
    # عتبات التشابه
    auto_merge_threshold: float = 0.90
    unsure_threshold: float = 0.70
    golden_match_threshold: float = 0.80
    
    # إعدادات التجميع
    enable_clustering: bool = True
    max_cluster_rows: int = 30000
    cluster_distance_threshold: float = 0.30
    
    # إعدادات الاستخراج الذكي
    enable_smart_extraction: bool = True
    preserve_original_names: bool = True
    extract_specialties: bool = True
    
    # إعدادات المرجع الذهبي
    auto_learn_from_golden: bool = True
    golden_priority_over_clustering: bool = True
    
    # إعدادات التصدير
    include_debug_columns: bool = False
    split_persons_facilities: bool = True
    generate_stats_report: bool = True

# ✅ إضافة دالة للعثور على أفضل مرجع ذهبي
def get_best_golden_reference(base_path: Path) -> Optional[Path]:
    """العثور على أفضل مرجع ذهبي متاح"""
    
    # أولوية البحث
    candidates = [
        base_path / "reference" / "golden_doctors.xlsx",      # المرجع الرئيسي الجديد
        base_path / "reference" / "golden_reference.xlsx",   # بديل في reference
        base_path / "golden_reference.xlsx",                 # المرجع القديم
        base_path / "doctor_cleaner" / "golden_reference.xlsx"  # في المجلد الفرعي
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    return None

# الإعدادات الافتراضية
DEFAULT_CONFIG = ProcessingConfig()
