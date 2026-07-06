from datetime import date
from pathlib import Path
import pandas as pd
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QBrush, QColor, QPalette, QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QSpinBox, QCheckBox, QDateEdit, QListWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QFrame, QAbstractItemView)
from app.core.excel_loader import load_excel, LABELS
from app.core.calendar_utils import working_days
from app.core.capacity_calculator import calculate
from app.core.export_excel import export_results
from app.core.template_generator import create_data_template


STYLE = """
QWidget { color:#f4f7fb; font-family:'Segoe UI'; font-size:13px; }
QFrame#panel { background:rgba(7,17,31,220); border:1px solid rgba(239,51,64,90); border-radius:16px; }
QLabel#title { font-size:28px; font-weight:800; color:#ffffff; }
QLabel#subtitle { color:#9bb0c8; font-size:12px; }
QLabel#metric { font-size:23px; font-weight:700; color:#ef3340; }
QPushButton { background:#c9182b; border:1px solid #ef4a58; border-radius:9px; padding:9px 16px; font-weight:650; }
QPushButton:hover { background:#ef3340; }
QPushButton:disabled { background:#253449; color:#74849a; border-color:#34475e; }
QComboBox,QSpinBox,QDateEdit,QListWidget,QTableWidget { background:rgba(9,25,44,235); border:1px solid #334860; border-radius:7px; padding:5px; selection-background-color:#b82032; }
QHeaderView::section { background:#14263c; color:#dce7f2; padding:8px; border:0; border-right:1px solid #263a51; font-weight:600; }
QTableWidget { gridline-color:#20364e; alternate-background-color:rgba(17,39,62,220); }
QCheckBox::indicator { width:17px; height:17px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pattern Sentinel • Pres Kapasite Planlama")
        self.resize(1380, 820)
        self.data = None
        self.calculated = None
        self.results = None
        self._build()
        self.setStyleSheet(STYLE)
        self._set_background()

    def _set_background(self):
        path = Path(__file__).resolve().parents[1] / "assets" / "spider_industry_bg.png"
        pix = QPixmap(str(path))
        pal = self.palette()
        pal.setBrush(QPalette.Window, QBrush(pix.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)))
        self.setPalette(pal)

    def resizeEvent(self, event):
        self._set_background()
        super().resizeEvent(event)

    def panel(self):
        frame = QFrame(objectName="panel")
        frame.setLayout(QVBoxLayout())
        return frame

    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(28, 22, 28, 24); outer.setSpacing(14)
        head = QHBoxLayout()
        titles = QVBoxLayout(); title = QLabel("PATTERN SENTINEL", objectName="title"); titles.addWidget(title)
        titles.addWidget(QLabel("PRES PATTERN PLANLAMA  /  KAPASİTE KONTROL MERKEZİ", objectName="subtitle"))
        head.addLayout(titles); head.addStretch()
        self.file_label = QLabel("Henüz veri yüklenmedi", objectName="subtitle"); head.addWidget(self.file_label)
        load = QPushButton("⚡  EXCEL YÜKLE"); load.clicked.connect(self.open_excel); head.addWidget(load)
        self.template_button = QPushButton("↓  BOŞ VERİ ŞABLONU İNDİR")
        self.template_button.setObjectName("templateButton")
        self.template_button.setToolTip("Örnek veriler içeren Excel şablonunu bilgisayarınıza kaydedin")
        self.template_button.clicked.connect(self.download_template)
        head.addWidget(self.template_button)
        outer.addLayout(head)

        body = QHBoxLayout(); body.setSpacing(14); outer.addLayout(body, 1)
        controls = self.panel(); controls.setFixedWidth(310); body.addWidget(controls)
        controls.layout().addWidget(QLabel("OPERASYON AYARLARI", objectName="subtitle"))
        self.month = QComboBox(); self.month.addItems(["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]); self.month.setCurrentIndex(date.today().month-1)
        self.year = QSpinBox(); self.year.setRange(2020, 2100); self.year.setValue(date.today().year)
        row = QHBoxLayout(); row.addWidget(self.month); row.addWidget(self.year); controls.layout().addLayout(row)
        controls.layout().addWidget(QLabel("Vardiya kapasitesi"))
        self.shift = QComboBox(); self.shift.addItem("1 vardiya  •  7,16 saat", 7.16); self.shift.addItem("2 vardiya  •  14,32 saat", 14.32); controls.layout().addWidget(self.shift)
        self.saturday = QCheckBox("Cumartesi çalışıyor"); self.sunday = QCheckBox("Pazar çalışıyor"); controls.layout().addWidget(self.saturday); controls.layout().addWidget(self.sunday)
        controls.layout().addWidget(QLabel("Tatil / çalışma dışı gün"))
        holiday_row = QHBoxLayout(); self.holiday_date = QDateEdit(QDate.currentDate()); self.holiday_date.setCalendarPopup(True); holiday_row.addWidget(self.holiday_date)
        add_h = QPushButton("+"); add_h.setFixedWidth(38); add_h.clicked.connect(self.add_holiday); holiday_row.addWidget(add_h); controls.layout().addLayout(holiday_row)
        self.holidays = QListWidget(); self.holidays.setMaximumHeight(90); self.holidays.itemDoubleClicked.connect(lambda i: self.holidays.takeItem(self.holidays.row(i))); controls.layout().addWidget(self.holidays)
        self.calc_btn = QPushButton("HESAPLA"); self.calc_btn.setEnabled(False); self.calc_btn.clicked.connect(self.run_calculation); controls.layout().addWidget(self.calc_btn)
        self.export_btn = QPushButton("SONUÇLARI EXCEL'E AKTAR"); self.export_btn.setEnabled(False); self.export_btn.clicked.connect(self.export); controls.layout().addWidget(self.export_btn)
        controls.layout().addStretch(); controls.layout().addWidget(QLabel("İpucu: Tatili silmek için çift tıklayın.", objectName="subtitle"))

        right = QVBoxLayout(); body.addLayout(right, 1)
        metrics = QHBoxLayout(); self.days_card, self.days_value = self.metric("ÇALIŞMA GÜNÜ", "—"); self.hours_card, self.hours_value = self.metric("AYLIK KAPASİTE", "—"); self.load_card, self.load_value = self.metric("TOPLAM İŞ YÜKÜ", "—")
        metrics.addWidget(self.days_card); metrics.addWidget(self.hours_card); metrics.addWidget(self.load_card); right.addLayout(metrics)
        table_panel = self.panel(); right.addWidget(table_panel, 1)
        top = QHBoxLayout(); top.addWidget(QLabel("MAKİNE BAZLI KAPASİTE RADARI", objectName="subtitle")); top.addStretch(); self.status = QLabel("Veri bekleniyor", objectName="subtitle"); top.addWidget(self.status); table_panel.layout().addLayout(top)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Makine / Pres", "Gerekli Saat", "Kapasite", "Kullanım", "Durum"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setAlternatingRowColors(True); table_panel.layout().addWidget(self.table)

    def metric(self, name, value):
        card = self.panel(); card.layout().addWidget(QLabel(name, objectName="subtitle")); label = QLabel(value, objectName="metric"); card.layout().addWidget(label); return card, label

    def add_holiday(self):
        text = self.holiday_date.date().toString("yyyy-MM-dd")
        if not self.holidays.findItems(text, Qt.MatchExactly): self.holidays.addItem(text)

    def open_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Üretim planını seç", "", "Excel (*.xlsx *.xls)")
        if not path: return
        try:
            self.data = load_excel(path); self.file_label.setText(Path(path).name); self.calc_btn.setEnabled(True); self.status.setText(f"{len(self.data)} satır hazır")
        except Exception as exc: QMessageBox.critical(self, "Excel okunamadı", str(exc))

    def download_template(self, checked=False):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Boş Veri Şablonunu Kaydet",
            "pres_pattern_veri_sablonu.xlsx",
            "Excel Dosyası (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            create_data_template(path)
            QMessageBox.information(
                self,
                "Başarılı",
                f"Şablon başarıyla kaydedildi:\n{path}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Hata",
                f"Şablon oluşturulurken hata oluştu:\n{exc}",
            )

    def run_calculation(self):
        holiday_dates = [date.fromisoformat(self.holidays.item(i).text()) for i in range(self.holidays.count())]
        days = working_days(self.year.value(), self.month.currentIndex()+1, self.saturday.isChecked(), self.sunday.isChecked(), holiday_dates)
        daily = self.shift.currentData(); self.calculated, self.results = calculate(self.data, days, daily)
        self.days_value.setText(str(days)); self.hours_value.setText(f"{days*daily:.1f} sa"); self.load_value.setText(f"{self.calculated.required_hours.sum():.1f} sa")
        self.table.setRowCount(len(self.results))
        for row, item in self.results.iterrows():
            values = [str(item.machine), f"{item.required_hours:.2f}", f"{item.capacity_hours:.2f}", f"%{item.usage_percent:.1f}", item.status]
            color = QColor("#39d98a" if item.status == "Uygun" else "#ffc857" if item.status == "Riskli" else "#ff4358")
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value); cell.setTextAlignment(Qt.AlignCenter); self.table.setItem(row, col, cell)
            self.table.item(row, 4).setForeground(color)
        overloaded = int((self.results.usage_percent >= 100).sum()); self.status.setText(f"{overloaded} kapasite aşımı • {len(self.results)} makine"); self.export_btn.setEnabled(True)

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sonuçları kaydet", "kapasite_sonuclari.xlsx", "Excel (*.xlsx)")
        if not path: return
        try: export_results(path, self.calculated, self.results); QMessageBox.information(self, "Tamamlandı", "Kapasite raporu başarıyla oluşturuldu.")
        except Exception as exc: QMessageBox.critical(self, "Dışa aktarma hatası", str(exc))
