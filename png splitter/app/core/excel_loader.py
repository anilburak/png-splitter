import re
import pandas as pd

FIELDS = {
    "part_no": ["parca no", "parca kodu", "part no", "part number"],
    "part_name": ["parca adi", "parca adı", "part name", "urun adi"],
    "pattern_no": ["pattern kalip no", "pattern no", "kalip no", "kalıp no", "pattern"],
    "machine": ["makine pres", "makine", "pres", "machine"],
    "quantity": ["aylik uretim adedi", "aylık üretim adedi", "uretim adedi", "adet", "quantity"],
    "cycle_seconds": ["cevrim suresi sn", "çevrim süresi sn", "parca basi sure sn", "süre sn", "cycle time"]
}
LABELS = {"part_no":"Parça No", "part_name":"Parça Adı", "pattern_no":"Pattern / Kalıp No", "machine":"Makine / Pres", "quantity":"Aylık Üretim Adedi", "cycle_seconds":"Çevrim Süresi (sn)"}


def normalize(value):
    table = str.maketrans("çğıöşüİÇĞIÖŞÜ", "cgiosuICGIOSU")
    return re.sub(r"[^a-z0-9]+", " ", str(value).translate(table).lower()).strip()


def detect_columns(columns):
    normalized = {c: normalize(c) for c in columns}
    mapping = {}
    for key, aliases in FIELDS.items():
        candidates = [normalize(x) for x in aliases]
        for original, clean in normalized.items():
            if clean in candidates or any(a in clean for a in candidates):
                mapping[key] = original
                break
    return mapping


def load_excel(path):
    frame = pd.read_excel(path)
    if frame.empty:
        raise ValueError("Excel dosyasında veri bulunamadı.")
    mapping = detect_columns(frame.columns)
    missing = [LABELS[k] for k in FIELDS if k not in mapping]
    if missing:
        raise ValueError("Eksik veya tanınamayan kolonlar: " + ", ".join(missing))
    result = frame.rename(columns={v: k for k, v in mapping.items()})[list(FIELDS)]
    for key in ("quantity", "cycle_seconds"):
        result[key] = pd.to_numeric(result[key], errors="coerce")
    bad = result[["quantity", "cycle_seconds"]].isna().any(axis=1)
    if bad.any():
        rows = ", ".join(str(i + 2) for i in result.index[bad][:8])
        raise ValueError(f"Sayısal olmayan adet veya süre var. Excel satırları: {rows}")
    return result
