# Project Credits, Upstream Repositories & Academic Citations 📜

The **Howdy Linux Face ID Biometric Engine** is built upon and inspired by outstanding open-source projects, neural network architectures, and computer vision research. We gratefully acknowledge and credit the following repositories, organizations, and authors:

---

## 🏛️ Core Upstream Projects & Repositories

### 1. [Howdy (Original Project)](https://github.com/boltgolt/howdy)
* **Author / Maintainer:** Slavik ["boltgolt"](https://github.com/boltgolt) & contributors
* **Repository:** [https://github.com/boltgolt/howdy](https://github.com/boltgolt/howdy)
* **License:** [MIT License](https://github.com/boltgolt/howdy/blob/master/LICENSE)
* **Contribution:** Foundational Linux PAM facial authentication framework, command-line interface design (`howdy add`, `howdy clear`, `howdy list`, `howdy config`, `howdy test`), video capture base, and initial dlib-based recognition pipeline.

### 2. [OpenCV Zoo & YuNet Deep CNN Face Detector](https://github.com/opencv/opencv_zoo)
* **Authors / Developers:** Shiqi Yu, Feng Ne, and the OpenCV Development Team
* **Repository:** [https://github.com/opencv/opencv_zoo](https://github.com/opencv/opencv_zoo)
* **Model File:** `face_detection_yunet_2023mar.onnx`
* **License:** [Apache License 2.0](https://github.com/opencv/opencv_zoo/blob/main/LICENSE)
* **Contribution:** Ultra-lightweight depthwise separable convolutional neural network (76,000 parameters). Provides sub-6ms single-core inference, high-precision bounding box detection across $\pm 85^\circ$ yaw angles, and 5-point facial landmark localization (eyes, nose, mouth).

### 3. [Silent-Face-Anti-Spoofing & MiniFASNet](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing)
* **Authors / Developers:** Minivision AI Research Team
* **Repository:** [https://github.com/minivision-ai/Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing)
* **ONNX Conversion:** [garciafido/minifasnet-v2-anti-spoofing-onnx](https://huggingface.co/garciafido/minifasnet-v2-anti-spoofing-onnx) by Fido Garcia
* **Model File:** `minifasnet_v2.onnx`
* **License:** [Apache License 2.0](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/master/LICENSE)
* **Contribution:** Passive anti-spoofing and liveness verification neural network. Analyzes surface reflectance micro-textures and auxiliary 2D Fast Fourier Transform (FFT) frequency spectrums to detect 2D screen replays, paper printouts, and silicone presentation attacks without requiring friction-inducing active challenges.

### 4. [dlib Machine Learning Toolkit](https://github.com/davisking/dlib)
* **Author / Maintainer:** Davis E. King
* **Repository:** [https://github.com/davisking/dlib](https://github.com/davisking/dlib)
* **Models:**
  - `dlib_face_recognition_resnet_model_v1.dat` (ResNet-34 based 128-dimensional metric face embedding)
  - `shape_predictor_5_face_landmarks.dat` (5-point facial landmark alignment predictor)
* **License:** [Boost Software License 1.0 (BSL-1.0)](https://github.com/davisking/dlib/blob/master/dlib/LICENSE.txt)
* **Contribution:** High-precision facial feature extraction, face recognition ResNet embeddings, and facial pose shape alignment.

### 5. [OpenCV (Open Source Computer Vision Library)](https://github.com/opencv/opencv)
* **Organization:** OpenCV Foundation / Gary Bradski, Vadim Pisarevsky
* **Repository:** [https://github.com/opencv/opencv](https://github.com/opencv/opencv)
* **License:** [Apache License 2.0](https://github.com/opencv/opencv/blob/4.x/LICENSE)
* **Contribution:** Hardware VideoCapture V4L2 streaming backend, colorspace transformations (BGR, RGB, Grayscale, LAB), CLAHE contrast equalization, dynamic resizing, and deep neural network (DNN) runtime.

### 6. [Microsoft ONNX Runtime](https://github.com/microsoft/onnxruntime)
* **Author / Maintainer:** Microsoft Corporation
* **Repository:** [https://github.com/microsoft/onnxruntime](https://github.com/microsoft/onnxruntime)
* **License:** [MIT License](https://github.com/microsoft/onnxruntime/blob/main/LICENSE)
* **Contribution:** Cross-platform accelerated neural network inference engine with automated multi-hardware execution provider probing (CPU SIMD, Intel OpenVINO, NVIDIA CUDA/TensorRT, AMD ROCm).

### 7. [PyCA Cryptography](https://github.com/pyca/cryptography)
* **Authors:** Python Cryptographic Authority (PyCA)
* **Repository:** [https://github.com/pyca/cryptography](https://github.com/pyca/cryptography)
* **License:** [Apache License 2.0 / BSD 3-Clause](https://github.com/pyca/cryptography/blob/main/LICENSE)
* **Contribution:** Authenticated Encryption with Associated Data (AES-256-GCM AEAD) and HMAC-based Key Derivation Function (HKDF-SHA256) for machine-bound biometric vault security.

### 8. [XZ Utils & LZMA SDK](https://tukaani.org/xz/)
* **Authors:** Igor Pavlov (LZMA SDK), Lasse Collin & Tukaani Project (`xz-utils`)
* **Repository:** [https://github.com/tukaani-project/xz](https://github.com/tukaani-project/xz)
* **License:** Public Domain / GNU LGPL
* **Contribution:** LZMA2 compression algorithm powering the ultra-compact biometric template storage (reducing 1,000 face models down to 454 KB on disk).

### 9. [pam-python](https://github.com/pypa/pam-python)
* **Author:** Russell Stuart
* **Repository:** [https://github.com/pypa/pam-python](https://github.com/pypa/pam-python) / Debian `libpam-python`
* **License:** [GNU Lesser General Public License 2.1 (LGPL-2.1)](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
* **Contribution:** C-to-Python PAM bridge enabling PAM modules to execute natively in Python during Linux system authentication.

---

## 🔬 Academic & Research Citations

1. **Multi-Scale Retinex with Color Restoration (MSRCR):**
   * **Paper:** Jobson, D. J., Rahman, Z., & Woodell, G. A. (1997). *"A multiscale retinex for bridging the gap between color images and the human observation of scenes"*. IEEE Transactions on Image Processing, 6(7), 965-976.
   * **Affiliation:** NASA Langley Research Center.
   * **Application:** Photometric normalization decomposing observed frames into dynamic illumination ($L$) and spatial reflectance ($R$) to extract facial boundaries under harsh backlights and specular glare.

2. **Deep Residual Learning for Image Recognition (ResNet):**
   * **Paper:** He, K., Zhang, X., Ren, S., & Sun, J. (2016). *"Deep Residual Learning for Image Recognition"*. IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 770-778.
   * **Application:** 29-layer residual convolutional network used by dlib for generating Euclidean metric face vector embeddings.

3. **Face Spoofing Detection via Fourier Micro-Textures:**
   * **Paper:** Zhang, Z., Yan, J., Liu, S., Lei, Z., Yi, D., & Li, S. Z. (2012). *"A face antispoofing database with diverse attacks"*. IAPR International Conference on Biometrics (ICB), 26-31.
   * **Application:** Dual-stream passive liveness verification utilizing 2D Fast Fourier Transform frequency distributions.

4. **Enterprise Linux Facial Biometrics Architectural Specification:**
   * **Reference:** [Gemini Deep Research Architectural Blueprint](https://share.gemini.google/XJnNXieEEALm)
   * **Application:** End-to-end blueprint specifying MSRCR luminance filtering, YuNet CNN multi-angle cascade, MiniFASNet anti-spoofing, ACPI hardware lid gating, and memory-locking hardening.

---

## ⚖️ License Summary

This project is licensed under the **MIT License**. All individual upstream models, libraries, and components retain their respective original licenses (MIT, Apache 2.0, Boost Software License 1.0, LGPL 2.1, and Public Domain).
