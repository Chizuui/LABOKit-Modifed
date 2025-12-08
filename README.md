# LABOKit

<img width="1365" height="416" alt="Image" src="https://github.com/user-attachments/assets/f4ab1e1b-de1c-4a0f-a648-25b210f0ea4f" />

**LABOKit** is a desktop tool for offline image background removal and image upscaling on Windows. Built with Python (PySide6), it aims to provide a fast, simple, and user-friendly batch-processing workflow with a retro "Steins;Gate" divergence meter aesthetic.

> *"El Psy Kongroo."*

## Features

* User-Friendly & Fast: Designed for simplicity and speed. The interface is clean and easy to understand—just load your images and click.
* Batch Background Removal: Powered by `rembg` (U^2-Net).
* Batch Upscaling: Powered by `Real-ESRGAN-ncnn-vulkan`.
* World Line Meter: Visual decoration displaying divergence numbers.
* Plugin System: Extend functionality using `.kit` files.
* Offline Mode: All processing is done locally on your machine.

## 📥 Download (Portable Version)

1.  Go to the **[Releases](https://github.com/wagakano/LABOKit/releases)** page.
2.  Download the `LABOKit_v1.2.zip` (or latest version).
3.  Extract the zip file.
4.  Run `LABOKit.exe`.

> **Note:** The portable version is larger in size because it bundles the Python engine and necessary libraries.

## 🛠️ Installation

### Prerequisites
* Python 3.10+
* Windows (Recommended)

### Setup
1.  Clone the repository:
    ```bash
    git clone [https://github.com/wagakano/LABOKit.git](https://github.com/wagakano/LABOKit.git)
    cd LABOKit
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Model Setup (Important)**
    
    * **Background Removal (`rembg`):**
        * **Automatic:** The application will automatically download the required model (`u2net.onnx`, ~170MB) into the `models/` folder on the first run.
        * **Manual (Offline):** If you prefer manual setup, download [u2net.onnx](https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx), create a folder named `models` in the project root, and place the file there (`LABOKit/models/u2net.onnx`).

    * **Upscaler (`Real-ESRGAN`):**
        * Download `realesrgan-ncnn-vulkan.exe` and the models (e.g., `realesrgan-x4plus.bin`, etc.).
        * Place them in the `realesrgan/` folder inside the project directory.
        * *(Note: Ensure the executable path matches the setup in `main.py`)*

4.  Run the application:
    ```bash
    python main.py
    ```

## 🧩 How to Use

### 1. BG Remover
* Drag & drop or add images to the list.
* Select a preset (Standard/Medium/High).
* Click **Remove BG**. Output will be saved in `LABOKit_BG` folder.

### 2. Upscaler
* Add images to the Upscaler tab.
* Choose Scale (2x/4x) and Model (General/Anime).
* Click **Upscale**. Output will be saved in `LABOKit_UP` folder.

## Plugins
LABOKit supports `.kit` plugins. Place your plugin files in the `plugins/` directory and load them via the **Config** menu.

## 📄 License & Credits
See [LABOKit_NOTICE.txt](LABOKit_NOTICE.txt) for detailed license information regarding third-party components (rembg, Real-ESRGAN, Qt, etc.).

**LABOKit** is a fan-inspired tool and is not affiliated with the creators of Steins;Gate.