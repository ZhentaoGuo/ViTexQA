<div align="center">

# ViTexQA: A Multi-Frame Temporal Perception Dataset for Video Text Question Answering

[![ECCV 2026](https://img.shields.io/badge/ECCV-2026-blue.svg)]()
[![License](https://img.shields.io/badge/License-Apache--2.0-green.svg)]()
[![HuggingFace Dataset](https://img.shields.io/badge/HuggingFace-Dataset-yellow)](https://huggingface.co/...)

</div>

---

## 🔥 News

- **2026/07** 🎉 ViTexQA has been accepted to **ECCV 2026**.
- **2026/07** 🤗 ViTexQA dataset is released on HuggingFace.
- **Coming Soon** Training code for FrameThinker.

---

## 📖 Introduction

ViTexQA is a large-scale benchmark for **multi-frame video text understanding**.

Unlike existing video text QA datasets, where many questions can still be answered from a single frame, **every question in ViTexQA requires integrating textual information across multiple video frames.**

<div align="center">

<img src="assets/teaser.png" width="95%">

</div>

Our contributions include:

- ✅ 5,147 videos
- ✅ 6,864 QA pairs
- ✅ 100% verified multi-frame dependency
- ✅ Temporal Chain-of-Thought annotations
- ✅ Diverse real-world scenarios (sports, news, driving, tutorials, etc.)
- ✅ Synthetic rolling-text video generation pipeline

---

## 📊 Dataset Statistics

<div align="center">

<img src="assets/statistics.png" width="95%">

</div>

ViTexQA contains

| Item | Value |
|------|------:|
| Videos | 5,147 |
| QA pairs | 6,864 |
| Multi-frame dependency | **100%** |
| Categories | 30 |
| Duration | 363 Hours |

---

# 📥 Dataset Download

The complete dataset is hosted on HuggingFace.

> **HuggingFace:**  
> https://huggingface.co/datasets/xxxxx/ViTexQA

Download includes:

```
ViTexQA/
│
├── train.json
├── val.json
├── test.json
│
├── videos/
│
├── cot_annotations/
│
├── metadata/
│
└── README.md
```

Each sample contains

- video path
- question
- answer
- temporal CoT
- timestamps
- metadata

---

# 🛠 Synthetic Video Generation

We also release the synthetic rolling-text video generation pipeline used in the paper.

```
Synthetic_video/

├── backgrounds/
├── corpus/
├── fonts/
├── generate_video.py
├── render_text.py
├── animation.py
├── transition.py
└── utils.py
```

The pipeline supports

- Random text corpus
- Random fonts
- Random colors
- Shadows
- Transparency
- Scrolling animation
- Typewriter animation
- Multiple transition effects
- Automatic QA annotation generation

Example

```bash
python generate_video.py \
    --output output_dir \
    --num_videos 100
```

Generated videos can be directly used for training and evaluation.

---

# 📂 Repository Structure

```
ViTexQA/

├── assets/
│
├── Synthetic_video/
│
├── examples/
│
├── LICENSE
├── README.md
└── requirements.txt
```

---

# 📷 Examples

<div align="center">

<img src="assets/example1.png" width="90%">

<img src="assets/example2.png" width="90%">

</div>

---

# 📄 Paper

If you find our work useful, please consider citing

```bibtex
@inproceedings{vitexqa2026,
  title={ViTexQA: A Multi-Frame Temporal Perception Dataset for Video Text Question Answering},
  author={XXX},
  booktitle={ECCV},
  year={2026}
}
```

---

# 🙏 Acknowledgements

We thank all annotators and the open-source community for making this project possible.

---

# ⭐ Star

If ViTexQA is useful for your research, please consider giving this repository a ⭐.
