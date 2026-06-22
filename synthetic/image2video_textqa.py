import os
import cv2
import numpy as np
import random
import subprocess
from multiprocessing import Pool, cpu_count
from collections import defaultdict

# ===================== Control Parameters =====================
foreground_txt = 'synthetic/textvqa.txt'  # Foreground image + annotation content txt
background_folder = 'synthetic/ILSVRC2012'  # Background image folder
background_exts = ['.jpg', '.png', '.jpeg']  # Background image extensions
video_output_dir = 'synthetic/video'  # Output video folder
label_output_dir = 'synthetic/label'  # Output label folder

video_duration_range = (30, 180)  # Video duration range (seconds)
image_duration_range = (2, 5)  # Each image display duration (seconds)
fps = 12  # Frames per second
resize_long_edge = 720  # Resize longest edge of foreground image to 720
transition_types = ['cut', 'fade', 'blinds']  # Supported transition animations
transition_duration = 0.5  # Transition animation duration (seconds)

os.makedirs(video_output_dir, exist_ok=True)
os.makedirs(label_output_dir, exist_ok=True)
# ===================================================

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
    return img, scale

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
    img, _ = resize_image_keep_aspect(img, max(target_size))  # No need to use the scale factor here
    img = pad_to_size(img, target_size)
    return img

def convert_to_h264(src_path, dst_path):
    cmd = [
        'ffmpeg',
        '-y',
        '-i', src_path,
        '-c:v', 'libx264',
        '-c:a', 'copy',
        dst_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Converted to H264: {dst_path}")
        os.remove(src_path)
        os.rename(dst_path, src_path)
    except Exception as e:
        print(f"ffmpeg conversion failed: {src_path} -> {dst_path}, error: {e}")

def process_one(args):
    line, all_background_files, output_name = args
    try:
        fg_path, question, answer, coords_str = line.split('\t')
    except Exception as e:
        print(f"Format error: {line}")
        return
    video_output_path = os.path.join(video_output_dir, f'{output_name}.mp4')
    label_output_path = os.path.join(label_output_dir, f'{output_name}.txt')
    video_duration = random.randint(*video_duration_range)
    num_images = int(video_duration / random.uniform(*image_duration_range))
    background_num = num_images - 1
    if background_num > len(all_background_files):
        print(f"Not enough background images: required {background_num}, available {len(all_background_files)}")
        return
    background_files = random.sample(all_background_files, background_num)
    all_images = background_files + [fg_path]
    random.shuffle(all_images)
    fg_img = cv2.imread(fg_path, cv2.IMREAD_COLOR)
    if fg_img is None:
        print(f"Foreground image not found: {fg_path}")
        return
    fg_img, scale = resize_image_keep_aspect(fg_img, resize_long_edge)
    target_size = fg_img.shape[:2]
    images = []

    for path in all_images:
        if path == fg_path:
            images.append(fg_img)
        else:
            try:
                bg_img = load_and_resize(path, target_size)
                images.append(bg_img)
            except Exception as e:
                print(f"Failed to load background image: {path}, {str(e)}")
                return

    image_durations = [random.uniform(*image_duration_range) for _ in images]
    total_duration = sum(image_durations)
    scale_duration = video_duration / total_duration
    image_durations = [d * scale_duration for d in image_durations]
    frames = []
    fg_start_frame = None
    fg_end_frame = None
    cur_frame = 0
    for i in range(len(images)):
        img = images[i]
        duration = image_durations[i]
        frame_count = int(duration * fps)
        if all_images[i] == fg_path:
            fg_start_frame = cur_frame
            fg_end_frame = cur_frame + frame_count - 1
        frames.extend([img] * frame_count)
        cur_frame += frame_count
        if i < len(images) - 1:
            transition = random.choice(transition_types)
            transition_func = get_transition_func(transition)
            t_frames = int(transition_duration * fps)
            if transition == 'blinds':
                t_imgs = transition_func(img, images[i+1], t_frames, blinds=12)
            else:
                t_imgs = transition_func(img, images[i+1], t_frames)
            frames.extend(t_imgs)
            cur_frame += t_frames

    h, w = target_size
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_output_path, fourcc, fps, (w, h))
    for frame in frames:
        out.write(frame)
    out.release()
    # ========== ffmpeg convert to h264 ==========
    h264_video_path = video_output_path + ".tmp_h264.mp4"
    convert_to_h264(video_output_path, h264_video_path)
    print(f"Video generated: {video_output_path}")

    # ==== Write label (with foreground time range) ====
    if fg_start_frame is not None and fg_end_frame is not None:
        start_sec = fg_start_frame // fps
        end_sec = (fg_end_frame + 1) // fps  # End time is the time of the frame after the last foreground frame
        
        # Parse and scale coordinates
        coords = eval(coords_str)
        scaled_coords = [(int(x * scale), int(y * scale)) for x, y in coords]

        with open(label_output_path, 'w', encoding='utf-8') as lf:
            lf.write(f'[{start_sec},{end_sec}]\t{question}\t{answer}\t{scaled_coords}')
        print(f"Label saved: {label_output_path}")
    else:
        print(f"Foreground frame range not found: {fg_path}")


if __name__ == '__main__':
    # 1. Read foreground image and label list
    with open(foreground_txt, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    # 1.1 Count occurrences of each foreground image basename and assign unique names
    basename_count = defaultdict(int)
    unique_output_names = []
    for line in lines:
        fg_path = line.split('\t', 1)[0]
        fg_basename = os.path.splitext(os.path.basename(fg_path))[0]
        basename_count[fg_basename] += 1
        if basename_count[fg_basename] == 1:
            unique_name = fg_basename
        else:
            unique_name = f"{fg_basename}_{basename_count[fg_basename]}"
        unique_output_names.append(unique_name)

    # 2. Recursively scan all background image paths (only once)
    all_background_files = get_all_background_files(background_folder, background_exts)
    print(f"Total background images: {len(all_background_files)}")

    # 3. Multi-process parallel processing
    args_list = [(line, all_background_files, unique_output_names[i]) for i, line in enumerate(lines)]
    num_workers = min(cpu_count(), 32)
    print(f"Number of processes used: {num_workers}")

    with Pool(processes=num_workers) as pool:
        pool.map(process_one, args_list)