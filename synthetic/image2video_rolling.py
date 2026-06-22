import os
import cv2
import numpy as np
import random
from multiprocessing import Pool, cpu_count
from PIL import ImageFont, ImageDraw, Image, ImageFilter
import subprocess

# ===================== Control Parameters =====================
word_txt = 'synthetic/words.txt'
font_folder = 'synthetic/font' 
font_exts = ['.ttf', '.otf', '.ttc']
background_folder = 'synthetic/ILSVRC2012'
background_exts = ['.jpg', '.png', '.jpeg']
video_output_dir = 'synthetic/video'
label_output_dir = 'synthetic/label'
font_size_range = (60, 110) #(80, 150)
text_word_count_range = (3, 7)
video_duration_range = (30, 180)
image_duration_range = (2, 3)
fps = 12
resize_long_edge = 720
transition_types = ['cut', 'fade', 'blinds']
transition_duration = 0.5

# Additional parameters
scroll_speed_range = (10, 20)
scroll_direction_choices = ['typewriter','left2right','right2left'] # 'typewriter','left2right','right2left'

text_color_range = ((0, 0, 0), (128, 128, 128))

# ========== Text visual effect parameters ==========
text_alpha_range = (0.9, 0.99)  # Transparency range
text_blur_range = (0, 1)       # Gaussian blur radius range
shadow_offset_range = ((2, 2), (3, 3))  # Shadow offset range (low, high)
shadow_color_range = ((30, 30, 30), (90, 90, 90))  # Shadow color
shadow_alpha_range = (0.3, 0.7)  # Shadow transparency

# White background parameters for text
text_white_bg_prob = 0.2  # Probability of white background
white_bg_alpha_range = (0.7, 1.0)  # White background transparency range
white_bg_expand_px = (1,2)  # White background expansion in pixels (top, bottom, left, right)
# =====================================

os.makedirs(video_output_dir, exist_ok=True)
os.makedirs(label_output_dir, exist_ok=True)

def get_all_font_files(folder, exts):
    font_files = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if os.path.splitext(file)[1].lower() in exts:
                font_files.append(os.path.join(root, file))
    return font_files

def get_all_background_files(folder, exts):
    all_files = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if os.path.splitext(file)[1].lower() in exts:
                all_files.append(os.path.join(root, file))
    return all_files

def resize_image_keep_aspect(img, target_long_edge):
    h, w = img.shape[:2]
    scale = target_long_edge / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    img = cv2.resize(img, (new_w, new_h))
    return img

def pad_to_size(img, target_size):
    th, tw = target_size
    h, w = img.shape[:2]
    if h > th or w > tw:
        img = cv2.resize(img, (tw, th))
        return img
    top = (th - h) // 2
    bottom = th - h - top
    left = (tw - w) // 2
    right = tw - w - left
    color = [0, 0, 0]
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return img

def transition_cut(img1, img2, frames):
    return [img2.copy() for _ in range(frames)]

def transition_fade(img1, img2, frames):
    return [cv2.addWeighted(img1, 1 - i/(frames-1), img2, i/(frames-1), 0) for i in range(frames)]

def transition_blinds(img1, img2, frames, blinds=10):
    h, w = img1.shape[:2]
    out = []
    for f in range(frames):
        mask = np.zeros((h, w), dtype=np.uint8)
        step = int(w / blinds)
        progress = (f+1) / frames
        for i in range(blinds):
            x0 = i * step
            x1 = int(x0 + step * progress)
            mask[:, x0:x1] = 255
        img = img1.copy()
        img[mask == 255] = img2[mask == 255]
        out.append(img)
    return out

def get_transition_func(name):
    if name == 'cut':
        return transition_cut
    elif name == 'fade':
        return transition_fade
    elif name == 'blinds':
        return transition_blinds
    else:
        raise ValueError(f"Unknown transition type: {name}")

def load_and_resize(path, target_size):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Image not found: {path}")
    img = resize_image_keep_aspect(img, max(target_size))
    img = pad_to_size(img, target_size)
    return img

def get_random_text(words, word_count_range):
    n = random.randint(*word_count_range)
    sel = random.sample(words, n)
    return ' '.join(sel)

def get_random_color(color_range):
    low, high = color_range
    return tuple(random.randint(low[i], high[i]) for i in range(3))

def get_random_tuple(range_tuple):
    # Supports ((min1,min2),(max1,max2)) -> (v1,v2)
    return tuple(random.randint(range_tuple[0][i], range_tuple[1][i]) for i in range(len(range_tuple[0])))

def render_text_effect_on_frame(
        frame, text, font_path, font_size, text_color,
        alpha=1.0, blur_radius=0, shadow_offset=(0,0),
        shadow_color=(0,0,0), shadow_alpha=0.5, xy=None,
        white_bg=False, white_bg_alpha=1.0, white_bg_expand=8):
    """ Draw text with shadow/transparent/blur/white background on frame, supports specific position xy """
    img_pil = Image.fromarray(frame).convert("RGBA")
    txt_layer = Image.new('RGBA', img_pil.size, (0,0,0,0))
    draw = ImageDraw.Draw(txt_layer)
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    if xy is None:
        x = (img_pil.width - text_w) // 2
        y = (img_pil.height - text_h) // 2
    else:
        x, y = xy

    # White background layer
    if white_bg:
        expand = white_bg_expand
        bg_x0 = x - expand
        bg_y0 = y - expand
        bg_x1 = x + text_w + expand
        bg_y1 = y + text_h + expand
        white_fill = (255, 255, 255, int(255 * white_bg_alpha))
        draw.rectangle([bg_x0, bg_y0, bg_x1, bg_y1], fill=white_fill)

    # Shadow layer
    if shadow_offset != (0, 0):
        sx, sy = shadow_offset
        shadow_rgba = shadow_color + (int(255*shadow_alpha),)
        draw.text((x+sx, y+sy), text, font=font, fill=shadow_rgba)

    # Text layer
    text_rgba = text_color + (int(255*alpha),)
    draw.text((x, y), text, font=font, fill=text_rgba)

    out_img = Image.alpha_composite(img_pil, txt_layer)

    # Blur
    if blur_radius > 0:
        out_img = out_img.filter(ImageFilter.GaussianBlur(blur_radius))

    return np.array(out_img.convert("RGB"))