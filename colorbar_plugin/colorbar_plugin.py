import os
import io
from qgis.PyQt.QtCore import Qt, QRectF, QSize, QByteArray
from qgis.PyQt.QtGui import QIcon, QPainter, QImage, QPixmap, QColor, QFont, QLinearGradient, QPen, QFontMetrics
from qgis.PyQt.QtWidgets import (QAction, QFileDialog, QMessageBox, QDialog, 
                                 QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                                 QSpinBox, QPushButton, QFontComboBox, QLineEdit, 
                                 QCheckBox, QApplication, QColorDialog)
from qgis.PyQt.QtSvg import QSvgGenerator, QSvgRenderer
from qgis.core import (QgsMapLayerType, QgsSingleBandPseudoColorRenderer, 
                       QgsColorRampShader, QgsGraduatedSymbolRenderer)

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.backends.backend_svg import FigureCanvasSVG

# --- DATA STRUCTURE ---

class ColorItem:
    """A unified structure for both Raster Ramps and Vector Classes."""
    def __init__(self, value, color, label=""):
        self.value = value
        self.color = color
        self.label = label


# --- HELPER FUNCTIONS FOR DRAWING ---

def generate_labels(items, num_ticks, decimals, units, use_scientific, use_latex, use_siunitx):
    """Pre-calculates all label strings to accurately determine bounding boxes."""
    labels = []
    min_val = items[0].value
    max_val = items[-1].value
    val_range = max_val - min_val if max_val != min_val else 1
    
    for i in range(num_ticks):
        rel_pos = i / (num_ticks - 1) if num_ticks > 1 else 0
        val = min_val + (rel_pos * val_range)
        
        val_str = f"{val:.{decimals}e}" if use_scientific else f"{val:.{decimals}f}"
        
        if use_latex:
            if use_siunitx:
                if units:
                    label_text = rf"\SI{{{val_str}}}{{{units}}}"
                else:
                    label_text = rf"\num{{{val_str}}}"
            else:
                if units:
                    label_text = rf"${val_str}$ {units}".strip()
                else:
                    label_text = rf"${val_str}$"
        else:
            label_text = f"{val_str} {units}".strip()
            
        labels.append(label_text)
        
    return labels

def get_colorbar_dimensions(orientation, title_text, font_size, text_box_width, label_spacing, rotate_labels):
    """Calculates sizes and layout based on the chosen orientation and title presence."""
    margin = 20
    bar_thickness = 40
    bar_length = 360
    tick_length = 5
    
    title_space = int(font_size * 2.5) if title_text.strip() else 0
    top_margin = margin + title_space
    
    if orientation == "Vertical":
        # Expand width if labels are rotated so they don't clip
        adjusted_text_width = text_box_width * 1.2 if rotate_labels else text_box_width
        total_content_width = bar_thickness + tick_length + label_spacing + adjusted_text_width
        img_width = max(450.0, total_content_width + 80.0)
        
        offset_x = (img_width - total_content_width) / 2.0
        img_height = top_margin + bar_length + 40
        bar_rect = QRectF(offset_x, top_margin, bar_thickness, bar_length)
        
    else: # Horizontal
        side_margin = max(40.0, text_box_width) if rotate_labels else max(40.0, text_box_width / 2.0)
        img_width = bar_length + (2 * side_margin)
        
        # Expand bottom height significantly if labels are rotated
        rotation_expansion = text_box_width * 0.7 if rotate_labels else 0
        img_height = top_margin + bar_thickness + tick_length + label_spacing + int(font_size * 5.5) + rotation_expansion + 20
        
        offset_x = side_margin
        bar_rect = QRectF(offset_x, top_margin, bar_length, bar_thickness)
        
    return img_width, img_height, bar_rect, offset_x, top_margin, bar_thickness, bar_length, title_space


def draw_latex_text(painter, text, x, y, font_family, font_size, alignment, is_bold=False, use_siunitx=True, rotate_angle=0):
    """Uses Matplotlib to render Math/LaTeX to an SVG on a fixed canvas."""
    
    if use_siunitx:
        rc_params = {
            'text.usetex': True,
            'font.family': 'sans-serif',
            'text.latex.preamble': r'\usepackage{siunitx} \usepackage{amsmath}'
        }
        if is_bold:
            text = rf"\textbf{{{text}}}"
    else:
        rc_params = {
            'text.usetex': False,
            'mathtext.default': 'regular'
        }
        
    with mpl.rc_context(rc_params):
        # We use a massive 10x10 inch canvas so that rotated math strings never clip the internal bounding box
        fig_width_in = 10.0
        fig_height_in = 10.0
        fig = Figure(figsize=(fig_width_in, fig_height_in), dpi=72)
        canvas = FigureCanvasSVG(fig)
        
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')
        
        weight = 'bold' if is_bold else 'normal'
        
        if alignment & Qt.AlignHCenter:
            ha, text_x = 'center', 0.5
        elif alignment & Qt.AlignRight:
            ha, text_x = 'right', 1.0
        else:
            ha, text_x = 'left', 0.0

        if alignment & Qt.AlignVCenter:
            va, text_y = 'center', 0.5
        elif alignment & Qt.AlignBottom:
            va, text_y = 'bottom', 0.0
        else: 
            va, text_y = 'top', 1.0
            
        ax.text(text_x, text_y, text, transform=ax.transAxes, 
                fontsize=font_size, family=font_family, 
                weight=weight, ha=ha, va=va, color='black', rotation=rotate_angle)
        
        buf = io.BytesIO()
        fig.savefig(buf, format='svg', transparent=True)
        
        svg_data = buf.getvalue()
        renderer = QSvgRenderer(QByteArray(svg_data))
        
        scale = 96.0 / 72.0 
        w_px = fig_width_in * 72.0 * scale
        h_px = fig_height_in * 72.0 * scale
        
        draw_x, draw_y = x, y
        
        if alignment & Qt.AlignHCenter: draw_x -= (w_px / 2.0)
        elif alignment & Qt.AlignRight: draw_x -= w_px
            
        if alignment & Qt.AlignVCenter: draw_y -= (h_px / 2.0)
        elif alignment & Qt.AlignBottom: draw_y -= h_px
            
        rect = QRectF(draw_x, draw_y, w_px, h_px)
        renderer.render(painter, rect)


def render_colorbar(paint_device, items, labels, orientation, num_ticks, img_width, img_height, 
                    bar_rect, offset_x, top_margin, bar_thickness, bar_length, title_space, text_box_width, label_spacing,
                    font_family, font_size, title, bg_color, is_transparent, use_latex, use_siunitx, text_alignment, is_discrete, rotate_labels):
    
    painter = QPainter(paint_device)
    if isinstance(paint_device, QImage):
        painter.setRenderHint(QPainter.Antialiasing)

    if orientation == "Horizontal":
        h_align = Qt.AlignHCenter
    else:
        if text_alignment == "Left": h_align = Qt.AlignLeft
        elif text_alignment == "Center": h_align = Qt.AlignHCenter
        else: h_align = Qt.AlignRight

    if not is_transparent:
        painter.fillRect(QRectF(0, 0, img_width, img_height), bg_color)

    if title.strip():
        if use_latex:
            draw_latex_text(painter, title.strip(), img_width / 2.0, 20, 
                            font_family, font_size * 1.2, Qt.AlignHCenter | Qt.AlignTop, 
                            is_bold=True, use_siunitx=use_siunitx)
        else:
            title_font = QFont(font_family, int(font_size * 1.2), QFont.Bold)
            painter.setFont(title_font)
            title_rect = QRectF(0, 20, img_width, title_space)
            painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop, title.strip())

    min_val = items[0].value
    max_val = items[-1].value
    val_range = max_val - min_val if max_val != min_val else 1

    if is_discrete:
        if isinstance(paint_device, QImage):
            painter.setRenderHint(QPainter.Antialiasing, False)
            
        painter.setPen(Qt.NoPen)
        for i in range(0, len(items), 2):
            if i + 1 >= len(items):
                break
            
            lower_item = items[i]
            upper_item = items[i+1]
            
            rel_lower = max(0.0, min(1.0, (lower_item.value - min_val) / val_range))
            rel_upper = max(0.0, min(1.0, (upper_item.value - min_val) / val_range))
            
            if orientation == "Vertical":
                y1 = top_margin + bar_length - (rel_upper * bar_length)
                y2 = top_margin + bar_length - (rel_lower * bar_length)
                block_rect = QRectF(bar_rect.x(), y1, bar_rect.width(), y2 - y1)
            else:
                x1 = offset_x + (rel_lower * bar_length)
                x2 = offset_x + (rel_upper * bar_length)
                block_rect = QRectF(x1, bar_rect.y(), x2 - x1, bar_rect.height())
                
            painter.setBrush(lower_item.color)
            painter.drawRect(block_rect)
            
        if isinstance(paint_device, QImage):
            painter.setRenderHint(QPainter.Antialiasing, True)
    else:
        if orientation == "Vertical":
            gradient = QLinearGradient(0, top_margin + bar_length, 0, top_margin)
        else:
            gradient = QLinearGradient(offset_x, 0, offset_x + bar_length, 0)
        
        for item in items:
            rel_pos = (item.value - min_val) / val_range
            rel_pos = max(0.0, min(1.0, rel_pos)) 
            gradient.setColorAt(rel_pos, item.color)

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRect(bar_rect)
    
    pen = QPen(Qt.black, 1)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(bar_rect)

    tick_font = QFont(font_family, font_size)
    painter.setFont(tick_font)
    tick_length = 5

    # Angles: Qt rotates Clockwise. Matplotlib rotates Counter-Clockwise.
    rotation_qt = 45 if rotate_labels else 0
    rotation_mpl = -45 if rotate_labels else 0

    for i in range(num_ticks):
        rel_pos = i / (num_ticks - 1) if num_ticks > 1 else 0
        label_text = labels[i]
        box_height = font_size * 3.0 
        
        if orientation == "Vertical":
            y = (top_margin + bar_length) - (rel_pos * bar_length)
            tick_start_x = offset_x + bar_thickness
            tick_end_x = tick_start_x + tick_length
            painter.drawLine(int(tick_start_x), int(y), int(tick_end_x), int(y))
            
            text_box_start = tick_end_x + label_spacing
            
            if h_align == Qt.AlignLeft: 
                anchor_x = text_box_start
                rect = QRectF(0, -box_height / 2.0, text_box_width, box_height)
            elif h_align == Qt.AlignHCenter: 
                anchor_x = text_box_start + (text_box_width / 2.0)
                rect = QRectF(-text_box_width / 2.0, -box_height / 2.0, text_box_width, box_height)
            else: 
                anchor_x = text_box_start + text_box_width
                rect = QRectF(-text_box_width, -box_height / 2.0, text_box_width, box_height)
            
            if use_latex:
                draw_latex_text(painter, label_text, anchor_x, y, 
                                font_family, font_size, h_align | Qt.AlignVCenter, 
                                use_siunitx=use_siunitx, rotate_angle=rotation_mpl)
            else:
                painter.save()
                painter.translate(anchor_x, y)
                painter.rotate(rotation_qt)
                painter.drawText(rect, h_align | Qt.AlignVCenter, label_text)
                painter.restore()
            
        else:
            x = offset_x + (rel_pos * bar_length)
            tick_start_y = top_margin + bar_thickness
            tick_end_y = tick_start_y + tick_length
            painter.drawLine(int(x), int(tick_start_y), int(x), int(tick_end_y))
            
            anchor_y = tick_end_y + label_spacing
            anchor_x = x
            
            if h_align == Qt.AlignLeft: 
                rect = QRectF(0, 0, text_box_width, box_height)
            elif h_align == Qt.AlignHCenter: 
                rect = QRectF(-text_box_width / 2.0, 0, text_box_width, box_height)
            else: 
                rect = QRectF(-text_box_width, 0, text_box_width, box_height)

            if use_latex:
                draw_latex_text(painter, label_text, anchor_x, anchor_y, 
                                font_family, font_size, h_align | Qt.AlignTop, 
                                use_siunitx=use_siunitx, rotate_angle=rotation_mpl)
            else:
                painter.save()
                painter.translate(anchor_x, anchor_y)
                painter.rotate(rotation_qt)
                painter.drawText(rect, h_align | Qt.AlignTop, label_text)
                painter.restore()

    painter.end()


# --- UI DIALOG WITH PREVIEW ---

class ColorbarSettingsDialog(QDialog):
    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.is_vector = layer.type() == QgsMapLayerType.VectorLayer
        self.setWindowTitle("Colorbar Export Settings")
        self.file_path = None
        self.bg_color = QColor(Qt.white)
        self._updating_preview = False
        self.system_latex_available = None
        self._warned_latex = False
        
        layout = QVBoxLayout()
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Orientation:"))
        self.combo_orientation = QComboBox()
        self.combo_orientation.addItems(["Vertical", "Horizontal"])
        self.combo_orientation.currentIndexChanged.connect(self.on_orientation_changed)
        h_layout.addWidget(self.combo_orientation)
        
        h_layout.addWidget(QLabel("Ticks:"))
        self.spin_ticks = QSpinBox()
        self.spin_ticks.setRange(2, 50)
        self.spin_ticks.setValue(5)
        self.spin_ticks.valueChanged.connect(self.update_preview)
        h_layout.addWidget(self.spin_ticks)
        
        h_layout.addWidget(QLabel("Align:"))
        self.combo_align = QComboBox()
        self.combo_align.addItems(["Left", "Center", "Right"])
        self.combo_align.currentIndexChanged.connect(self.update_preview)
        h_layout.addWidget(self.combo_align)
        
        h_layout.addWidget(QLabel("Spacing:"))
        self.spin_spacing = QSpinBox()
        self.spin_spacing.setRange(0, 100)
        self.spin_spacing.setValue(5)
        self.spin_spacing.valueChanged.connect(self.update_preview)
        h_layout.addWidget(self.spin_spacing)
        
        layout.addLayout(h_layout)

        h_text = QHBoxLayout()
        h_text.addWidget(QLabel("Font:"))
        self.combo_font = QFontComboBox()
        self.combo_font.setCurrentFont(QFont("Arial"))
        self.combo_font.currentFontChanged.connect(self.update_preview)
        h_text.addWidget(self.combo_font)
        
        h_text.addWidget(QLabel("Size:"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(6, 72)
        self.spin_size.setValue(10)
        self.spin_size.valueChanged.connect(self.update_preview)
        h_text.addWidget(self.spin_size)

        h_text.addWidget(QLabel("Decimals:"))
        self.spin_decimals = QSpinBox()
        self.spin_decimals.setRange(0, 10)
        self.spin_decimals.setValue(2)
        self.spin_decimals.valueChanged.connect(self.update_preview)
        h_text.addWidget(self.spin_decimals)
        layout.addLayout(h_text)
        
        # Split toggles into two rows for better spacing
        h_toggles1 = QHBoxLayout()
        self.check_sci = QCheckBox("Scientific Notation")
        self.check_sci.stateChanged.connect(self.update_preview)
        h_toggles1.addWidget(self.check_sci)
        
        self.check_latex = QCheckBox("Enable LaTeX Math (siunitx)")
        self.check_latex.stateChanged.connect(self.update_preview)
        h_toggles1.addWidget(self.check_latex)
        h_toggles1.addStretch()
        layout.addLayout(h_toggles1)
        
        h_toggles2 = QHBoxLayout()
        self.check_rotate = QCheckBox("Rotate Labels 45°")
        self.check_rotate.stateChanged.connect(self.update_preview)
        h_toggles2.addWidget(self.check_rotate)

        self.check_interpolate = QCheckBox("Interpolate Colors (Vector)")
        self.check_interpolate.stateChanged.connect(self.update_preview)
        if not self.is_vector:
            self.check_interpolate.setDisabled(True)
        h_toggles2.addWidget(self.check_interpolate)
        h_toggles2.addStretch()
        layout.addLayout(h_toggles2)
        
        h_labels = QHBoxLayout()
        h_labels.addWidget(QLabel("Title:"))
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("e.g. Elevation")
        self.edit_title.textChanged.connect(self.update_preview)
        h_labels.addWidget(self.edit_title)

        h_labels.addWidget(QLabel("Units:"))
        self.edit_units = QLineEdit()
        self.edit_units.setPlaceholderText("e.g. m/s or $m/s^2$")
        self.edit_units.textChanged.connect(self.update_preview)
        h_labels.addWidget(self.edit_units)
        layout.addLayout(h_labels)
        
        h_bg = QHBoxLayout()
        self.check_transparent = QCheckBox("Transparent Background")
        self.check_transparent.stateChanged.connect(self.toggle_transparent)
        h_bg.addWidget(self.check_transparent)
        
        self.btn_bg_color = QPushButton("Select Background Color...")
        self.btn_bg_color.setStyleSheet(f"background-color: {self.bg_color.name()}; border: 1px solid #999;")
        self.btn_bg_color.clicked.connect(self.select_bg_color)
        h_bg.addWidget(self.btn_bg_color)
        layout.addLayout(h_bg)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(540, 520) 
        self.preview_label.setStyleSheet("background-color: #e0e0e0; border: 1px inset #999;")
        layout.addWidget(self.preview_label)
        
        h_buttons = QHBoxLayout()
        self.btn_copy = QPushButton("Copy to Clipboard")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        h_buttons.addWidget(self.btn_copy)
        
        self.btn_save = QPushButton("Save As...")
        self.btn_save.clicked.connect(self.select_file)
        h_buttons.addWidget(self.btn_save)
        layout.addLayout(h_buttons)
        
        self.setLayout(layout)
        self.update_preview()
        
    def is_system_latex_available(self):
        """Checks if a full LaTeX distribution is accessible in the system PATH."""
        if self.system_latex_available is None:
            try:
                with mpl.rc_context({'text.usetex': True, 'text.latex.preamble': r'\usepackage{siunitx} \usepackage{amsmath}'}):
                    fig = Figure(dpi=72)
                    fig.text(0.5, 0.5, r"\SI{1}{m}")
                    buf = io.BytesIO()
                    fig.savefig(buf, format='svg')
                self.system_latex_available = True
            except Exception:
                self.system_latex_available = False
        return self.system_latex_available
        
    def on_orientation_changed(self):
        if self.combo_orientation.currentText() == "Horizontal":
            self.combo_align.setCurrentText("Center")
            self.combo_align.setEnabled(False)
        else:
            self.combo_align.setEnabled(True)
        self.update_preview()
        
    def select_bg_color(self):
        color = QColorDialog.getColor(self.bg_color, self, "Select Background Color")
        if color.isValid():
            self.bg_color = color
            self.btn_bg_color.setStyleSheet(f"background-color: {self.bg_color.name()}; border: 1px solid #999;")
            self.update_preview()
            
    def toggle_transparent(self):
        self.btn_bg_color.setDisabled(self.check_transparent.isChecked())
        self.update_preview()

    def extract_items(self):
        items = []
        if self.layer.type() == QgsMapLayerType.RasterLayer:
            ramp_shader = self.layer.renderer().shader().rasterShaderFunction()
            for item in ramp_shader.colorRampItemList():
                items.append(ColorItem(item.value, item.color, item.label))
                
        elif self.layer.type() == QgsMapLayerType.VectorLayer:
            ranges = self.layer.renderer().ranges()
            sorted_ranges = sorted(ranges, key=lambda r: r.lowerValue())
            
            if self.check_interpolate.isChecked():
                if sorted_ranges:
                    items.append(ColorItem(sorted_ranges[0].lowerValue(), sorted_ranges[0].symbol().color(), ""))
                    for r in sorted_ranges:
                        mid = (r.lowerValue() + r.upperValue()) / 2.0
                        items.append(ColorItem(mid, r.symbol().color(), r.label()))
                    items.append(ColorItem(sorted_ranges[-1].upperValue(), sorted_ranges[-1].symbol().color(), ""))
            else:
                for r in sorted_ranges:
                    color = r.symbol().color()
                    items.append(ColorItem(r.lowerValue(), color, r.label()))
                    items.append(ColorItem(r.upperValue(), color, r.label()))
                    
        return items
        
    def generate_current_image(self):
        orientation = self.combo_orientation.currentText()
        num_ticks = self.spin_ticks.value()
        font_family = self.combo_font.currentFont().family()
        font_size = self.spin_size.value()
        decimals = self.spin_decimals.value()
        title = self.edit_title.text()
        units = self.edit_units.text()
        use_scientific = self.check_sci.isChecked()
        is_transparent = self.check_transparent.isChecked()
        use_latex = self.check_latex.isChecked()
        rotate_labels = self.check_rotate.isChecked()
        text_alignment = self.combo_align.currentText()
        label_spacing = self.spin_spacing.value()
        
        is_discrete = self.is_vector and not self.check_interpolate.isChecked()
        
        use_siunitx = False
        if use_latex:
            if self.is_system_latex_available():
                use_siunitx = True
            else:
                if not getattr(self, '_warned_latex', False):
                    QMessageBox.warning(self, "LaTeX Not Found", 
                                        "System LaTeX distribution (e.g., TeX Live or MiKTeX) not found.\n\n"
                                        "Falling back to Matplotlib's built-in math parser. "
                                        "siunitx commands will be bypassed.")
                    self._warned_latex = True
        
        items = self.extract_items()
        
        plain_labels = generate_labels(items, num_ticks, decimals, units, use_scientific, use_latex=False, use_siunitx=False)
        labels = generate_labels(items, num_ticks, decimals, units, use_scientific, use_latex, use_siunitx)
        
        fm = QFontMetrics(QFont(font_family, font_size))
        max_w = max(fm.boundingRect(l).width() for l in plain_labels) if plain_labels else 0
        text_box_w = max_w + (font_size * 2.5 if use_latex else 10)
        
        img_w, img_h, bar_rect, offset_x, top_m, bar_t, bar_l, title_s = get_colorbar_dimensions(
            orientation, title, font_size, text_box_w, label_spacing, rotate_labels
        )
        
        image = QImage(int(img_w), int(img_h), QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        
        render_colorbar(image, items, labels, orientation, num_ticks, img_w, img_h, 
                        bar_rect, offset_x, top_m, bar_t, bar_l, title_s, text_box_w, label_spacing,
                        font_family, font_size, title, self.bg_color, is_transparent, 
                        use_latex, use_siunitx, text_alignment, is_discrete, rotate_labels)
        return image
        
    def update_preview(self):
        if self._updating_preview: return 
        self._updating_preview = True
        
        try:
            image = self.generate_current_image()
            pixmap = QPixmap.fromImage(image)
            self.preview_label.setPixmap(pixmap)
        except Exception as e:
            QMessageBox.warning(self, "Rendering Error", str(e))
        finally:
            self._updating_preview = False
        
    def copy_to_clipboard(self):
        try:
            image = self.generate_current_image()
            QApplication.clipboard().setImage(image)
            QMessageBox.information(self, "Success", "Colorbar copied to clipboard!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate image:\n{str(e)}")
        
    def select_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Colorbar", os.path.expanduser("~"), 
            "PNG Images (*.png);;TIFF Images (*.tif *.tiff);;SVG Vector Graphics (*.svg)"
        )
        if path:
            self.file_path = path
            self.accept()


# --- MAIN PLUGIN CLASS ---

class ColorbarExporter:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None

    def initGui(self):
        self.action = QAction("Export Colorbar", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToRasterMenu("Colorbar Exporter", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginRasterMenu("Colorbar Exporter", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(self.iface.mainWindow(), "Error", "Please select a layer first.")
            return

        is_valid = False
        
        if layer.type() == QgsMapLayerType.RasterLayer:
            renderer = layer.renderer()
            if isinstance(renderer, QgsSingleBandPseudoColorRenderer):
                if isinstance(renderer.shader().rasterShaderFunction(), QgsColorRampShader):
                    is_valid = True
                    
        elif layer.type() == QgsMapLayerType.VectorLayer:
            renderer = layer.renderer()
            if isinstance(renderer, QgsGraduatedSymbolRenderer) and renderer.ranges():
                is_valid = True
                
        if not is_valid:
            QMessageBox.warning(self.iface.mainWindow(), "Error", 
                                "Please select a Raster (Pseudocolor) or Vector (Graduated) layer with a valid color ramp.")
            return

        dialog = ColorbarSettingsDialog(layer, self.iface.mainWindow())
        if dialog.exec_():
            self.save_colorbar(dialog)

    def save_colorbar(self, dialog):
        try:
            orientation = dialog.combo_orientation.currentText()
            num_ticks = dialog.spin_ticks.value()
            font_family = dialog.combo_font.currentFont().family()
            font_size = dialog.spin_size.value()
            decimals = dialog.spin_decimals.value()
            title = dialog.edit_title.text()
            units = dialog.edit_units.text()
            use_scientific = dialog.check_sci.isChecked()
            is_transparent = dialog.check_transparent.isChecked()
            bg_color = dialog.bg_color
            use_latex = dialog.check_latex.isChecked()
            rotate_labels = dialog.check_rotate.isChecked()
            text_alignment = dialog.combo_align.currentText()
            label_spacing = dialog.spin_spacing.value()
            file_path = dialog.file_path

            is_discrete = dialog.is_vector and not dialog.check_interpolate.isChecked()
            use_siunitx = dialog.is_system_latex_available() if use_latex else False

            items = dialog.extract_items()
            
            plain_labels = generate_labels(items, num_ticks, decimals, units, use_scientific, use_latex=False, use_siunitx=False)
            labels = generate_labels(items, num_ticks, decimals, units, use_scientific, use_latex, use_siunitx)
            
            fm = QFontMetrics(QFont(font_family, font_size))
            max_w = max(fm.boundingRect(l).width() for l in plain_labels) if plain_labels else 0
            text_box_w = max_w + (font_size * 2.5 if use_latex else 10)

            img_w, img_h, bar_rect, offset_x, top_m, bar_t, bar_l, title_s = get_colorbar_dimensions(
                orientation, title, font_size, text_box_w, label_spacing, rotate_labels
            )
            
            is_svg = os.path.splitext(file_path)[1].lower() == '.svg'

            if is_svg:
                generator = QSvgGenerator()
                generator.setFileName(file_path)
                generator.setSize(QSize(int(img_w), int(img_h)))
                generator.setViewBox(QRectF(0, 0, img_w, img_h))
                paint_device = generator
            else:
                image = QImage(int(img_w), int(img_h), QImage.Format_ARGB32)
                image.fill(Qt.transparent)
                paint_device = image
            
            render_colorbar(paint_device, items, labels, orientation, num_ticks, img_w, img_h, 
                            bar_rect, offset_x, top_m, bar_t, bar_l, title_s, text_box_w, label_spacing,
                            font_family, font_size, title, bg_color, is_transparent, 
                            use_latex, use_siunitx, text_alignment, is_discrete, rotate_labels)
            
            if is_svg:
                self.iface.messageBar().pushMessage("Success", f"SVG saved to {file_path}", level=0)
            else:
                if image.save(file_path):
                    self.iface.messageBar().pushMessage("Success", f"Image saved to {file_path}", level=0)
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "Error", f"Failed to save colorbar:\n{str(e)}")