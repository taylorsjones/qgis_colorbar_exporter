# ![My Image](colorbar_plugin/icon.png) QGIS Colorbar Exporter 

A powerful, highly customizable QGIS 3 plugin to extract color ramps from Raster and Vector layers and export them as publication-ready colorbars. 

This plugin provides a fully interactive GUI with a live preview to get your colorbar looking exactly how you need it.

## ✨ Features

* **Universal Compatibility:** Works with both **Raster Layers** (Singleband Pseudocolor) and **Vector Layers** (Graduated styling).
* **Live Preview:** See your changes update in real-time before saving.
* **Multiple Formats:** Export to **PNG**, **TIFF**, or scalable vector **SVG**.
* **Quick Copy:** A dedicated "Copy to Clipboard" button allows you to instantly paste the colorbar into Word, PowerPoint, or image editors.
* **Vector Handling:** Choose between smooth gradients or discrete, hard-edged color blocks for Graduated vector layers.
* **Advanced Typography & Layout:**
  * Custom Fonts, Font Sizes, and Decimal places.
  * Adjust spacing between ticks and labels.
  * Rotate text 45° to fit long numbers.
  * Left, Center, or Right text justification.
  * Horizontal or Vertical orientations.
* **Scientific & Academic Ready:** 
  * Add custom Titles and Unit strings.
  * Toggle Scientific Notation.
  * **Native LaTeX Support:** Render complex math (e.g., `$\mu g/m^3$`). If a system LaTeX distribution (TeX Live / MiKTeX) is found in your PATH, it automatically uses the `siunitx` package for flawless scientific unit formatting. (Gracefully falls back to Matplotlib's built-in math parser if LaTeX is not installed).
* **Custom Backgrounds:** Choose a solid background color or export with full transparency.

## 📦 Installation

Since this plugin is manually installed (not yet in the official QGIS repository), follow these steps:

1. Download or clone this repository. You should have a folder containing:
   * `__init__.py`
   * `colorbar_plugin.py`
   * `metadata.txt`
   * `icon.png`
2. Rename the folder to `ColorbarExporter`.
3. Open QGIS. Go to **Settings > User Profiles > Open Active Profile Folder**.
4. In the file browser that opens, navigate into `python/plugins/`.
5. Move your `ColorbarExporter` folder into the `plugins` directory.
6. Restart QGIS (or use the *Plugin Reloader* plugin).
7. Go to **Plugins > Manage and Install Plugins...**, select the **Installed** tab, and check the box next to **Colorbar Exporter** to enable it.

## 🚀 Usage

1. Load a Raster layer and style it using **Singleband pseudocolor**, OR load a Vector layer and style it using **Graduated** symbols.
2. Ensure the layer is selected (highlighted) in your QGIS Layers Panel.
3. Click the **Colorbar Exporter icon** in your QGIS Toolbar (or navigate to `Raster > Colorbar Exporter > Export Colorbar`).
4. A dialog will appear with a live preview. Adjust your orientation, ticks, typography, title, and units.
5. Click **Copy to Clipboard** to paste it immediately, or **Save As...** to export your PNG, TIFF, or SVG.

## 🧮 A Note on LaTeX Formatting

If you check **"Enable LaTeX Math"**:
* You can write standard text normally.
* To render math symbols, wrap them in dollar signs `$ ... $` (e.g., `Elevation ($m$)`).
* **If you have a full LaTeX distribution** (like TeX Live or MiKTeX) installed and accessible in your system `PATH`, the plugin will detect it and utilize the `siunitx` package for rendering strings.
* **If you do not have LaTeX installed**, the plugin will issue a warning and seamlessly fall back to Matplotlib's internal `MathText` parser, which still allows for standard mathematical symbols but bypasses `siunitx`.

## 🐛 Troubleshooting

* **Plugin won't open / Layer error:** Ensure you actually have a valid styling applied to the layer. The plugin requires continuous color ramps (Rasters) or graduated symbol ranges (Vectors). Categorized or Single Symbol layers do not have colorbars to extract.
* **SVG text looks wrong in Illustrator:** If using LaTeX, the text is exported as vector paths to ensure it never changes shape or requires specific fonts to be installed on the destination computer. 

## 📄 License

This project is licensed under the MIT License.
