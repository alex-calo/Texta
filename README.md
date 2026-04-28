TEXTA --Created by Alex Calò - 2025--
# 📄 Document Camera OCR Prototype

## 🧩 Summary  
**Document Camera OCR** is a Python-based prototype designed to capture, process, and analyze text from static images. It integrates **Tesseract OCR** with intelligent preprocessing, **dictionary validation**, and **spelling correction** to improve text recognition accuracy.  

The app is built with a **modular architecture** using **PyQt5** for the GUI, **OpenCV** for image handling, and **pytesseract** for text extraction.

---

## ⚙️ Features
- Static image OCR capture  
- Image preprocessing for better OCR results  
- Integrated spelling correction and dictionary validation  
- Export recognized text to **PDF**  
- Modular code structure for easy extension and testing  

---

## 🧰 Requirements

To install dependencies, use:

```bash
pip install -r requirements.txt
```

**Dependencies:**
```
PyQt5==5.15.9
opencv-python==4.8.1.78
pytesseract==0.3.10
fpdf==1.7.2
numpy>=1.24.3
Pillow==9.5.0
pyspellchecker==0.7.2
language-tool-python==2.7.1
```

> **Note:**  
> Make sure [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) is installed and available in your system’s PATH.

---

## 🗂️ Project Structure

```
Texta\
 
├── main.py 
├── requirements.txt 
├── config.py
├── run.py
├── assets\
            ├── ── ── texta.png
├── core\
            ├── ── ── _init_.py
            ├── ── ──  camera_thread.py
            ├── ── ── ocr_engine.py
            ├── ── ── pdf_generator.py
├── gui\
            ├── ── ── _init_.py
            ├── ── ──  main_window.py
            ├── ── ── widgets.py
├── utils\
            ├── ── ── _init_.py
            ├── ── ──  camera_utils.py
            ├── ── ── file_utils.py
            ├── ── ── image_processing.py
            ├── ── ── ocr_trainer.py
            ├── ── ── word_list.txt
```

---

## 🚀 How to Run

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alex-calo/OCR-Software
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app:**
   ```bash
   python main.py
   ```
   or
   ```bash
   python run.py
   ```

---

## 📜 License
This project is open source and distributed under the **MIT License**.  
See the [LICENSE](LICENSE) file for more information.
