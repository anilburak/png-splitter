import pandas as pd


def export_results(path, raw, machines):
    pattern = raw.groupby("pattern_no", dropna=False)["required_hours"].sum().reset_index()
    parts = raw.groupby(["part_no", "part_name"], dropna=False)["required_hours"].sum().reset_index()
    overloaded = machines[machines["usage_percent"] >= 100]
    summary = pd.DataFrame({"Gösterge": ["Toplam gerekli saat", "Makine sayısı", "Kapasite aşımı"], "Değer": [round(raw.required_hours.sum(), 2), machines.machine.nunique(), len(overloaded)]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary.to_excel(writer, "Genel Özet", index=False)
        machines.to_excel(writer, "Makine Bazlı Kapasite", index=False)
        pattern.to_excel(writer, "Pattern Bazlı İş Yükü", index=False)
        parts.to_excel(writer, "Parça Bazlı İş Yükü", index=False)
        overloaded.to_excel(writer, "Kapasite Aşımı Olanlar", index=False)
        raw.to_excel(writer, "Ham Veri", index=False)
