# doctor_cleaner/cli.py
from __future__ import annotations

import argparse
import logging
import time
import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Union
from dataclasses import dataclass
from functools import lru_cache

# التكامل مع النظام المتقدم
try:
    from rapidfuzz import fuzz
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.decomposition import TruncatedSVD
    ADVANCED_MODE = True
except ImportError:
    ADVANCED_MODE = False
    print("[WARNING] Advanced libraries not available. Running in basic mode.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# =========================
# Constants & Configuration
# =========================

# ✅ تحديث المسارات الافتراضية بالبحث الذكي
def get_default_golden_path() -> str:
    """الحصول على أفضل مسار للمرجع الذهبي"""
    try:
        from config import get_best_golden_reference
        base_path = Path(__file__).parent.parent  # للوصول للمجلد الأساسي
        best_ref = get_best_golden_reference(base_path)
        
        if best_ref:
            return str(best_ref)
    except ImportError:
        pass  # لو مافيش config module
    
    # fallback للمسار القديم
    return str(Path(__file__).with_name("golden_reference.xlsx"))

DEFAULT_GOLDEN = get_default_golden_path()  # ✅ استخدام الدالة الذكية
DEFAULT_NEW_ALIASES = str(Path(__file__).with_name("Doctor_List_Final_Names.xlsx"))

# Thresholds
AUTO_MERGE_THRESHOLD = 0.90
UNSURE_THRESHOLD_DEFAULT = 0.70
FIRST_TOKENS_SIM_REQ = 0.80
CLUSTER_DISTANCE_THRESHOLD = 0.30
MAX_CLUSTER_ROWS = 30000

# Regex patterns
NON_WORD = re.compile(r"[^\w\s\-]", re.I)
MULTISPACE = re.compile(r"\s+")
HYPHEN_SPLIT = re.compile(r"[\s\-]+")
TITLE_REGEX = re.compile(r"\b(dr|doctor|prof|mr|mrs|ms|miss|md|phd|msc|bsc|consultant|specialist)\b\.?", re.I)
BRACKETED = re.compile(r"(\{.*?\}|\[.*?\]|\(.*?\)|\$\{.*?\})")
ABD_PAT = re.compile(r"\babd(?:\s*[\-\_])*\s*(?:el|al)\b", flags=re.I)

# Branch codes and service words
BRANCH_CODES = {"alw","akw","snb","ahj","afw","fwz","trd","trad"}
BRANCH_CODES_REGEX = re.compile(rf"\b({'|'.join(sorted(BRANCH_CODES))})\b", re.I)

SERVICE_WORDS = {
    "clinic","screening","dental","endoscopy","endoscopic","er","icu","ent",
    "nutrition","radiology","imaging","xray","x-ray","lab","labs","laboratory",
    "unit","department","dept","center","centre","polyclinic","ward","opd","ipd",
    "ot","theatre","therapy","physio","orthopedic","orthopaedic","derma",
    "dermatology","pediatrics","paediatrics","gyne","gyn","obgyn","ophthalmology",
    "urology","cardio","cardiology","hepatology","gastro","snb","fwz","trd","trad",
    "hospital","homecare","home","care"
}

SERVICE_REGEX = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, SERVICE_WORDS), key=len, reverse=True)) + r")\b",
    re.I
)

# Name normalization maps
TOKEN_MAP = {
    "mohammed":"mohamed","muhammad":"mohamed","mohamad":"mohamed","muhamad":"mohamed",
    "ahmad":"ahmed","youssef":"yousef","yusuf":"yousef","yousif":"yousef",
    "hussain":"hussein","khalid":"khaled","tariq":"tarek","tareq":"tarek",
    "al":"el","al-":"el","el-":"el",
}

COMMON_FAMILY_STOPLIST: Set[str] = {
    "mohamed","ahmed","ali","hassan","hussein","mostafa","mustafa",
    "mahmoud","ibrahim","saad","said","youssef","yousef","omar",
    "hamdy","hamdi","abdallah","abdelrahman"
}

COMMON_GIVEN_TOKENS: Set[str] = {
    "mohamed","mohammad","mohamad","mohd","ahmed","ahmad",
    "abdullah","abdallah","abdel","abdul","ali","hassan","hussein","ibrahim","omar",
    "yousef","youssef","saad","said","khaled","saleh","salem","sayed","saeed",
    "bin","bint","abu","ibn"
}

DEGREE_TOKENS = {"md","phd","msc","bsc","frcs","mrcp","mrcgp","facc","facs","fcps","mbbs","do","dds","dmd","mba","dch"}

# =========================
# Advanced Name Replacements
# =========================

REPLACEMENTS: Dict[str, List[str]] = {
    "abdelfatah": ["abd el fattah","abd el fatah","abdel fattah","abdel fatah","abdelfattah","abdul fatah"],
    "abdelrazek": ["abd el razek","abd el razik","abdel razek","abdel razik","abdelrazik","abdul razek"],
    "abdelrahman": ["abd el rahman","abdel rahman","abd el rhman","abdel rhman","abdulrahman","abdurrahman"],
    "abdallah": ["abd allah","abdellah","abd ellah","abdullah","abdulah","abdulla"],
    "mohamed": ["mohammed","mohamad","muhamed","mohammod","mohammad","muhamad","muhammed"],
    "ahmed": ["ahmad","ahmet","ahmmed","ahmd","ahmid","ahmade"],
    "mostafa": ["mustafa","moustafa","mustpha","mostpha","mustapha","mstafa"],
    "fatma": ["fatima","fatimah","fatmah","fatmeh","fatemah","fatema","fatimeh"],
    "yousef": ["youssef","yousif","yusef","yusif","youssif","yosef","usif"],
    "sherif": ["shareef","shereef","sharif","shareif","sheref","sharef"],
    "fathy": ["fathi","fathii","fathie","fatthy","fathey"],
    "ali": ["aly","alee","alii","aalee","aaly"],
}

def build_replacements_pattern(rep: Dict[str, List[str]]) -> Tuple[re.Pattern, Dict[str, str]]:
    pairs = []
    for correct, wrongs in rep.items():
        for wrong in wrongs:
            pairs.append(wrong)
    pairs = sorted(set(pairs), key=len, reverse=True)
    
    reverse_map = {}
    for correct, wrongs in rep.items():
        for wrong in wrongs:
            reverse_map[wrong.lower()] = correct
    
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, pairs)) + r")\b", flags=re.I)
    return pattern, reverse_map

REPL_PAT, REPL_MAP = build_replacements_pattern(REPLACEMENTS)

def apply_replacements(text: Optional[str]) -> str:
    if not text:
        return ""
    def repl(m: re.Match) -> str:
        w = m.group(0).lower()
        return REPL_MAP[w] if w in REPL_MAP else w
    return REPL_PAT.sub(repl, text)

# =========================
# Specialty Normalization
# =========================

SPECIALTY_STOPWORDS = {
    "service","services","dept","department","unit","clinic","center","centre",
    "polyclinic","ward","opd","ipd","section","division","of"
}

SPECIALTY_CANONICAL: Dict[str, List[str]] = {
    "dental": ["dentistry","dental service","dental clinic","dent","oral","odontology"],
    "dermatology": ["derma","skin","dermatologic","dermatology clinic"],
    "ent": ["otolaryngology","ear nose throat","ent clinic","ent department"],
    "pediatrics": ["paediatrics","peds","children","child health","pediatrics clinic"],
    "gynecology & obstetrics": ["gyn","obgyn","ob/gyn","gyne","obstetrics","obstetric","ob"],
    "cardiology": ["cardio","heart","cardiac"],
    "urology": ["uro","urinary"],
    "radiology": ["imaging","xray","x-ray","radiology dept","diagnostic imaging"],
    "gastroenterology": ["gastro","gi","digestive"],
    "hepatology": ["hepa","liver"],
    "ophthalmology": ["ophtha","ophthalmic","eye","eye clinic"],
    "orthopedics": ["orthopedic","orthopaedic","ortho","bones","orthopedics clinic"],
    "nutrition": ["diet","dietary","nutrition clinic"],
    "icu": ["intensive care","critical care"],
    "er": ["emergency","a&e","casualty","ed","emergency department","accident & emergency"],
    "endoscopy": ["endoscopic","endoscopy unit"],
    "lab": ["laboratory","labs","pathology","lab services"],
    "neurology": ["neuro","nervous system"],
    "oncology": ["cancer","onco"],
    "nephrology": ["renal","kidney"],
    "endocrinology": ["endo","hormones"],
    "psychiatry": ["psych","mental health"],
    "pulmonology": ["respiratory","chest","pulmonary"],
}

SPEC_TOK_MAP = {
    "obgyn":"obgyn","ob":"obstetrics","gyn":"gyne","gi":"gastro","ent":"ent",
    "derma":"derma","ortho":"ortho","ophtha":"ophtha","x-ray":"xray","xray":"xray",
    "a&e":"er","ed":"er"
}

def _clean_specialty_text(x: str) -> str:
    txt = str(x).lower().strip() if x and not pd.isna(x) else ""
    if not txt:
        return ""
    txt = NON_WORD.sub(" ", txt)
    toks = re.split(r"[\s/,\-\_]+", txt)
    toks = [t for t in toks if t and t not in SPECIALTY_STOPWORDS]
    toks = [SPEC_TOK_MAP.get(t, t) for t in toks]
    return " ".join(toks)

def normalize_specialty(val: str) -> str:
    """تطبيع التخصصات الطبية"""
    base = _clean_specialty_text(val)
    if not base:
        return "Unknown"
    
    # مطابقة مباشرة
    for canon, syns in SPECIALTY_CANONICAL.items():
        if base == canon or base in syns:
            return canon.title()
    
    # مطابقة جزئية
    for canon, syns in SPECIALTY_CANONICAL.items():
        keys = [canon] + syns
        for k in keys:
            if re.search(rf"\b{re.escape(k)}\b", base):
                return canon.title()
    
    # Fuzzy matching للتخصصات المعقدة
    if ADVANCED_MODE:
        best, score = None, 0
        for canon, syns in SPECIALTY_CANONICAL.items():
            for k in [canon] + syns:
                sc = fuzz.partial_ratio(base, k)
                if sc > score:
                    score, best = sc, canon
        if score >= 88 and best:
            return best.title()
    
    return base.title()

# =========================
# Core Utilities
# =========================

def s(x) -> str:
    """Safe string conversion"""
    return "" if pd.isna(x) else str(x)

@lru_cache(maxsize=200_000)
def normalize_tokens(name: str, *, is_person: bool = True) -> List[str]:
    """تطبيع الرموز مع التحسينات الكاملة"""
    s_ = s(name).lower().strip()
    if not s_:
        return []
    
    # إزالة الأقواس ورموز الفروع
    s_ = BRACKETED.sub(" ", s_)
    s_ = BRANCH_CODES_REGEX.sub(" ", s_)
    s_ = TITLE_REGEX.sub(" ", s_)
    s_ = NON_WORD.sub(" ", s_)
    s_ = s_.replace("_", " ").replace(".", " ")
    s_ = MULTISPACE.sub(" ", s_).strip()
    
    # تطبيق التصحيحات
    s_ = apply_replacements(s_)
    s_ = ABD_PAT.sub("abdel", s_)
    s_ = re.sub(r"\ba\s+(?=[a-z])", "al ", s_)
    
    tokens = HYPHEN_SPLIT.split(s_)
    out: List[str] = []
    i = 0
    
    while i < len(tokens):
        t = tokens[i]
        if not t or t in DEGREE_TOKENS:
            i += 1
            continue
        if t in {"al","el"} and i + 1 < len(tokens) and tokens[i+1]:
            out.append("el" + tokens[i+1])
            i += 2
            continue
        
        t = TOKEN_MAP.get(t, t)
        if not (not is_person and out and out[-1] == t):
            out.append(t)
        i += 1
    
    return [w for w in out if len(w) > 1]

@lru_cache(maxsize=200_000)
def clean_name(name: str, *, is_person: bool = True) -> str:
    """تنظيف الأسماء مع الكاش"""
    return " ".join(normalize_tokens(name, is_person=is_person)).title()

def extract_person_name_smart(raw_text: str) -> str:
    """استخراج اسم الشخص من النص المعقد بذكاء"""
    if not raw_text or pd.isna(raw_text):
        return ""
    
    text = str(raw_text).strip()
    if not text:
        return ""
    
    # إزالة الأقواس ومحتواها
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)
    
    # إزالة علامات الترقيم
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    
    clean_words = []
    titles = {"dr", "doctor", "prof", "mr", "mrs", "ms", "miss", "md", "phd"}
    
    for word in words:
        word_lower = word.lower().strip()
        # تجاهل الألقاب والخدمات ورموز الفروع
        if word_lower in titles or word_lower in SERVICE_WORDS or word_lower in BRANCH_CODES:
            continue
        if len(word_lower) < 2 or word_lower.isdigit():
            continue
        clean_words.append(word.title())
    
    result = ' '.join(clean_words)
    return re.sub(r'\s+', ' ', result).strip()

def is_facility(name: str) -> bool:
    """تحديد ما إذا كان الاسم منشأة أم شخص"""
    n = s(name).lower().strip()
    if not n:
        return False
    
    if SERVICE_REGEX.search(n):
        return True
    
    if re.search(r"\b(clinic|centre|center|department|unit|polyclinic|hospital|ward)\b$", n):
        return True
    
    # إذا بدأ بـ Dr. لكن قصير ومافيش كلمات خدمات، يبقى شخص
    if n.startswith(("dr ", "dr.", "doctor ")):
        tok_count = len(re.findall(r"\w+", n))
        if tok_count <= 3 and not SERVICE_REGEX.search(n):
            return False
    
    return False

# =========================
# Golden Reference Management
# =========================

def _normalize_cols(cols: List[str]) -> List[str]:
    return [re.sub(r"\s+", " ", c).strip().lower().replace("_", " ") for c in cols]

def load_golden_map(path: Optional[str] = None) -> pd.DataFrame:
    """تحميل المرجع الذهبي مع دعم أعمدة متعددة والبحث الذكي"""
    
    # ✅ إذا لم يُحدد مسار، ابحث عن أفضل مرجع متاح
    if not path:
        try:
            from config import get_best_golden_reference
            base_path = Path(__file__).parent.parent  # للوصول للمجلد الأساسي
            best_ref = get_best_golden_reference(base_path)
            if best_ref:
                path = str(best_ref)
                logging.info(f"🔍 Auto-detected golden reference: {path}")
            else:
                logging.warning("⚠️ No golden reference found in any location")
                return pd.DataFrame({
                    "BI Name": pd.Series(dtype=str),
                    "Standard_Name": pd.Series(dtype=str),
                    "Original_Specialty": pd.Series(dtype=str),
                    "Alias_Clean": pd.Series(dtype=str)
                })
        except ImportError:
            # fallback إذا مافيش config module
            path = str(Path(__file__).parent / "golden_reference.xlsx")
    
    p = Path(path)
    if not p.exists():
        logging.warning(f"[Golden] File not found: {path}")
        # ✅ جرب البحث التلقائي كـ fallback
        try:
            from config import get_best_golden_reference
            base_path = Path(__file__).parent.parent
            best_ref = get_best_golden_reference(base_path)
            if best_ref and best_ref.exists():
                logging.info(f"🔄 Falling back to: {best_ref}")
                p = best_ref
            else:
                return pd.DataFrame({
                    "BI Name": pd.Series(dtype=str),
                    "Standard_Name": pd.Series(dtype=str),
                    "Original_Specialty": pd.Series(dtype=str),
                    "Alias_Clean": pd.Series(dtype=str)
                })
        except ImportError:
            return pd.DataFrame({
                "BI Name": pd.Series(dtype=str),
                "Standard_Name": pd.Series(dtype=str),
                "Original_Specialty": pd.Series(dtype=str),
                "Alias_Clean": pd.Series(dtype=str)
            })
    
    # قراءة الملف
    if p.suffix.lower() == ".csv":
        g = pd.read_csv(p, dtype=str)
    else:
        g = pd.read_excel(p, sheet_name=0, dtype=str)
    
    # تطبيع أسماء الأعمدة
    cols_norm = _normalize_cols(list(g.columns))
    g.columns = cols_norm
    
    # البحث عن الأعمدة المطلوبة
    col_map = {}
    for i, c in enumerate(cols_norm):
        if c in ("bi name","bi names"):
            col_map["BI Name"] = g.iloc[:, i]
        elif c in ("standard name","standard_name","standard names"):
            col_map["Standard_Name"] = g.iloc[:, i]
        elif c in ("original specialty","original_specialty","specialty","speciality"):
            col_map["Original_Specialty"] = g.iloc[:, i]
    
    if "BI Name" not in col_map or "Standard_Name" not in col_map:
        raise ValueError("[Golden] Expected columns not found. Include 'BI Name' and 'Standard_Name'")
    
    # بناء DataFrame منظم
    gg = pd.DataFrame({
        "BI Name": col_map["BI Name"],
        "Standard_Name": col_map["Standard_Name"],
        "Original_Specialty": col_map.get("Original_Specialty", pd.Series("", index=col_map["BI Name"].index))
    }).dropna(subset=["BI Name","Standard_Name"])
    
    gg["Alias_Clean"] = gg["BI Name"].apply(lambda x: clean_name(x, is_person=True))
    gg = gg.drop_duplicates(subset=["Alias_Clean"], keep="last")
    
    logging.info(f"[Golden] Loaded {len(gg)} records from {p}")
    return gg

def find_best_match_in_golden(extracted_name: str, golden_df: pd.DataFrame, threshold: float = 0.8) -> Tuple[Optional[str], float]:
    """العثور على أفضل مطابقة في المرجع الذهبي"""
    if not extracted_name or golden_df.empty:
        return None, 0.0
    
    # مطابقة مباشرة
    if extracted_name in golden_df['BI Name'].values:
        return extracted_name, 1.0
    
    # مطابقة مع Alias_Clean
    if 'Alias_Clean' in golden_df.columns:
        extracted_clean = clean_name(extracted_name, is_person=True)
        if extracted_clean in golden_df['Alias_Clean'].values:
            match_row = golden_df[golden_df['Alias_Clean'] == extracted_clean].iloc[0]
            return match_row['BI Name'], 1.0
    
    # Fuzzy matching إذا توفرت المكتبات المتقدمة
    if not ADVANCED_MODE:
        return None, 0.0
    
    best_match, best_score = None, 0.0
    for idx, row in golden_df.iterrows():
        score1 = fuzz.ratio(extracted_name.lower(), str(row['BI Name']).lower()) / 100.0
        score2 = 0.0
        if 'Alias_Clean' in row:
            score2 = fuzz.ratio(extracted_name.lower(), str(row['Alias_Clean']).lower()) / 100.0
        
        max_score = max(score1, score2)
        if max_score > best_score and max_score >= threshold:
            best_score = max_score
            best_match = row['BI Name']
    
    return best_match, best_score

# =========================
# Advanced Clustering (if available)
# =========================

def smart_merge_persons(df: pd.DataFrame, unsure_threshold: float = UNSURE_THRESHOLD_DEFAULT) -> pd.DataFrame:
    """دمج ذكي للأشخاص باستخدام التجميع المتقدم"""
    if not ADVANCED_MODE:
        logging.warning("[Clustering] Advanced mode not available, skipping smart merge")
        return df
    
    df = df.copy()
    df['Std_Tokens'] = df['Standard_Name'].apply(lambda s: normalize_tokens(s, is_person=True))
    df['Family_Name'] = df['Standard_Name'].apply(lambda x: x.split()[-1] if x else "")
    
    # تجميع بسيط بناءً على العائلة والطول
    def _block_key(toks: List[str]) -> Tuple[str, str, int]:
        if not toks:
            return ("", "", 0)
        first = toks[0] if toks else ""
        last = toks[-1] if toks[-1] else ""
        return (first, last, 0 if len(toks) <= 2 else (1 if len(toks) <= 4 else 2))
    
    df['Block'] = df['Std_Tokens'].apply(_block_key)
    
    # تطبيق المنطق المتقدم للدمج
    mapping: Dict[str, str] = {}
    unsure_pairs: Set[Tuple[str, str]] = set()
    
    for _, grp in df.groupby('Block', dropna=False):
        names = grp['Standard_Name'].tolist()
        toks = grp['Std_Tokens'].tolist()
        fams = [s.lower() for s in grp['Family_Name'].tolist()]
        
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                if fams[i] != fams[j] or not toks[i] or not toks[j]:
                    continue
                
                # حساب التشابه
                if ADVANCED_MODE:
                    sim = fuzz.token_set_ratio(' '.join(toks[i]), ' '.join(toks[j])) / 100.0
                else:
                    sim = len(set(toks[i]) & set(toks[j])) / len(set(toks[i]) | set(toks[j])) if toks[i] or toks[j] else 0
                
                if sim >= AUTO_MERGE_THRESHOLD:
                    # اختر الأطول أو الأكثر تفصيلاً
                    len_i, len_j = len(toks[i]), len(toks[j])
                    if len_i > len_j:
                        choose, other = names[i], names[j]
                    elif len_j > len_i:
                        choose, other = names[j], names[i]
                    else:
                        uniq_i, uniq_j = len(set(toks[i])), len(set(toks[j]))
                        choose, other = (names[i], names[j]) if uniq_i >= uniq_j else (names[j], names[i])
                    mapping[other] = choose
                elif sim >= unsure_threshold:
                    a, b = sorted((names[i], names[j]))
                    unsure_pairs.add((a, b))
    
    # تطبيق التعديلات
    if mapping:
        df['Standard_Name'] = df['Standard_Name'].replace(mapping)
    
    unsure_names: Set[str] = set([n for pair in unsure_pairs for n in pair])
    df['Not_Sure'] = df['Standard_Name'].apply(lambda x: "Not Sure" if x in unsure_names else "")
    
    return df.drop(columns=['Std_Tokens','Family_Name','Block'])

# =========================
# Main Processing Function
# =========================

def process_file(
    input_path: str,
    output_path: str,
    golden_path: Optional[str] = None,
    new_aliases_out: Optional[str] = None,
    threshold: Optional[float] = None,
) -> None:
    """المعالجة الرئيسية المحسنة والموحدة"""
    
    t0 = time.time()
    threshold = threshold or UNSURE_THRESHOLD_DEFAULT
    
    logging.info("=" * 60)
    logging.info("🚀 STARTING ENHANCED DOCTOR PROCESSING")
    logging.info(f"📁 Input: {input_path}")
    logging.info(f"📁 Output: {output_path}")
    logging.info(f"📁 Golden: {golden_path or 'auto-detect'}")
    logging.info(f"🎯 Threshold: {threshold}")
    logging.info(f"🔧 Advanced Mode: {'✅ ENABLED' if ADVANCED_MODE else '❌ BASIC'}")
    logging.info("=" * 60)
    
    # قراءة البيانات
    logging.info("📖 Loading input data...")
    df = pd.read_excel(input_path, dtype=str)
    
    if "BI Name" not in df.columns:
        raise ValueError("Input file must contain column 'BI Name'.")
    
    logging.info(f"📊 Loaded {len(df)} records")
    
    # ✅ تحميل المرجع الذهبي مع البحث الذكي
    golden = load_golden_map(golden_path)  # سيبحث تلقائياً لو مافيش path محدد
    
    # معالجة التخصصات
    if 'Specialty' in df.columns:
        df['Original_Specialty'] = df['Specialty']
        df['Specialty_Std'] = df['Specialty'].apply(normalize_specialty)
        logging.info("🏥 Processed specialty information")
    else:
        df['Original_Specialty'] = ""
        df['Specialty_Std'] = "Unknown"
    
    # تصنيف الكيانات (أشخاص vs منشآت)
    logging.info("🔍 Classifying entities (persons vs facilities)...")
    df['Entity_Type'] = df['BI Name'].apply(lambda x: "facility" if is_facility(x) else "person")
    
    persons = df[df['Entity_Type']=="person"].copy()
    facilities = df[df['Entity_Type']=="facility"].copy()
    
    logging.info(f"👥 Found {len(persons)} persons, 🏢 {len(facilities)} facilities")
    
    # معالجة الأشخاص
    if not persons.empty:
        logging.info("🧠 Processing persons with smart extraction...")
        
        # استخراج الأسماء الذكي
        persons['Extracted_Name'] = persons['BI Name'].apply(extract_person_name_smart)
        persons['Cleaned_Name'] = persons['Extracted_Name'].apply(lambda x: clean_name(x, is_person=True))
        
        # عرض أمثلة على الاستخراج
        examples = persons[persons['BI Name'] != persons['Extracted_Name']].head(5)
        if not examples.empty:
            logging.info("💡 Smart extraction examples:")
            for idx, row in examples.iterrows():
                logging.info(f"   '{row['BI Name']}' → '{row['Extracted_Name']}'")
        
        # مطابقة مع المرجع الذهبي
        if not golden.empty:
            logging.info("🎯 Matching with golden reference...")
            persons['Golden_Match'] = ""
            persons['Match_Score'] = 0.0
            persons['Standard_Name'] = ""
            
            # مطابقة مباشرة
            golden_direct_map = dict(zip(golden['BI Name'], golden['Standard_Name']))
            direct_matches = persons['BI Name'].map(golden_direct_map)
            direct_mask = direct_matches.notna()
            
            persons.loc[direct_mask, 'Standard_Name'] = direct_matches[direct_mask]
            persons.loc[direct_mask, 'Golden_Match'] = persons.loc[direct_mask, 'BI Name']
            persons.loc[direct_mask, 'Match_Score'] = 1.0
            
            # مطابقة ذكية للباقي
            no_direct_match = ~direct_mask
            if no_direct_match.any():
                for idx in persons[no_direct_match].index:
                    extracted = persons.at[idx, 'Extracted_Name']
                    if extracted:
                        match, score = find_best_match_in_golden(extracted, golden, threshold=0.8)
                        if match:
                            persons.at[idx, 'Golden_Match'] = match
                            persons.at[idx, 'Match_Score'] = score
                            golden_row = golden[golden['BI Name'] == match].iloc[0]
                            persons.at[idx, 'Standard_Name'] = golden_row['Standard_Name']
                        else:
                            persons.at[idx, 'Standard_Name'] = extracted or persons.at[idx, 'BI Name']
            
            matched_count = (persons['Golden_Match'] != "").sum()
            logging.info(f"🎯 Golden matches: {matched_count}/{len(persons)} ({matched_count/len(persons)*100:.1f}%)")
        else:
            persons['Standard_Name'] = persons['Cleaned_Name']
        
        # التجميع الذكي للأسماء غير المطابقة
        if ADVANCED_MODE and not golden.empty:
            has_ref = (persons['Golden_Match'] != "") if 'Golden_Match' in persons.columns else pd.Series(False, index=persons.index)
            missing_mask = ~has_ref
            
            if missing_mask.any():
                logging.info(f"🔗 Smart clustering for {missing_mask.sum()} unmatched names...")
                persons = smart_merge_persons(persons, unsure_threshold=threshold)
        
        # تحديد الأسماء المتغيرة
        persons['Name_Changed'] = persons['BI Name'] != persons['Standard_Name']
        
    # معالجة المنشآت
    if not facilities.empty:
        logging.info("🏢 Processing facilities...")
        facilities['Standard_Name'] = facilities['BI Name'].apply(lambda x: clean_name(x, is_person=False))
        facilities['Name_Changed'] = facilities['BI Name'] != facilities['Standard_Name']
    
    # تصدير الأسماء الجديدة للمراجعة
    try:
        if not golden.empty:
            known_names = set(golden['BI Name'].unique())
            new_aliases = persons[~persons['BI Name'].isin(known_names)][
                ['BI Name','Extracted_Name','Original_Specialty','Standard_Name']
            ].drop_duplicates()
        else:
            new_aliases = persons[['BI Name','Extracted_Name','Original_Specialty','Standard_Name']].drop_duplicates()
        
        if len(new_aliases) > 0:
            new_out = new_aliases_out or DEFAULT_NEW_ALIASES
            Path(new_out).parent.mkdir(parents=True, exist_ok=True)
            new_aliases['Unsure'] = "Not Sure"
            new_aliases.to_excel(new_out, index=False)
            logging.info(f"📝 New aliases for review: {len(new_aliases)} → {new_out}")
    except Exception as e:
        logging.warning(f"⚠️ Could not write new aliases file: {e}")
    
    # حفظ النتائج
    logging.info("💾 Saving results...")
    
    # تنسيق أعمدة الأشخاص
    person_cols = ['BI Name','Extracted_Name','Original_Specialty','Specialty_Std','Standard_Name','Name_Changed']
    if 'Golden_Match' in persons.columns:
        person_cols.insert(-1, 'Golden_Match')
    if 'Match_Score' in persons.columns:
        person_cols.insert(-1, 'Match_Score')
    if 'Not_Sure' in persons.columns:
        person_cols.append('Not_Sure')
    
    # تأكد من وجود كل الأعمدة
    for col in person_cols:
        if col not in persons.columns:
            persons[col] = ""
    
    # كتابة النتائج
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if not persons.empty:
            persons[person_cols].to_excel(writer, sheet_name="Doctors", index=False)
        if not facilities.empty:
            facilities[['BI Name','Standard_Name','Name_Changed']].to_excel(writer, sheet_name="Facilities", index=False)
    
    # إحصائيات نهائية
    t1 = time.time()
    unique_before = persons['BI Name'].nunique(dropna=True) if not persons.empty else 0
    unique_after = persons['Standard_Name'].nunique(dropna=True) if not persons.empty else 0
    reduction = (unique_before - unique_after) / unique_before * 100 if unique_before else 0.0
    changed_ratio = (persons['Name_Changed']).mean() * 100 if not persons.empty else 0.0
    
    logging.info("=" * 60)
    logging.info("📊 PROCESSING COMPLETE")
    logging.info(f"👥 Persons: {len(persons)}")
    logging.info(f"🏢 Facilities: {len(facilities)}")
    logging.info(f"🔄 Unique names before: {unique_before}")
    logging.info(f"🎯 Unique names after: {unique_after}")
    logging.info(f"📉 Reduction: {reduction:.1f}%")
    logging.info(f"✏️ Names changed: {changed_ratio:.1f}%")
    logging.info(f"⏱️ Processing time: {t1-t0:.2f}s")
    logging.info("=" * 60)

# =========================
# Golden Reference Learning
# =========================

def update_golden_from_review(base_golden_path: str, reviewed_path: str, out_path: Optional[str] = None) -> str:
    """تحديث المرجع الذهبي من الملفات المراجعة"""
    logging.info("📚 Updating golden reference from reviewed data...")
    
    # تحميل المرجع الأساسي
    base = load_golden_map(base_golden_path)
    if base.empty:
        base = pd.DataFrame({
            "BI Name": pd.Series(dtype=str),
            "Standard_Name": pd.Series(dtype=str),
            "Original_Specialty": pd.Series(dtype=str)
        })
    
    # تحميل الملف المراجع
    if reviewed_path.lower().endswith(".csv"):
        rev = pd.read_csv(reviewed_path, dtype=str)
    else:
        try:
            rev = pd.read_excel(reviewed_path, sheet_name="Doctors", dtype=str)
        except Exception:
            rev = pd.read_excel(reviewed_path, dtype=str)
    
    # تطبيع أسماء الأعمدة
    cols_lc = {c.lower().strip(): c for c in rev.columns}
    required = ["bi name", "standard_name"]
    
    if not all(col in cols_lc for col in required):
        raise ValueError("Reviewed file must contain 'BI Name' and 'Standard_Name' columns.")
    
    # استخراج البيانات المطلوبة
    rev_data = {
        "BI Name": rev[cols_lc["bi name"]],
        "Standard_Name": rev[cols_lc["standard_name"]]
    }
    
    # إضافة التخصص إذا وُجد
    specialty_cols = [c for c in cols_lc.keys() if any(x in c for x in ["specialty", "speciality", "department"])]
    if specialty_cols:
        rev_data["Original_Specialty"] = rev[cols_lc[specialty_cols[0]]]
    else:
        rev_data["Original_Specialty"] = ""
    
    rev_df = pd.DataFrame(rev_data).dropna(subset=["BI Name","Standard_Name"])
    rev_df["Alias_Clean"] = rev_df["BI Name"].apply(lambda x: clean_name(x, is_person=True))
    
    # دمج البيانات
    keep_cols = ["BI Name","Standard_Name","Original_Specialty","Alias_Clean"]
    base_clean = base[keep_cols] if not base.empty else pd.DataFrame(columns=keep_cols)
    
    merged = pd.concat([base_clean, rev_df[keep_cols]], ignore_index=True)
    merged = merged.sort_values(by="Alias_Clean").drop_duplicates(subset=["Alias_Clean"], keep="last")
    
    # حفظ النتائج
    target = out_path or base_golden_path
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    merged[keep_cols].to_excel(target, index=False)
    
    logging.info(f"✅ Golden reference updated: {target} ({len(merged)} records)")
    return target

# =========================
# Pipeline Integration
# =========================

@dataclass
class ProcessRequest:
    input_path: Path
    output_path: Path
    golden_path: Optional[Path]
    new_aliases_out: Optional[Path]
    threshold: float = UNSURE_THRESHOLD_DEFAULT

def run_processing(req: ProcessRequest) -> None:
    """Wrapper للتوافق مع pipeline الموجود"""
    process_file(
        input_path=str(req.input_path),
        output_path=str(req.output_path),
        golden_path=str(req.golden_path) if req.golden_path else None,
        new_aliases_out=str(req.new_aliases_out) if req.new_aliases_out else None,
        threshold=req.threshold,
    )

def learn_from_review(golden_path: Path, reviewed_path: Path, out_path: Optional[Path] = None) -> Path:
    """Wrapper للتوافق مع pipeline الموجود"""
    result = update_golden_from_review(
        base_golden_path=str(golden_path),
        reviewed_path=str(reviewed_path),
        out_path=str(out_path) if out_path else None
    )
    return Path(result)

# =========================
# Command Line Interface
# =========================

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Enhanced Doctors Name Processing with Smart Extraction & Golden Learning")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Process command
    sp = sub.add_parser("process", help="Process doctors list with smart name extraction")
    sp.add_argument("--input", required=True, help="Input Excel file path")
    sp.add_argument("--output", required=True, help="Output Excel file path")
    sp.add_argument("--golden", default=None, help="Golden reference Excel/CSV path (auto-detected if not provided)")
    sp.add_argument("--new-aliases-out", default=DEFAULT_NEW_ALIASES, help="Where to write new/unmapped aliases")
    sp.add_argument("--threshold", type=float, default=UNSURE_THRESHOLD_DEFAULT, help="Similarity threshold for matching")

    # Learn command
    sl = sub.add_parser("learn", help="Update golden reference from reviewed output")
    sl.add_argument("--golden", required=True, help="Base golden reference path to update")
    sl.add_argument("--reviewed", required=True, help="Reviewed file (must include BI Name + Standard_Name)")
    sl.add_argument("--out", help="Optional output path for the updated golden (defaults to --golden)")

    return p

def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.cmd == "process":
        process_file(
            input_path=args.input,
            output_path=args.output,
            golden_path=args.golden,  # سيبحث تلقائياً لو None
            new_aliases_out=args.new_aliases_out,
            threshold=args.threshold,
        )
    elif args.cmd == "learn":
        update_golden_from_review(
            base_golden_path=args.golden,
            reviewed_path=args.reviewed,
            out_path=args.out,
        )

if __name__ == "__main__":
    main()
