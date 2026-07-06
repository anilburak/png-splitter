import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk


INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


class PNGSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG Splitter")
        self.root.geometry("1180x760")
        self.root.minsize(900, 620)

        self.image = None
        self.image_path = None
        self.preview_photo = None
        self.preview_scale = 1.0
        self.preview_x = self.preview_y = 0
        self.vertical_lines = []
        self.horizontal_lines = []
        self.output_dir = tk.StringVar()
        self.cut_mode = tk.StringVar(value="manual")
        self.line_mode = tk.StringVar(value="vertical")
        self.rows = tk.IntVar(value=1)
        self.cols = tk.IntVar(value=1)
        self.name_vars = []
        self.presets = {}
        self.preset_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "name_presets.json")

        self._build_ui()
        self._load_presets_file()
        self.root.after(100, self.update_name_table)

    def _build_ui(self):
        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Görsel Yükle", command=self.load_image).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Çıktı Klasörü", command=self.choose_output_dir).pack(side="left", padx=3)
        ttk.Entry(toolbar, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(toolbar, text="PNG'leri Oluştur", command=self.split_image).pack(side="right", padx=3)

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(body)
        right = ttk.Frame(body, width=360)
        body.add(left, weight=3)
        body.add(right, weight=2)

        modes = ttk.LabelFrame(left, text="Kesme Ayarları", padding=7)
        modes.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(modes, text="Manuel çizgi", variable=self.cut_mode, value="manual",
                        command=self.mode_changed).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(modes, text="Grid", variable=self.cut_mode, value="grid",
                        command=self.mode_changed).grid(row=0, column=1, sticky="w", padx=(12, 0))

        self.manual_frame = ttk.Frame(modes)
        self.manual_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Radiobutton(self.manual_frame, text="Dikey çizgi ekle", variable=self.line_mode,
                        value="vertical").pack(side="left")
        ttk.Radiobutton(self.manual_frame, text="Yatay çizgi ekle", variable=self.line_mode,
                        value="horizontal").pack(side="left", padx=8)
        ttk.Button(self.manual_frame, text="Son çizgiyi sil", command=self.delete_last_line).pack(side="left", padx=3)
        ttk.Button(self.manual_frame, text="Tüm çizgileri temizle", command=self.clear_lines).pack(side="left", padx=3)

        self.grid_frame = ttk.Frame(modes)
        ttk.Label(self.grid_frame, text="Satır:").pack(side="left")
        row_spin = ttk.Spinbox(self.grid_frame, from_=1, to=999, width=6, textvariable=self.rows,
                               command=self.update_name_table)
        row_spin.pack(side="left", padx=(3, 12))
        ttk.Label(self.grid_frame, text="Sütun:").pack(side="left")
        col_spin = ttk.Spinbox(self.grid_frame, from_=1, to=999, width=6, textvariable=self.cols,
                               command=self.update_name_table)
        col_spin.pack(side="left", padx=3)
        row_spin.bind("<KeyRelease>", lambda _e: self.update_name_table())
        col_spin.bind("<KeyRelease>", lambda _e: self.update_name_table())

        canvas_box = ttk.LabelFrame(left, text="Önizleme (çizgi eklemek için görsele tıklayın)", padding=4)
        canvas_box.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_box, background="#303030", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.canvas_click)
        self.canvas.bind("<Configure>", lambda _e: self.root.after_idle(self.render_preview))

        names = ttk.LabelFrame(right, text="Dosya İsimleri", padding=7)
        names.pack(fill="both", expand=True)
        preset_bar = ttk.Frame(names)
        preset_bar.pack(fill="x", pady=(0, 6))
        self.preset_combo = ttk.Combobox(preset_bar, state="readonly")
        self.preset_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(preset_bar, text="Preset yükle", command=self.load_selected_preset).pack(side="left", padx=(5, 0))
        ttk.Button(names, text="İsim listesini kaydet", command=self.save_preset).pack(fill="x", pady=(0, 6))

        header = ttk.Frame(names)
        header.pack(fill="x")
        ttk.Label(header, text="Sıra No", width=10).pack(side="left")
        ttk.Label(header, text="Dosya Adı").pack(side="left", fill="x", expand=True)

        table_wrap = ttk.Frame(names)
        table_wrap.pack(fill="both", expand=True)
        self.names_canvas = tk.Canvas(table_wrap, highlightthickness=0)
        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.names_canvas.yview)
        self.names_inner = ttk.Frame(self.names_canvas)
        self.names_window = self.names_canvas.create_window((0, 0), window=self.names_inner, anchor="nw")
        self.names_canvas.configure(yscrollcommand=scrollbar.set)
        self.names_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.names_inner.bind("<Configure>", lambda _e: self.names_canvas.configure(
            scrollregion=self.names_canvas.bbox("all")))
        self.names_canvas.bind("<Configure>", lambda e: self.names_canvas.itemconfigure(
            self.names_window, width=e.width))

        self.status = tk.StringVar(value="Bir PNG veya JPG görsel yükleyin.")
        ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w", padding=4).pack(fill="x")
        self.mode_changed()

    def mode_changed(self):
        if self.cut_mode.get() == "manual":
            self.grid_frame.grid_forget()
            self.manual_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        else:
            self.manual_frame.grid_forget()
            self.grid_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        self.render_preview()
        self.update_name_table()

    def load_image(self):
        path = filedialog.askopenfilename(title="Görsel seçin",
            filetypes=[("Görseller", "*.png *.jpg *.jpeg"), ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")])
        if not path:
            return
        try:
            with Image.open(path) as source:
                self.image = source.copy()
            self.image_path = path
            self.vertical_lines.clear()
            self.horizontal_lines.clear()
            self.status.set(f"Yüklendi: {os.path.basename(path)} — {self.image.width} × {self.image.height} px")
            self.render_preview()
            self.update_name_table()
        except Exception as exc:
            messagebox.showerror("Görsel açılamadı", f"Görsel yüklenirken hata oluştu:\n{exc}")

    def choose_output_dir(self):
        path = filedialog.askdirectory(title="Çıktı klasörünü seçin")
        if path:
            self.output_dir.set(path)

    def render_preview(self):
        self.canvas.delete("all")
        if self.image is None:
            self.canvas.create_text(max(1, self.canvas.winfo_width()) / 2,
                                    max(1, self.canvas.winfo_height()) / 2,
                                    text="Henüz görsel yüklenmedi", fill="white", font=("Segoe UI", 14))
            return
        cw, ch = max(10, self.canvas.winfo_width()), max(10, self.canvas.winfo_height())
        self.preview_scale = min(cw / self.image.width, ch / self.image.height, 1.0)
        pw = max(1, round(self.image.width * self.preview_scale))
        ph = max(1, round(self.image.height * self.preview_scale))
        preview = self.image.resize((pw, ph), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(preview)
        self.preview_x, self.preview_y = (cw - pw) / 2, (ch - ph) / 2
        self.canvas.create_image(self.preview_x, self.preview_y, image=self.preview_photo, anchor="nw")
        if self.cut_mode.get() == "manual":
            for x in self.vertical_lines:
                px = self.preview_x + x * self.preview_scale
                self.canvas.create_line(px, self.preview_y, px, self.preview_y + ph, fill="red", width=2)
            for y in self.horizontal_lines:
                py = self.preview_y + y * self.preview_scale
                self.canvas.create_line(self.preview_x, py, self.preview_x + pw, py, fill="red", width=2)

    def canvas_click(self, event):
        if self.image is None or self.cut_mode.get() != "manual":
            return
        ox = round((event.x - self.preview_x) / self.preview_scale)
        oy = round((event.y - self.preview_y) / self.preview_scale)
        if not (0 <= ox < self.image.width and 0 <= oy < self.image.height):
            return
        if self.line_mode.get() == "vertical":
            if 0 < ox < self.image.width and ox not in self.vertical_lines:
                self.vertical_lines.append(ox)
                self.vertical_lines.sort()
        else:
            if 0 < oy < self.image.height and oy not in self.horizontal_lines:
                self.horizontal_lines.append(oy)
                self.horizontal_lines.sort()
        self.render_preview()
        self.update_name_table()

    def delete_last_line(self):
        lines = self.vertical_lines if self.line_mode.get() == "vertical" else self.horizontal_lines
        if lines:
            lines.pop()
            self.render_preview()
            self.update_name_table()

    def clear_lines(self):
        self.vertical_lines.clear()
        self.horizontal_lines.clear()
        self.render_preview()
        self.update_name_table()

    def get_dimensions(self):
        if self.cut_mode.get() == "manual":
            return len(self.horizontal_lines) + 1, len(self.vertical_lines) + 1
        try:
            rows, cols = int(self.rows.get()), int(self.cols.get())
            if rows < 1 or cols < 1:
                raise ValueError
            return rows, cols
        except (ValueError, tk.TclError):
            return 0, 0

    def update_name_table(self, names=None):
        existing = [var.get() for var in self.name_vars]
        if names is not None:
            existing = names
        rows, cols = self.get_dimensions()
        count = rows * cols
        for widget in self.names_inner.winfo_children():
            widget.destroy()
        self.name_vars = []
        for i in range(count):
            r, c = divmod(i, cols)
            default = f"split_r{r + 1:02d}_c{c + 1:02d}"
            value = existing[i] if i < len(existing) else ""
            var = tk.StringVar(value=value)
            self.name_vars.append(var)
            ttk.Label(self.names_inner, text=str(i + 1), width=10).grid(row=i, column=0, sticky="w", pady=1)
            entry = ttk.Entry(self.names_inner, textvariable=var)
            entry.grid(row=i, column=1, sticky="ew", pady=1)
            entry.configure(validate="focusout", validatecommand=(self.root.register(
                lambda v, d=default: self._clean_entry(v, d)), "%P"))
        self.names_inner.columnconfigure(1, weight=1)
        self.status.set(f"{count} parça oluşturulacak." if count else "Satır ve sütun değerleri geçerli olmalı.")

    def _clean_entry(self, value, _default):
        cleaned = INVALID_FILENAME_CHARS.sub("", value).strip()
        if cleaned != value:
            self.root.after_idle(lambda: messagebox.showwarning(
                "Geçersiz karakter", 'Dosya adındaki \\ / : * ? " < > | karakterleri kullanılamaz.'))
        return True

    def _resolved_names(self, rows, cols):
        result, seen = [], set()
        for i, var in enumerate(self.name_vars):
            r, c = divmod(i, cols)
            default = f"split_r{r + 1:02d}_c{c + 1:02d}"
            raw = var.get().strip()
            name = INVALID_FILENAME_CHARS.sub("", raw).strip()
            if name.lower().endswith(".png"):
                name = name[:-4].rstrip()
            name = name or default
            if name.lower() in seen:
                raise ValueError(f'"{name}" dosya adı birden fazla kullanılmış.')
            seen.add(name.lower())
            result.append(name + ".png")
        return result

    def split_image(self):
        if self.image is None:
            messagebox.showerror("Görsel yok", "Önce bir PNG veya JPG görsel yükleyin.")
            return
        output = self.output_dir.get().strip()
        if not output or not os.path.isdir(output):
            messagebox.showerror("Klasör seçilmedi", "Geçerli bir çıktı klasörü seçin.")
            return
        rows, cols = self.get_dimensions()
        if rows < 1 or cols < 1:
            messagebox.showerror("Geçersiz değer", "Satır ve sütun sayıları en az 1 olmalıdır.")
            return
        try:
            names = self._resolved_names(rows, cols)
        except ValueError as exc:
            messagebox.showerror("Dosya adı hatası", str(exc))
            return

        if self.cut_mode.get() == "manual":
            xs = [0] + sorted(self.vertical_lines) + [self.image.width]
            ys = [0] + sorted(self.horizontal_lines) + [self.image.height]
        else:
            # Integer boundaries give every pixel to exactly one cell; remainder lands in later cells.
            xs = [(i * self.image.width) // cols for i in range(cols)] + [self.image.width]
            ys = [(i * self.image.height) // rows for i in range(rows)] + [self.image.height]
            if len(set(xs)) != len(xs) or len(set(ys)) != len(ys):
                messagebox.showerror("Grid çok büyük", "Satır veya sütun sayısı görselin piksel boyutunu aşıyor.")
                return
        try:
            index = 0
            for r in range(rows):
                for c in range(cols):
                    part = self.image.crop((xs[c], ys[r], xs[c + 1], ys[r + 1]))
                    part.save(os.path.join(output, names[index]), format="PNG")
                    index += 1
            self.status.set(f"{index} adet PNG oluşturuldu — {output}")
            messagebox.showinfo("İşlem tamamlandı", f"{index} adet PNG oluşturuldu")
        except Exception as exc:
            messagebox.showerror("Kaydetme hatası", f"PNG dosyaları kaydedilirken hata oluştu:\n{exc}")

    def _load_presets_file(self):
        try:
            if os.path.exists(self.preset_file):
                with open(self.preset_file, "r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, dict):
                    self.presets = {str(k): list(v) for k, v in data.items() if isinstance(v, list)}
        except (OSError, json.JSONDecodeError):
            messagebox.showwarning("Preset uyarısı", "name_presets.json okunamadı; boş preset listesi kullanılacak.")
        self.preset_combo["values"] = sorted(self.presets, key=str.casefold)

    def save_preset(self):
        name = simpledialog.askstring("Preset kaydet", "Preset adı:", parent=self.root)
        if not name or not name.strip():
            return
        preset_name = name.strip()
        values = [INVALID_FILENAME_CHARS.sub("", var.get().strip()) for var in self.name_vars]
        self.presets[preset_name] = values
        try:
            with open(self.preset_file, "w", encoding="utf-8") as file:
                json.dump(self.presets, file, ensure_ascii=False, indent=2)
            self.preset_combo["values"] = sorted(self.presets, key=str.casefold)
            self.preset_combo.set(preset_name)
            messagebox.showinfo("Preset kaydedildi", f'"{preset_name}" preset olarak kaydedildi.')
        except OSError as exc:
            messagebox.showerror("Preset kaydedilemedi", f"Preset dosyası yazılamadı:\n{exc}")

    def load_selected_preset(self):
        name = self.preset_combo.get()
        if not name or name not in self.presets:
            messagebox.showwarning("Preset seçilmedi", "Lütfen yüklenecek bir preset seçin.")
            return
        self.update_name_table(self.presets[name])


def main():
    root = tk.Tk()
    PNGSplitterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
