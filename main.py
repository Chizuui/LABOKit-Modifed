import sys
import os
import random
import subprocess
import importlib.util
import importlib.machinery
import shutil
from pathlib import Path

# --- Path & Model Setup ---
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
MODEL_DIR = BASE_DIR / "models"
os.environ["U2NET_HOME"] = str(MODEL_DIR)

ICON_PATH = BASE_DIR / "labokit.ico"
PLUGIN_DIR = BASE_DIR / "plugins"
PLUGIN_DIR.mkdir(exist_ok=True)

# Real-ESRGAN exe path
# Check this path if you use different file/folder names
REALESRGAN_EXE = BASE_DIR / "realesrgan" / "realesrgan-ncnn-vulkan.exe"

remove = None

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QPixmap, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QFileDialog,
    QMessageBox, QProgressDialog, QFrame, QComboBox, QTabWidget,
    QDialog, QPlainTextEdit,
)

# Image extension filter
IMAGE_FILTER = (
    "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp *.gif "
    "*.JPG *.JPEG *.PNG *.BMP *.TIF *.TIFF *.WEBP *.GIF)"
)

# --- Running World Line Meter Text Data (Bottom Decoration) ---
RUNNING_VALUES = [
    # α
    "0.000000α", "0.134891α", "0.170922α", "0.210317α", "0.295582α",
    "0.328403α", "0.334581α", "0.337161α", "0.337187α", "0.337199α", "0.337337α",
    "0.409420α", "0.409431α", "0.456903α", "0.456914α", "0.456923α",
    "0.509736α", "0.523299α", "0.523307α",
    "0.549111α", "0.571015α", "0.571024α", "0.571046α", "0.571???α", "0.571082α",
    "0.615483α", "0.751354α", "0.815524α", "0.934587α",
    # β
    "1.053649β", "1.055821β", "1.064750β", "1.064756β", "1.081163β", "1.097302β",
    "1.123581β", "1.129848β", "1.129954β",
    "1.130205β", "1.130206β", "1.130207β", "1.130208β", "1.130209β",
    "1.130211β", "1.130212β", "1.130238β", "1.130426β",
    "1.143688β", "1.382733β", "1.467093β", "1.818520β",
    # δ
    "3.019430δ", "3.030493δ", "3.130238δ", "3.182879δ", "3.372329δ", "3.386019δ",
    "3.406288δ", "3.600104δ", "3.667293δ",
    # ε
    "4.456441ε", "4.456442ε", "4.493623ε", "4.493624ε", "4.530805ε", "4.530806ε",
]

# --- BG Removal Presets ---
BG_PRESETS = {
    "Standard": {
        "alpha_matting": False,
        "post_process_mask": False,
    },
    "Medium": {
        "alpha_matting": False,
        "post_process_mask": True,
    },
    "High": {
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 240,
        "alpha_matting_background_threshold": 10,
        "alpha_matting_erode_structure_size": 10,
        "alpha_matting_base_size": 1000,
        "post_process_mask": True,
    },
}

DEFAULT_PRESET_NAME = "Standard"


# ==========================================
# TAB 1: BG REMOVER
# ==========================================

class BgRemoverTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Init variables
        self.image_paths: list[Path] = []
        self.output_dir: Path | None = None
        self.output_map: dict[Path, Path] = {}

        self.current_original_pixmap: QPixmap | None = None
        self.current_result_pixmap: QPixmap | None = None

        self.pixel_labels: list[QLabel] = []
        self._running_index = 0
        self._running_timer: QTimer | None = None

        self.presets = BG_PRESETS
        self.current_preset_name = DEFAULT_PRESET_NAME

        self._setup_ui()
        self._init_running_text()

    # --- Setup UI ---
    def _setup_ui(self):
        # Main Layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(6)

        main_layout = QHBoxLayout()
        outer_layout.addLayout(main_layout, stretch=1)

        # LEFT: File List
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, stretch=1)

        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.on_file_selected)
        lbl_list = QLabel("LOADED IMAGES (BG Remover):")
        lbl_list.setStyleSheet("border: none; background: transparent;") 
        left_layout.addWidget(lbl_list)
        left_layout.addWidget(self.file_list, stretch=1)

        btn_add = QPushButton("Add Images…")
        btn_add.clicked.connect(self.add_images)
        btn_clear = QPushButton("Clear List")
        btn_clear.clicked.connect(self.clear_list)

        left_btn_row = QHBoxLayout()
        left_btn_row.addWidget(btn_add)
        left_btn_row.addWidget(btn_clear)
        left_layout.addLayout(left_btn_row)

        # RIGHT: Preview & Controls
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, stretch=3)

        self.output_label = QLabel("BG OUTPUT FOLDER: (auto)")
        self.output_label.setWordWrap(True)
        right_layout.addWidget(self.output_label)

        # Preview Area
        previews_layout = QHBoxLayout()
        right_layout.addLayout(previews_layout, stretch=5)

        self.original_label = self._create_preview_box("Original")
        self.result_label = self._create_preview_box("Result (Background Removed)")
        previews_layout.addWidget(self.original_label, stretch=1)
        previews_layout.addWidget(self.result_label, stretch=1)

        # Preset Selection
        right_layout.addSpacing(6)
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Sensitivity:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.presets.keys())
        self.preset_combo.setCurrentText(self.current_preset_name)
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_row.addWidget(self.preset_combo)
        right_layout.addLayout(preset_row)

        # Process Buttons
        right_layout.addSpacing(10)
        btn_row = QHBoxLayout()
        right_layout.addLayout(btn_row)

        self.btn_process_selected = QPushButton("Remove BG (Selected)")
        self.btn_process_selected.clicked.connect(self.process_selected)
        self.btn_process_all = QPushButton("Remove BG (All)")
        self.btn_process_all.clicked.connect(self.process_all)

        btn_row.addWidget(self.btn_process_selected)
        btn_row.addWidget(self.btn_process_all)

        right_layout.addStretch(1)

        # Bottom bar (pixel style)
        bottom_frame = QFrame()
        bottom_frame.setObjectName("PixelBar")
        bar_layout = QHBoxLayout(bottom_frame)
        bar_layout.setContentsMargins(10, 3, 10, 4)
        bar_layout.setSpacing(18)

        pixel_font = QFont("Consolas", 9)
        for _ in range(10):
            lbl = QLabel("0.000000α")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lbl.setFont(pixel_font)
            self.pixel_labels.append(lbl)
            bar_layout.addWidget(lbl)

        outer_layout.addWidget(bottom_frame)

    def _create_preview_box(self, title: str) -> QLabel:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(frame)
        lbl_title = QLabel(title)
        layout.addWidget(lbl_title)
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setMinimumSize(QSize(200, 200))
        layout.addWidget(lbl_img, stretch=1)

        frame.image_label = lbl_img
        return frame

    # --- Running Text Logic ---

    def _init_running_text(self):
        # Random initial values
        for lbl in self.pixel_labels:
            lbl.setText(self._random_running_value() + "  •")

        self._running_index = 0
        self._running_timer = QTimer(self)
        self._running_timer.setInterval(1000)
        self._running_timer.timeout.connect(self._update_running_bar)
        self._running_timer.start()

    def _random_running_value(self) -> str:
        return random.choice(RUNNING_VALUES)

    def _update_running_bar(self):
        if not self.pixel_labels:
            return
        idx = self._running_index % len(self.pixel_labels)
        self._running_index += 1
        self.pixel_labels[idx].setText(self._random_running_value() + "  •")

    # --- File List Management ---

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select images", "", IMAGE_FILTER
        )
        if not files:
            return

        added = 0
        for f in files:
            path = Path(f)
            if path not in self.image_paths:
                self.image_paths.append(path)
                item = QListWidgetItem(path.name)
                item.setData(Qt.UserRole, path)
                self.file_list.addItem(item)
                added += 1

        if added > 0 and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)

    def clear_list(self):
        self.image_paths.clear()
        self.output_map.clear()
        self.file_list.clear()
        self.current_original_pixmap = None
        self.current_result_pixmap = None
        self._update_previews(None)

    def on_file_selected(self, row: int):
        if row < 0 or row >= len(self.image_paths):
            self._update_previews(None)
            return
        path = self.image_paths[row]
        self._update_previews(path)

    # --- Preview Logic ---

    def _update_previews(self, path: Path | None):
        orig_label: QLabel = self.original_label.image_label  # type: ignore
        res_label: QLabel = self.result_label.image_label      # type: ignore

        if path is None:
            orig_label.setPixmap(QPixmap())
            orig_label.setText("(no image)")
            res_label.setPixmap(QPixmap())
            res_label.setText("(no result)")
            return

        # Show Original
        pix = QPixmap(str(path))
        if not pix.isNull():
            self.current_original_pixmap = pix
            orig_label.setPixmap(
                pix.scaled(
                    orig_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            orig_label.setText("")
        else:
            orig_label.setPixmap(QPixmap())
            orig_label.setText("(failed to load)")

        # Show Result (if exists)
        out = self.output_map.get(path)
        if out is not None and out.exists():
            pix_res = QPixmap(str(out))
            if not pix_res.isNull():
                self.current_result_pixmap = pix_res
                res_label.setPixmap(
                    pix_res.scaled(
                        res_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
                res_label.setText("")
                return

        # No result yet
        res_label.setPixmap(QPixmap())
        res_label.setText("(no result yet)")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Rescale on window resize
        row = self.file_list.currentRow()
        if 0 <= row < len(self.image_paths):
            self._update_previews(self.image_paths[row])

    def on_preset_changed(self, name: str):
        if name in self.presets:
            self.current_preset_name = name

    # --- Output Folder ---

    def ensure_output_dir(self, sample_input: Path) -> Path:
        # Create LABOKit_BG folder next to input file if not set
        if self.output_dir is None:
            base = sample_input.parent
            out = base / "LABOKit_BG"
            out.mkdir(exist_ok=True)
            self.output_dir = out
            self.output_label.setText(f"BG OUTPUT FOLDER: {self.output_dir}")
            QMessageBox.information(
                self,
                "LABOKit",
                f"BG output folder automatically set to:\n{self.output_dir}",
            )
        return self.output_dir

    def change_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select BG output folder")
        if folder:
            self.output_dir = Path(folder)
            self.output_label.setText(f"BG OUTPUT FOLDER: {self.output_dir}")

    # --- Main Process ---

    def process_selected(self):
        selected_paths: list[Path] = []
        for item in self.file_list.selectedItems():
            path = item.data(Qt.UserRole)
            if isinstance(path, Path):
                selected_paths.append(path)

        if not selected_paths:
            QMessageBox.information(
                self, "LABOKit", "No images selected. Please select one or more images."
            )
            return

        self._process_paths(selected_paths)

    def process_all(self):
        if not self.image_paths:
            QMessageBox.information(
                self, "LABOKit", "No images loaded. Please add images first."
            )
            return
        self._process_paths(self.image_paths)

    def _process_paths(self, paths: list[Path]):
        out_dir = self.ensure_output_dir(paths[0])

        progress = QProgressDialog(
            "Removing backgrounds...", "Cancel", 0, len(paths), self
        )
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setWindowTitle("LABOKit - BG Remover")
        progress.show()

        processed = 0
        for i, p in enumerate(paths, start=1):
            if progress.wasCanceled():
                break

            progress.setLabelText(f"Processing {p.name} ({i}/{len(paths)})")
            QApplication.processEvents()

            try:
                out_path = out_dir / f"{p.stem}_nobg.png"
                self._remove_bg_file(p, out_path)
                self.output_map[p] = out_path
                processed += 1
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to process {p.name}:\n{e}",
                )

            progress.setValue(i)
            QApplication.processEvents()

        progress.close()

        QMessageBox.information(
            self,
            "LABOKit",
            f"Finished.\nProcessed: {processed} / {len(paths)} images.\n\n"
            f"Output folder:\n{out_dir}",
        )

        # Refresh preview of currently selected file
        row = self.file_list.currentRow()
        if 0 <= row < len(self.image_paths):
            self._update_previews(self.image_paths[row])

    def _remove_bg_file(self, input_path: Path, output_path: Path):
        import rembg
        with open(input_path, "rb") as f:
            input_bytes = f.read()

        preset = self.presets.get(self.current_preset_name, {})
        result_bytes = rembg.remove(input_bytes, **preset)

        with open(output_path, "wb") as f:
            f.write(result_bytes)

    # --- Help ---
    def show_help(self):
        text = (
            "LABOKit – BG Remover (Tab 1)\n\n"
            "1. Add images\n"
            "   • Use File → Add Images… or the 'Add Images…' button.\n"
            "   • You can select one or many files at once.\n\n"
            "2. Output folder\n"
            "   • By default, LABOKit will create a folder named 'LABOKit_BG'\n"
            "     next to your first image and save results there.\n"
            "   • You can change the BG output folder via File → Change Output Folder…\n"
            "     while this tab is active.\n\n"
            "3. Removing backgrounds\n"
            "   • Select one or more items in the list and click\n"
            "     'Remove BG (Selected)' to process only those images.\n"
            "   • Or click 'Remove BG (All)' to process every loaded image.\n"
            "   • A progress window will appear while processing.\n\n"
            "4. Preview\n"
            "   • Click on an item in the list to see its original preview.\n"
            "   • After processing, the result (with transparent background)\n"
            "     will appear in the 'Result (Background Removed)' panel.\n\n"
            "5. Presets\n"
            "   • Use the 'Removal preset' dropdown to choose how strong\n"
            "     the background removal should be (Standard / Medium / High).\n"
            "   • Higher presets may be slower but keep more detail.\n"
        )
        QMessageBox.information(self, "How To Use – BG Remover", text)


# ==========================================
# TAB 2: UPSCALER (Real-ESRGAN)
# ==========================================

class UpscalerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.image_paths: list[Path] = []
        self.output_dir: Path | None = None
        self.output_map: dict[Path, Path] = {}

        self.current_original_pixmap: QPixmap | None = None
        self.current_result_pixmap: QPixmap | None = None

        self.pixel_labels: list[QLabel] = []
        self._running_index = 0
        self._running_timer: QTimer | None = None

        self._setup_ui()
        self._init_running_text()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(6)

        main_layout = QHBoxLayout()
        outer_layout.addLayout(main_layout, stretch=1)

        # LEFT: File List
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, stretch=1)

        self.file_list = QListWidget()
        lbl_list = QLabel("LOADED IMAGES (Upscaler):")
        lbl_list.setStyleSheet("border: none; background: transparent;")
        left_layout.addWidget(lbl_list)
        left_layout.addWidget(self.file_list, stretch=1)

        btn_add = QPushButton("Add Images…")
        btn_add.clicked.connect(self.add_images)
        btn_clear = QPushButton("Clear List")
        btn_clear.clicked.connect(self.clear_list)

        left_btn_row = QHBoxLayout()
        left_btn_row.addWidget(btn_add)
        left_btn_row.addWidget(btn_clear)
        left_layout.addLayout(left_btn_row)

        # RIGHT: Preview & Controls
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, stretch=3)

        self.output_label = QLabel("UPSCALE OUTPUT FOLDER: (auto)")
        self.output_label.setWordWrap(True)
        right_layout.addWidget(self.output_label)

        previews_layout = QHBoxLayout()
        right_layout.addLayout(previews_layout, stretch=5)

        self.original_label = self._create_preview_box("Original")
        self.result_label = self._create_preview_box("Result (Upscaled)")
        previews_layout.addWidget(self.original_label, stretch=1)
        previews_layout.addWidget(self.result_label, stretch=1)

        # Upscale Options
        right_layout.addSpacing(6)
        opt_row = QHBoxLayout()

        opt_row.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["2x", "4x"])
        self.scale_combo.setCurrentText("4x")
        opt_row.addWidget(self.scale_combo)

        opt_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        # Model name must match 'realesrgan' folder
        self.model_combo.addItems(["realesrgan-x4plus", "realesrgan-x4plus-anime"])
        self.model_combo.setCurrentText("realesrgan-x4plus")
        opt_row.addWidget(self.model_combo)

        right_layout.addLayout(opt_row)

        # Process Buttons
        right_layout.addSpacing(10)
        btn_row = QHBoxLayout()
        self.btn_upscale_selected = QPushButton("Upscale (Selected)")
        self.btn_upscale_selected.clicked.connect(self.upscale_selected)
        self.btn_upscale_all = QPushButton("Upscale (All)")
        self.btn_upscale_all.clicked.connect(self.upscale_all)

        btn_row.addWidget(self.btn_upscale_selected)
        btn_row.addWidget(self.btn_upscale_all)
        right_layout.addLayout(btn_row)

        right_layout.addStretch(1)

        # Bottom Bar
        bottom_frame = QFrame()
        bottom_frame.setObjectName("PixelBar")
        bar_layout = QHBoxLayout(bottom_frame)
        bar_layout.setContentsMargins(10, 3, 10, 4)
        bar_layout.setSpacing(18)

        pixel_font = QFont("Consolas", 9)
        for _ in range(10):
            lbl = QLabel("0.000000α")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lbl.setFont(pixel_font)
            self.pixel_labels.append(lbl)
            bar_layout.addWidget(lbl)

        outer_layout.addWidget(bottom_frame)

    def _create_preview_box(self, title: str) -> QLabel:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(frame)
        lbl_title = QLabel(title)
        layout.addWidget(lbl_title)
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setMinimumSize(QSize(200, 200))
        layout.addWidget(lbl_img, stretch=1)

        frame.image_label = lbl_img
        return frame

    # --- Running Text ---

    def _init_running_text(self):
        for lbl in self.pixel_labels:
            lbl.setText(self._random_running_value() + "  •")

        self._running_index = 0
        self._running_timer = QTimer(self)
        self._running_timer.setInterval(1000)
        self._running_timer.timeout.connect(self._update_running_bar)
        self._running_timer.start()

    def _random_running_value(self) -> str:
        return random.choice(RUNNING_VALUES)

    def _update_running_bar(self):
        if not self.pixel_labels:
            return
        idx = self._running_index % len(self.pixel_labels)
        self._running_index += 1
        self.pixel_labels[idx].setText(self._random_running_value() + "  •")

    # --- File List & Selection ---

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select images for upscaling", "", IMAGE_FILTER
        )
        if not files:
            return

        added = 0
        for f in files:
            path = Path(f)
            if path not in self.image_paths:
                self.image_paths.append(path)
                item = QListWidgetItem(path.name)
                item.setData(Qt.UserRole, path)
                self.file_list.addItem(item)
                added += 1

        if added > 0 and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)

    def clear_list(self):
        self.image_paths.clear()
        self.output_map.clear()
        self.file_list.clear()
        self.current_original_pixmap = None
        self.current_result_pixmap = None
        self._update_previews(None)

    def on_file_selected(self, row: int):
        if row < 0 or row >= len(self.image_paths):
            self._update_previews(None)
            return
        path = self.image_paths[row]
        self._update_previews(path)

    def _update_previews(self, path: Path | None):
        orig_label: QLabel = self.original_label.image_label  # type: ignore
        res_label: QLabel = self.result_label.image_label      # type: ignore

        if path is None:
            orig_label.setPixmap(QPixmap())
            orig_label.setText("(no image)")
            res_label.setPixmap(QPixmap())
            res_label.setText("(no result)")
            return

        pix = QPixmap(str(path))
        if not pix.isNull():
            self.current_original_pixmap = pix
            orig_label.setPixmap(
                pix.scaled(
                    orig_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            orig_label.setText("")
        else:
            orig_label.setPixmap(QPixmap())
            orig_label.setText("(failed to load)")

        out = self.output_map.get(path)
        if out is not None and out.exists():
            pix_res = QPixmap(str(out))
            if not pix_res.isNull():
                self.current_result_pixmap = pix_res
                res_label.setPixmap(
                    pix_res.scaled(
                        res_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
                res_label.setText("")
                return

        res_label.setPixmap(QPixmap())
        res_label.setText("(no result yet)")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        row = self.file_list.currentRow()
        if 0 <= row < len(self.image_paths):
            self._update_previews(self.image_paths[row])

    # --- Output Folder ---

    def ensure_output_dir(self, sample_input: Path) -> Path:
        # Create LABOKit_UP folder next to input file
        if self.output_dir is None:
            base = sample_input.parent
            out = base / "LABOKit_UP"
            out.mkdir(exist_ok=True)
            self.output_dir = out
            self.output_label.setText(f"UPSCALE OUTPUT FOLDER: {self.output_dir}")
            QMessageBox.information(
                self,
                "LABOKit",
                f"Upscale output folder automatically set to:\n{self.output_dir}",
            )
        return self.output_dir

    def change_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Upscale output folder")
        if folder:
            self.output_dir = Path(folder)
            self.output_label.setText(f"Upscale OUTPUT FOLDER: {self.output_dir}")

    # --- Upscaling Process ---

    def upscale_selected(self):
        paths: list[Path] = []
        for item in self.file_list.selectedItems():
            p = item.data(Qt.UserRole)
            if isinstance(p, Path):
                paths.append(p)

        if not paths:
            QMessageBox.information(
                self, "LABOKit", "No images selected. Please select one or more images."
            )
            return

        self._process_paths(paths)

    def upscale_all(self):
        if not self.image_paths:
            QMessageBox.information(
                self, "LABOKit", "No images loaded. Please add images first."
            )
            return
        self._process_paths(self.image_paths)

    def _process_paths(self, paths: list[Path]):
        if not REALESRGAN_EXE.exists():
            QMessageBox.warning(
                self,
                "Upscale error",
                "Real-ESRGAN executable not found.\n"
                "Please place 'realesrgan-ncnn-vulkan.exe' in the 'realesrgan' folder.",
            )
            return

        out_dir = self.ensure_output_dir(paths[0])

        progress = QProgressDialog(
            "Upscaling images...", "Cancel", 0, len(paths), self
        )
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setWindowTitle("LABOKit - Upscaler")
        progress.show()

        # Parse scale
        scale_text = self.scale_combo.currentText()  # "2x" / "4x"
        try:
            scale = int(scale_text.replace("x", ""))
        except ValueError:
            scale = 4

        model_name = self.model_combo.currentText()

        processed = 0
        for i, p in enumerate(paths, start=1):
            if progress.wasCanceled():
                break

            progress.setLabelText(f"Processing {p.name} ({i}/{len(paths)})")
            QApplication.processEvents()

            try:
                out_path = out_dir / f"{p.stem}_up{scale}x.png"
                self._upscale_file(p, out_path, scale, model_name)
                self.output_map[p] = out_path
                processed += 1
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Upscale error",
                    f"Failed to upscale {p.name}:\n{e}",
                )

            progress.setValue(i)
            QApplication.processEvents()

        progress.close()

        QMessageBox.information(
            self,
            "LABOKit",
            f"Upscale finished.\nProcessed: {processed} / {len(paths)} images.\n\n"
            f"Output folder:\n{out_dir}",
        )

        row = self.file_list.currentRow()
        if 0 <= row < len(self.image_paths):
            self._update_previews(self.image_paths[row])

    def _upscale_file(self, input_path: Path, output_path: Path, scale: int, model_name: str):
        cmd = [
            str(REALESRGAN_EXE),
            "-i", str(input_path),
            "-o", str(output_path),
            "-n", model_name,
            "-s", str(scale),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "Unknown error from Real-ESRGAN")

    # --- Help ---

    def show_help(self):
        text = (
            "LABOKit – Upscaler (Tab 2)\n\n"
            "1. Add images\n"
            "   • Use File → Add Images… while this tab is active, or the\n"
            "     'Add Images…' button inside the Upscaler tab.\n\n"
            "2. Output folder\n"
            "   • By default, LABOKit will create a folder named 'LABOKit_UP'\n"
            "     next to your first image and save upscaled results there.\n"
            "   • You can change the Upscale output folder via File → Change Output Folder…\n"
            "     while this tab is active.\n\n"
            "3. Scale & model\n"
            "   • Choose the upscale factor (2x or 4x).\n"
            "   • Choose the Real-ESRGAN model (e.g. 'realesrgan-x4plus' for general use,\n"
            "     or 'realesrgan-x4plus-anime' for anime-style images).\n\n"
            "4. Upscaling\n"
            "   • Select one or more items in the list and click 'Upscale (Selected)'\n"
            "     to process only those images.\n"
            "   • Or click 'Upscale (All)' to process every loaded image.\n"
            "   • A progress window will appear while Real-ESRGAN is running.\n\n"
            "5. Preview\n"
            "   • Click on an item in the list to see the original on the left.\n"
            "   • After upscaling, the result will appear in the 'Result (Upscaled)'\n"
            "     preview panel.\n\n"
            "Note:\n"
            "   • This tab calls the external binary 'realesrgan-ncnn-vulkan.exe'.\n"
            "     Make sure it and its models are placed in the 'realesrgan' folder\n"
            "     inside the LABOKit directory.\n"
        )
        QMessageBox.information(self, "How To Use – Upscaler", text)


# ==========================================
# MAIN WINDOW & PLUGINS
# ==========================================

class LABOKitMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LABOKit")

        self.tabs = QTabWidget()
        self.bg_tab = BgRemoverTab(self)
        self.up_tab = UpscalerTab(self)

        self.tabs.addTab(self.bg_tab, "BG Remover")
        self.tabs.addTab(self.up_tab, "Upscaler")
        self.setCentralWidget(self.tabs)

        # Active plugin list
        self.loaded_plugins: list[dict] = []

        self._setup_menu()
        self._load_plugins()

    def _load_plugins(self):
        """Load .kit files from plugins folder"""

        if not PLUGIN_DIR.exists():
            PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

        # Clear old tabs before reload
        for pinfo in getattr(self, "loaded_plugins", []):
            tab_widget = pinfo.get("tab")
            if tab_widget is not None:
                idx = self.tabs.indexOf(tab_widget)
                if idx != -1:
                    self.tabs.removeTab(idx)

        self.loaded_plugins.clear()

        for path in PLUGIN_DIR.glob("*.kit"):
            module_name = f"labokit_plugin_{path.stem}"

            try:
                # Manual module load
                loader = importlib.machinery.SourceFileLoader(
                    module_name, str(path)
                )
                spec = importlib.util.spec_from_file_location(
                    module_name, str(path), loader=loader
                )
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore[attr-defined]

                plugin_id = getattr(module, "PLUGIN_ID", path.stem)
                plugin_name = getattr(module, "PLUGIN_NAME", path.stem)
                help_text = getattr(module, "HELP_TEXT", "")

                if not hasattr(module, "create_tab"):
                    continue

                tab_widget = module.create_tab(parent=self)
                self.tabs.addTab(tab_widget, plugin_name)

                self.loaded_plugins.append(
                    {
                        "id": plugin_id,
                        "name": plugin_name,
                        "module": module,
                        "help": help_text,
                        "tab": tab_widget,
                    }
                )

            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Plugin error",
                    f"Failed to load plugin from:\n{path}\n\nError:\n{e}",
                )

        # Update plugin help menu
        if hasattr(self, "plugins_help_menu"):
            self.plugins_help_menu.clear()
            if not self.loaded_plugins:
                dummy = QAction("(No plugins loaded)", self)
                dummy.setEnabled(False)
                self.plugins_help_menu.addAction(dummy)
            else:
                for plugin in self.loaded_plugins:
                    act = QAction(plugin["name"], self)
                    act.triggered.connect(
                        lambda checked=False, p=plugin: self._show_plugin_help(p)
                    )
                    self.plugins_help_menu.addAction(act)

    def load_plugin_from_file(self):
        """Select .kit file, copy to plugins folder, reload."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select LABOKit plugin file",
            "",
            "LABOKit plugin (*.kit);;All files (*.*)",
        )
        if not file_path:
            return

        src = Path(file_path)
        if not src.exists():
            QMessageBox.warning(self, "Plugin load", "Selected file does not exist.")
            return

        PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        dst = PLUGIN_DIR / src.name

        # Overwrite check
        if dst.exists():
            resp = QMessageBox.question(
                self,
                "Plugin already exists",
                f"A plugin file named '{src.name}' already exists.\n"
                "Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        try:
            shutil.copy2(src, dst)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Plugin load error",
                f"Failed to copy plugin file:\n{e}",
            )
            return

        # Reload
        self._load_plugins()

        QMessageBox.information(
            self,
            "Plugin loaded",
            f"Plugin file copied to:\n{dst}\n\n"
            "If the plugin is valid, it should now appear as a new tab.",
        )
    
    def _show_plugin_help(self, plugin_info: dict):
        text = plugin_info.get("help") or "(No help text provided for this plugin.)"
        QMessageBox.information(
            self,
            f"Plugin Help – {plugin_info.get('name', '')}",
            text,
        )

    def _setup_menu(self):
        menubar = self.menuBar()

        # Menu: File
        file_menu = menubar.addMenu("&File")

        act_add = QAction("Add Images…", self)
        act_add.triggered.connect(self.add_images_current_tab)
        file_menu.addAction(act_add)

        act_change_output = QAction("Change Output Folder…", self)
        act_change_output.triggered.connect(self.change_output_folder_current_tab)
        file_menu.addAction(act_change_output)

        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Menu: Config
        config_menu = menubar.addMenu("&Config")

        act_load_plugin = QAction("Load Plugin (.kit)…", self)
        act_load_plugin.triggered.connect(self.load_plugin_from_file)
        config_menu.addAction(act_load_plugin)

        # Menu: Help
        help_menu = menubar.addMenu("&Help")

        act_help_bg = QAction("BG Remover", self)
        act_help_bg.triggered.connect(self.show_bg_help)
        help_menu.addAction(act_help_bg)

        act_help_up = QAction("Upscaler", self)
        act_help_up.triggered.connect(self.show_upscale_help)
        help_menu.addAction(act_help_up)

        help_menu.addSeparator()

        act_notice = QAction("Licenses / NOTICE", self)
        act_notice.triggered.connect(self.show_notice)
        help_menu.addAction(act_notice)

        # Submenu plugins
        self.plugins_help_menu = help_menu.addMenu("Plugins")


    # --- Menu Actions ---

    def add_images_current_tab(self):
        current = self.tabs.currentWidget()
        if hasattr(current, "add_images"):
            current.add_images()

    def change_output_folder_current_tab(self):
        current = self.tabs.currentWidget()
        if hasattr(current, "change_output_folder"):
            current.change_output_folder()

    def show_bg_help(self):
        self.bg_tab.show_help()

    def show_upscale_help(self):
        self.up_tab.show_help()

    def show_notice(self):
        notice_path = BASE_DIR / "LABOKit_NOTICE.txt"

        if not notice_path.exists():
            QMessageBox.warning(
                self,
                "NOTICE",
                "LABOKit_NOTICE.txt not found.\n"
                "Please make sure the file is in the same folder as main.py / LABOKit.exe.",
            )
            return

        try:
            text = notice_path.read_text(encoding="utf-8")
        except Exception as e:
            QMessageBox.warning(
                self,
                "NOTICE",
                f"Failed to read NOTICE file:\n{e}",
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("LABOKit – NOTICE & Licenses")
        dlg.resize(700, 500)

        layout = QVBoxLayout(dlg)

        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        editor.setFont(QFont("Consolas", 9))
        layout.addWidget(editor)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.exec()


# ==========================================
# APP ENTRY POINT
# ==========================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LABOKit")
    icon_path = ICON_PATH
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash_img_path = BASE_DIR / "splash.png"

    if splash_img_path.exists():
        pixmap = QPixmap(str(splash_img_path))
        pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation) 
    else:
        pixmap = QPixmap(400, 100)
        pixmap.fill(Qt.white)

    from PySide6.QtWidgets import QSplashScreen
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents() 
    global remove
    try:
        from rembg import remove as rembg_remove
        dummy_data = b"\x00" * 100 
        try:
            rembg_remove(dummy_data) 
        except:
            pass
    except ImportError:
        pass

    app.setStyleSheet("""
        QMainWindow { background-color: #e9edf5; }
        /* ... (paste sisa CSS style kamu di sini seperti sebelumnya) ... */
        QTabWidget::pane { border: 1px solid #b3bcd1; border-radius: 4px; top: -1px; }
        QTabBar::tab { background-color: #dde4f5; border: 1px solid #b3bcd1; padding: 4px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; color: #1c2333; }
        QTabBar::tab:selected { background-color: #f5f7fb; }
        QMenuBar { background-color: #dbe2f2; color: #1c2333; border-bottom: 1px solid #b3bcd1; }
        QMenuBar::item { background: transparent; padding: 3px 8px; color: #1c2333; }
        QMenuBar::item:selected { background-color: #cfe2ff; color: #101522; }
        QMenu { background-color: #f7f9fc; border: 1px solid #b3bcd1; }
        QMenu::item { padding: 4px 20px; color: #1c2333; }
        QMenu::item:selected { background-color: #cfe2ff; color: #101522; }
        QListWidget { background-color: #f7f9fc; border: 1px solid #b3bcd1; border-radius: 4px; }
        QListWidget::item { padding: 4px 6px; color: #1c2333; }
        QListWidget::item:selected { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #cfe2ff, stop:1 #a9c5f2); color: #102039; }
        QFrame { background-color: #f5f7fb; border: 1px solid #b3bcd1; border-radius: 6px; }
        #PixelBar { background-color: #dde4f5; border-radius: 6px; border: 1px solid #b3bcd1; }
        #PixelBar QLabel { color: #4b556b; }
        QLabel { color: #1c2333; }
        QPushButton { color: #1c2333; background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #d8dfee); border: 1px solid #9ca7c2; border-radius: 5px; padding: 4px 12px; }
        QPushButton:hover { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #e6ecf7); }
        QPushButton:pressed { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #cfd6e8, stop:1 #b0bdd7); }
        QProgressDialog { background-color: #f5f7fb; }
        QDialog, QMessageBox { background-color: #f5f7fb; }
        QDialog QLabel, QMessageBox QLabel { color: #1c2333; }
        QDialog QPushButton, QMessageBox QPushButton { color: #1c2333; background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #d8dfee); border: 1px solid #9ca7c2; border-radius: 5px; padding: 4px 12px; }
        QPlainTextEdit { background-color: #f5f7fb; color: #1c2333; border: 1px solid #b3bcd1; border-radius: 4px; }
        QComboBox { background-color: #f7f9fc; border: 1px solid #b3bcd1; border-radius: 4px; padding: 2px 6px; color: #1c2333; }
        QComboBox QAbstractItemView { background-color: #ffffff; border: 1px solid #b3bcd1; selection-background-color: #cfe2ff; color: #1c2333; selection-color: #101522; }
    """)

    win = LABOKitMainWindow()
    win.show()
    
    splash.finish(win)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()