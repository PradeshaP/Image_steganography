
# 🔐 Image Steganography — CS23601 Mini Project

> **Secure image steganography using AES-128 encryption, SVD decomposition & compression, and LSB pixel embedding.**

---

## 📌 Project Overview

This project implements a **9-step hybrid steganography pipeline** that:

1. Takes a **cover image** and a **secret text message** as input
2. **Encrypts** the message using AES-128 CBC mode
3. **Preprocesses** the cover image (grayscale, square crop)
4. Applies **full SVD decomposition** (A = U · diag(S) · Vt)
5. Performs **SVD compression** (top-k = 50 singular values retained)
6. **Embeds** encrypted bits into pixel LSBs
7. **Reconstructs** and saves lossless BMP stego image
8. **Extracts** hidden bits from the stego image
9. **Decrypts** to recover the original message

### 📊 Key Results

| Metric | Value | Target |
|--------|-------|--------|
| PSNR | **78.95 dB** | > 40 dB ✅ |
| SSIM | **1.000000** | ≈ 1.0 ✅ |
| MSE | **0.000828** | ≈ 0 ✅ |
| SVD Compression | **6×** | — |

---

## 📁 Repository Structure

```
steganography_project/
│
├── README.md                        ← You are here
│
├── demo/
│   ├── steganography_complete.py    ← Main application code
│   └── README.md                    ← How to run the demo
│
├── latex/
│   ├── ieee_steganography.tex       ← IEEE conference paper (LaTeX)
│   └── README.md                    ← How to compile the paper
│
└── assets/
    └── README.md                    ← Screenshots and demo video info
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/steganography_project.git
cd steganography_project
```

### 2. Install dependencies
```bash
pip install pycryptodome gradio numpy Pillow scikit-image matplotlib
```

### 3. Run the application
```bash
cd demo
python steganography_complete.py
```

### 4. Open the web UI
The terminal will print a local URL like:
```
Running on local URL: http://127.0.0.1:7860
Running on public URL: https://xxxxxxxx.gradio.live
```
Open either link in your browser.

---

## 🔒 How to Embed a Secret Message

1. Go to the **🔒 Embed Secret** tab
2. Upload any cover image (JPG, PNG, BMP)
3. Type your secret message in the text box
4. Click **Encrypt & Embed**
5. Download the **Stego Image (.bmp)** and **Key File (.pkl)**
6. ⚠️ Keep both files — you need both to recover the message

## 🔓 How to Extract the Message

1. Go to the **🔓 Extract Secret** tab
2. Upload the **Stego Image (.bmp)** using the File uploader
3. Upload the **Key File (.pkl)**
4. Click **Extract & Decrypt**
5. The original message appears in the output box

> ⚠️ **Important:** Always use the File uploader (not Image widget) for the stego image. The Image widget re-encodes the file and destroys the hidden bits.

---

## 🛠️ Dependencies

```
pycryptodome    — AES-128 CBC encryption
numpy           — SVD via numpy.linalg.svd
Pillow          — Image loading and BMP saving
scikit-image    — SSIM quality metric
matplotlib      — Comparison plot generation
gradio          — Web-based user interface
```

Install all at once:
```bash
pip install pycryptodome gradio numpy Pillow scikit-image matplotlib
```

---

## 📐 System Requirements

- Python 3.8 or higher
- 4 GB RAM minimum (for SVD on large images)
- Any OS: Windows / macOS / Linux

---

## 📄 Paper

The IEEE conference paper is in the `latex/` folder.
See `latex/README.md` for compilation instructions.

---

## 📹 Demo Video

A 3–5 minute voice-over demo video is available in the `assets/` folder.
It covers:
- Running the application
- Embedding a secret message
- Downloading the stego image and key file
- Extracting and recovering the message
- Viewing the quality metrics and comparison plot

---

## 📚 References

1. P. K. Pooranakala and V. Jaitly, "Securing medical images using compression techniques with encryption and image steganography," CONIT 2023.
2. J. Verma et al., "Fusion of cryptography and steganography with LSB for secure data hiding," SUSTAINED 2024.
3. N. N. Murthy and V. Hegde, "Secure data hiding: A comprehensive LSB-based steganography framework," IEEE 2026.
4. R. R. Isnanto et al., "Robustness of steganography image method using dynamic LSB," ISRITI 2018.
5. T. Pevny and J. Fridrich, "Multiclass detector of steganographic methods for JPEG format," IEEE TIFS 2008.

---

## 📝 License

This project was developed as part of CS23601 Mini Project.
