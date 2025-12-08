# LABOKit 

![LABOKit Banner](https://via.placeholder.com/800x200.png?text=LABOKit+Preview)

**LABOKit** is a desktop tool for offline image background removal and image upscaling on Windows. Built with Python (PySide6), it aims to provide a fast, simple, and user-friendly batch-processing workflow with a retro "Steins;Gate" divergence meter aesthetic.

> *"El Psy Kongroo."*

## Features

* Batch Background Removal: Powered by `rembg` (U^2-Net).
* Batch Upscaling: Powered by `Real-ESRGAN-ncnn-vulkan`.
* World Line Meter: Visual decoration displaying divergence numbers.
* Plugin System: Extend functionality using `.kit` files.
* Offline Mode: All processing is done locally on your machine.

## 📥 Download (Portable Version)

1.  Go to the **[Releases](../../releases)** page.
2.  Download the `LABOKit_v1.2.zip` (or latest version).
3.  Extract the zip file.
4.  Run `LABOKit.exe`.

## Installation

### Prerequisites
* Python 3.10+
* Windows (Recommended)

### Setup
1.  Clone the repository:
    ```bash
    git clone [https://github.com/username/LABOKit.git](https://github.com/username/LABOKit.git)
    cd LABOKit
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Important**: Real-ESRGAN Setup
    * Download `realesrgan-ncnn-vulkan.exe` and the models.
    * Place them in the `realesrgan/` folder inside the project directory.
    * *(Note: Ensure the executable path matches the setup in `main.py`)*

4.  Run the application:
    ```bash
    python main.py
    ```

## How to Use

### 1. BG Remover
* Drag & drop or add images to the list.
* Select a preset (Standard/Medium/High).
* Click **Remove BG**. output will be saved in `LABOKit_BG` folder.

### 2. Upscaler
* Add images to the Upscaler tab.
* Choose Scale (2x/4x) and Model (General/Anime).
* Click **Upscale**. Output will be saved in `LABOKit_UP` folder.

## Plugins
LABOKit supports `.kit` plugins. Place your plugin files in the `plugins/` directory and load them via the **Config** menu.

## License & Credits
See [LABOKit_NOTICE.txt](LABOKit_NOTICE.txt) for detailed license information regarding third-party components (rembg, Real-ESRGAN, Qt, etc.).

**LABOKit** is a fan-inspired tool and is not affiliated with the creators of Steins;Gate.