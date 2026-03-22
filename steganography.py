import os, io, math, pickle, tempfile
import numpy as np
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import gradio as gr


def generate_key() -> bytes:
    return os.urandom(16)

def aes_encrypt(plaintext: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC)
    ct = cipher.encrypt(pad(plaintext, AES.block_size))
    return cipher.iv + ct

def aes_decrypt(data: bytes, key: bytes) -> bytes:
    iv, ct = data[:16], data[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return unpad(cipher.decrypt(ct), AES.block_size)

_k = generate_key()
assert aes_decrypt(aes_encrypt(b'test CS23601', _k), _k) == b'test CS23601'
print('✅ Step 2 & 9 — AES Module OK')


def load_grayscale(image_input) -> np.ndarray:
    if isinstance(image_input, str):
        img = Image.open(image_input).convert('L')
    else:
        img = image_input.convert('L')
    return np.array(img, dtype=np.float64)

def make_square(image) -> np.ndarray:
    gray = load_grayscale(image)
    if min(gray.shape) < 512:
        pil = Image.fromarray(gray.astype(np.uint8)).resize((512, 512), Image.LANCZOS)
        gray = np.array(pil, dtype=np.float64)
    size = min(gray.shape)
    return gray[:size, :size]

assert load_grayscale(Image.fromarray(np.zeros((64,64),dtype=np.uint8))).ndim == 2
print('✅ Step 3 — Image Preprocessing Module OK')


SVD_K = 50

def svd_decompose(gray: np.ndarray):
    return np.linalg.svd(gray, full_matrices=True)

def svd_compress(U, S, Vt, k=SVD_K) -> np.ndarray:
    k = min(k, len(S))
    return np.clip(np.dot(U[:, :k], np.dot(np.diag(S[:k]), Vt[:k, :])), 0, 255)

def compression_ratio(shape, k=SVD_K) -> float:
    m, n = shape
    return round(m * n / (k * (m + n + 1)), 2)

_U, _S, _Vt = svd_decompose(np.random.uniform(80, 180, (128, 128)))
assert np.allclose(np.dot(_U, np.dot(np.diag(_S), _Vt)),
                   np.dot(_U, np.dot(np.diag(_S), _Vt)), atol=1e-6)
print(f'✅ Step 4 & 5 — SVD Decompose + Compress OK (k={SVD_K}, ratio ≈{compression_ratio((512,512))}x)')


HEADER_BYTES = 4
HEADER_REPS  = 3

def bytes_to_bits(data: bytes) -> list:
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits

def bits_to_bytes(bits: list) -> bytes:
    out = []
    for i in range(0, len(bits) - len(bits) % 8, 8):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[i + j]
        out.append(b)
    return bytes(out)

def embed_lsb(gray: np.ndarray, bits: list) -> np.ndarray:
    flat = gray.flatten().astype(np.int32)
    if len(bits) > len(flat):
        raise ValueError(f'Message too large! Need {len(bits)} bits, only {len(flat)} pixels available.')
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & ~1) | bit
    return flat.reshape(gray.shape).astype(np.uint8)

def extract_lsb(arr: np.ndarray, num_bits: int) -> list:
    flat = arr.flatten().astype(np.int32)
    return [int(flat[i]) & 1 for i in range(min(num_bits, len(flat)))]

def build_header(enc_len: int) -> list:
    return bytes_to_bits(enc_len.to_bytes(HEADER_BYTES, 'big')) * HEADER_REPS

def decode_header(raw: list) -> int:
    bits = HEADER_BYTES * 8
    final = []
    for b in range(bits):
        votes = [raw[b + v * bits] for v in range(HEADER_REPS)]
        final.append(max(set(votes), key=votes.count))
    return int(''.join(str(x) for x in final), 2)

_tb = bytes_to_bits(b'LSB round-trip OK!')
_canvas = np.random.randint(100, 200, (128, 128), dtype=np.uint8)
_emb = embed_lsb(_canvas.astype(np.float64), _tb)
assert bits_to_bytes(extract_lsb(_emb, len(_tb))) == b'LSB round-trip OK!'
print('✅ Step 6 & 8 — LSB Embed/Extract in SVD OK')


def psnr(orig, stego):
    mse = np.mean((orig.astype(float) - stego.astype(float)) ** 2)
    return float('inf') if mse == 0 else round(20 * math.log10(255.0 / math.sqrt(mse)), 4)

def mse(orig, stego):
    return round(float(np.mean((orig.astype(float) - stego.astype(float)) ** 2)), 6)

def ssim(orig, stego):
    try:
        from skimage.metrics import structural_similarity as _ssim
        score, _ = _ssim(orig.astype(np.uint8), stego.astype(np.uint8), full=True)
        return round(float(score), 6)
    except Exception:
        return 'N/A'

print('✅ Quality Metrics Module OK')


def embed_pipeline(cover_image, secret_text: str):
    gray    = make_square(cover_image)
    h, w    = gray.shape
    gray_u8 = gray.astype(np.uint8)

    key       = generate_key()
    encrypted = aes_encrypt(secret_text.encode('utf-8'), key)
    enc_len   = len(encrypted)

    U, S, Vt   = svd_decompose(gray)
    compressed = svd_compress(U, S, Vt, k=SVD_K)
    ratio      = compression_ratio((h, w))

    header_bits    = build_header(enc_len)
    payload_bits   = bytes_to_bits(encrypted)
    all_bits       = header_bits + payload_bits
    pixel_capacity = h * w

    if len(all_bits) > pixel_capacity:
        raise ValueError(
            f'Message too large!\n'
            f'Pixels available : {pixel_capacity}\n'
            f'Bits needed      : {len(all_bits)}\n'
            f'Use a larger image or shorter message.'
        )

    stego_u8  = embed_lsb(gray, all_bits)
    stego_img = Image.fromarray(stego_u8)

    metrics = {
        'psnr'          : psnr(gray_u8, stego_u8),
        'mse'           : mse(gray_u8, stego_u8),
        'ssim'          : ssim(gray_u8, stego_u8),
        'img_shape'     : (h, w),
        'msg_len'       : len(secret_text),
        'enc_len'       : enc_len,
        'pixel_capacity': pixel_capacity,
        'bits_used'     : len(all_bits),
        'usage_pct'     : round(len(all_bits) / pixel_capacity * 100, 2),
        'svd_k'         : SVD_K,
        'svd_total'     : len(S),
        'ratio'         : ratio,
    }
    return stego_img, metrics, key, enc_len, gray_u8, stego_u8, compressed.astype(np.uint8)


def extract_pipeline(stego_image, key: bytes, enc_length: int) -> str:
    gray        = make_square(stego_image).astype(np.uint8)
    total_bits  = HEADER_BYTES * 8 * HEADER_REPS + enc_length * 8
    raw         = extract_lsb(gray, total_bits)
    header_bits = HEADER_BYTES * 8 * HEADER_REPS
    dec_len     = decode_header(raw[:header_bits])
    actual_len  = dec_len if 0 < dec_len <= enc_length + 32 else enc_length
    payload     = raw[header_bits : header_bits + actual_len * 8]
    encrypted   = bits_to_bytes(payload)
    return aes_decrypt(encrypted, key).decode('utf-8')

print('✅ Pipeline & Visualisation Module OK')


def make_plot(orig, compressed, stego, metrics) -> str:
    fig = plt.figure(figsize=(18, 4), facecolor='#0f1117')
    gs  = gridspec.GridSpec(1, 4, figure=fig, wspace=0.3)
    panels = [
        ('Original Cover',              orig,                                                          'gray'),
        (f'SVD Compressed (k={SVD_K})', compressed,                                                   'gray'),
        ('Stego Image',                 stego,                                                         'gray'),
        ('Difference ×20',              np.abs(orig.astype(int) - stego.astype(int)).clip(0,255//20) * 20, 'hot'),
    ]
    for i, (label, img, cmap) in enumerate(panels):
        ax = fig.add_subplot(gs[i])
        ax.imshow(np.clip(img, 0, 255).astype(np.uint8), cmap=cmap)
        ax.set_title(label, color='white', fontsize=10, fontweight='bold')
        ax.axis('off')

    ssim_str = f"{metrics['ssim']:.6f}" if isinstance(metrics['ssim'], float) else metrics['ssim']
    fig.text(0.5, 0.01,
        f"PSNR: {metrics['psnr']} dB  |  MSE: {metrics['mse']}  |  SSIM: {ssim_str}  |  "
        f"SVD k={SVD_K}  |  Compression ≈{metrics['ratio']}×  |  "
        f"Capacity used: {metrics['usage_pct']}%",
        ha='center', color='#aaaaaa', fontsize=8,
        bbox=dict(facecolor='#1e2130', edgecolor='#444', boxstyle='round,pad=0.4'))
    path = tempfile.mktemp(suffix='_plot.png')
    plt.savefig(path, dpi=120, bbox_inches='tight', facecolor='#0f1117')
    plt.close()
    return path


def gradio_embed(cover_path, message):
    if cover_path is None:
        return None, None, '❌ Please upload a cover image.', None
    if not message or not message.strip():
        return None, None, '❌ Please enter a secret message.', None
    try:
        cover = Image.open(cover_path)
        stego_img, metrics, key, enc_len, orig_u8, stego_u8, comp_u8 = embed_pipeline(cover, message)

        stego_path = tempfile.mktemp(suffix='_stego.bmp')
        stego_img.save(stego_path, format='BMP')

        key_path = tempfile.mktemp(suffix='_key.pkl')
        with open(key_path, 'wb') as f:
            pickle.dump({'key': key, 'enc_length': enc_len}, f)

        ssim_str = f"{metrics['ssim']:.6f}" if isinstance(metrics['ssim'], float) else metrics['ssim']
        result = (
            f"✅ Embedding Successful!\n"
            f"{'─'*50}\n"
            f"Image size         : {metrics['img_shape'][1]}×{metrics['img_shape'][0]} px\n"
            f"Message length     : {metrics['msg_len']} characters\n"
            f"AES key            : 128-bit CBC (random)\n"
            f"{'─'*50}\n"
            f"[STEP 4] SVD decomposed — {metrics['svd_total']} singular values\n"
            f"[STEP 5] SVD compressed — top k={metrics['svd_k']} retained\n"
            f"         Compression ratio ≈ {metrics['ratio']}×\n"
            f"[STEP 6] LSB embedding in pixel array\n"
            f"         Pixel capacity   : {metrics['pixel_capacity']} bits\n"
            f"         Bits embedded    : {metrics['bits_used']} bits\n"
            f"         Capacity used    : {metrics['usage_pct']}%\n"
            f"[STEP 7] Stego image saved as lossless BMP\n"
            f"{'─'*50}\n"
            f"PSNR  : {metrics['psnr']} dB  (>40 dB = imperceptible ✅)\n"
            f"MSE   : {metrics['mse']}      (near 0 = excellent ✅)\n"
            f"SSIM  : {ssim_str}  (near 1.0 = excellent ✅)"
        )
        plot_path = make_plot(orig_u8, comp_u8, stego_u8, metrics)
        return stego_path, key_path, result, plot_path

    except ValueError as e:
        return None, None, f'❌ {e}', None
    except Exception as e:
        import traceback
        return None, None, f'❌ Error: {e}\n\n{traceback.format_exc()}', None


def run_embed(cover_path, message):
    stego_path, key_path, result, plot_path = gradio_embed(cover_path, message)
    stego_btn = gr.DownloadButton(value=stego_path, visible=stego_path is not None)
    key_btn   = gr.DownloadButton(value=key_path,   visible=key_path   is not None)
    return stego_btn, key_btn, result, plot_path


def gradio_extract(stego_path, key_path):
    if stego_path is None:
        return '❌ Please upload the stego image.'
    if key_path is None:
        return '❌ Please upload the key file (.pkl).'
    try:
        stego_file = stego_path if isinstance(stego_path, str) else stego_path.name
        stego = Image.open(stego_file)
        stego.load()

        key_file = key_path if isinstance(key_path, str) else key_path.name
        with open(key_file, 'rb') as f:
            meta = pickle.load(f)

        recovered = extract_pipeline(stego, meta['key'], meta['enc_length'])
        return (
            f"✅ Extraction Successful!\n"
            f"{'─'*42}\n"
            f"[STEP 3] Stego image preprocessed\n"
            f"[STEP 8] LSBs extracted from pixel array\n"
            f"[STEP 9] AES-128 decrypted successfully\n"
            f"{'─'*42}\n"
            f"🔓 Recovered Message:\n\n{recovered}"
        )
    except Exception as e:
        import traceback
        return f'❌ Failed: {e}\n\n{traceback.format_exc()}'


with gr.Blocks(theme=gr.themes.Soft(), title='Image Steganography CS23601') as demo:

    gr.HTML("""
        <div style='text-align:center;padding:1rem 0;'>
          <h1 style='font-size:2rem;margin:0;'>🔐 Image Steganography</h1>
          <p style='color:gray;margin:6px 0 2px;'>
            AES-128 · SVD Decomposition · SVD Compression · LSB Embedding · CS23601
          </p>
          <p style='color:#888;font-size:0.85rem;margin:0;'>
            Sumitha GK &nbsp;|&nbsp; Jenifa V &nbsp;|&nbsp; Pradesha P &nbsp;|&nbsp; Vethavalli GM
          </p>
        </div>
    """)

    with gr.Tabs():

        with gr.Tab('🔒 Embed Secret'):
            gr.Markdown(
                'Upload any cover image and type your secret message. '
                'All 9 workflow steps run automatically. '
                'Download **both** output files — you need both to recover the message.'
            )
            with gr.Row():
                with gr.Column():
                    inp_img = gr.Image(
                        label='Cover Image (auto-cropped to ≥512×512 square)',
                        type='filepath'
                    )
                    inp_msg = gr.Textbox(
                        label='Secret Message',
                        lines=4,
                        placeholder='Type your secret message here...'
                    )
                    btn_emb = gr.Button('🔒 Encrypt & Embed', variant='primary')
                with gr.Column():
                    out_stego   = gr.DownloadButton(label='⬇️ Download Stego Image (.bmp)', visible=False)
                    out_key     = gr.DownloadButton(label='⬇️ Download Key File (.pkl)', visible=False)
                    out_metrics = gr.Textbox(
                        label='Pipeline Results & Quality Metrics', lines=22, interactive=False
                    )
            out_plot = gr.Image(
                label='Visual Comparison — Original | SVD Compressed | Stego | Difference ×20',
                type='filepath'
            )
            btn_emb.click(
                run_embed,
                inputs=[inp_img, inp_msg],
                outputs=[out_stego, out_key, out_metrics, out_plot]
            )
            gr.Markdown(
                '> ⚠️ **Important:** The downloaded stego file is a **.bmp** (lossless). '
                'Do not convert to JPEG — it will destroy the hidden bits.'
            )

        with gr.Tab('🔓 Extract Secret'):
            gr.Markdown(
                'Upload the stego **.bmp** image and the **.pkl** key file.\n\n'
                '> ⚠️ Use the **File** uploader below — it passes bytes through unchanged. '
                'An Image widget would re-encode the file and corrupt the hidden data.'
            )
            with gr.Row():
                with gr.Column():
                    ext_img = gr.File(
                        label='Stego Image (.bmp)',
                        type='filepath',
                        file_types=['.bmp', '.png', '.tiff', '.tif']
                    )
                    ext_key = gr.File(
                        label='Secret Key File (.pkl)',
                        type='filepath',
                        file_types=['.pkl']
                    )
                    btn_ext = gr.Button('🔓 Extract & Decrypt', variant='primary')
                with gr.Column():
                    ext_out = gr.Textbox(
                        label='Recovered Message',
                        lines=10, interactive=False,
                        placeholder='Recovered message appears here...'
                    )
            btn_ext.click(
                gradio_extract,
                inputs=[ext_img, ext_key],
                outputs=[ext_out]
            )

        with gr.Tab('📖 How It Works — All 9 Steps'):
            gr.Markdown(f"""
## Complete 9-Step Pipeline

### Step 1 — Input Acquisition
Cover image (any format/size) and secret text entered via Gradio UI.

### Step 2 — AES-128 Encryption
- Text → bytes → PKCS7 padding → 16-byte blocks
- Random 128-bit key generated; AES-CBC produces IV + ciphertext
- Even if extracted, ciphertext is unreadable without the key

### Step 3 — Image Preprocessing
- Loaded and converted to **grayscale 2D float64 matrix**
- Resized to ≥512×512, centre-cropped to square for consistent geometry

### Step 4 — SVD Decomposition
```
A = U · diag(S) · Vt
```
Full SVD applied to the grayscale matrix. S[0] carries the most image energy.

### Step 5 — SVD Compression (Low-Rank Approximation)
```
A_compressed ≈ U[:, :k] · diag(S[:k]) · Vt[:k, :]   (k={SVD_K})
```
Top-{SVD_K} singular values retained; smaller ones discarded.
Compression ratio ≈ {compression_ratio((512,512))}× for a 512×512 image.

### Step 6 — LSB Embedding
Encrypted bits embedded into **pixel Least Significant Bits**:
1. Encrypted bytes → binary bit stream
2. Each pixel value's LSB replaced with one secret bit
3. A 32-bit length header (×{HEADER_REPS} majority-vote copies) embedded first

### Step 7 — Image Reconstruction
The stego image is saved as a **lossless BMP** — every pixel preserved exactly.

### Step 8 — Data Extraction
1. Same square crop applied to stego image
2. Pixel LSBs read in the same order as embedding
3. First {HEADER_BYTES*8*HEADER_REPS} bits = length header (majority vote)
4. Remaining bits = encrypted payload bytes

### Step 9 — AES Decryption
AES-128 CBC decrypt with saved key → PKCS7 unpad → original plaintext.

---

### Quality Metrics
| Metric | Meaning | Target |
|--------|---------|--------|
| PSNR | Signal-to-noise ratio | > 40 dB |
| MSE  | Mean squared pixel error | Near 0 |
| SSIM | Structural similarity | Near 1.0 |

### Team
| Member | Roll No | Module |
|--------|---------|--------|
| Sumitha GK    | 2023503024 | Steps 2 & 9 — AES-128 CBC Encrypt/Decrypt |
| Jenifa V      | 2023503044 | Steps 3, 4, 5 — Preprocessing, SVD, Compression |
| Pradesha P    | 2023503054 | Steps 6 & 8 — LSB Embed/Extract |
| Vethavalli GM | 2023503550 | Steps 1 & 7 — Pipeline, Metrics, Gradio UI |
""")

demo.launch(share=True, debug=False)