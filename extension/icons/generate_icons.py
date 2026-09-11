"""
Script to generate official Chrome Extension icons for MahaSetu RPA Recorder
Generates icon16.png, icon32.png, icon48.png, icon128.png in extension/icons/
"""
import os
from PIL import Image, ImageDraw

def create_icon(size: int) -> Image.Image:
    # Use 4x supersampling for ultra crisp anti-aliasing
    scale = 4
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    pad = int(canvas_size * 0.06)
    r = int(canvas_size * 0.22)
    
    # Outer rounded badge with gradient effect
    # Background: dark slate #0f172a
    draw.rounded_rectangle(
        [pad, pad, canvas_size - pad, canvas_size - pad],
        radius=r,
        fill=(15, 23, 42, 255),
        outline=(16, 185, 129, 255),  # Emerald outline
        width=max(2, int(scale * size * 0.05))
    )
    
    # Center emblem: Robot / Bridge Automation Emblem
    cx = canvas_size // 2
    cy = canvas_size // 2
    
    # Antenna / Signal dot
    ant_r = int(canvas_size * 0.05)
    draw.ellipse([cx - ant_r, int(canvas_size * 0.20), cx + ant_r, int(canvas_size * 0.20) + 2 * ant_r], fill=(56, 189, 248, 255))
    draw.line([cx, int(canvas_size * 0.25), cx, int(canvas_size * 0.32)], fill=(56, 189, 248, 255), width=max(1, scale * 2))
    
    # Robot Head / Bridge Arch
    hw = int(canvas_size * 0.30)
    hh = int(canvas_size * 0.22)
    hx0 = cx - hw
    hy0 = int(canvas_size * 0.32)
    hx1 = cx + hw
    hy1 = hy0 + hh
    
    draw.rounded_rectangle(
        [hx0, hy0, hx1, hy1],
        radius=int(scale * 4),
        fill=(30, 41, 59, 255),
        outline=(56, 189, 248, 255),
        width=max(1, scale * 2)
    )
    
    # Glowing Eyes
    eye_w = int(canvas_size * 0.07)
    eye_y0 = hy0 + int(hh * 0.30)
    eye_y1 = eye_y0 + eye_w
    # Left eye
    draw.ellipse([cx - int(hw * 0.6), eye_y0, cx - int(hw * 0.6) + eye_w, eye_y1], fill=(16, 185, 129, 255))
    # Right eye
    draw.ellipse([cx + int(hw * 0.6) - eye_w, eye_y0, cx + int(hw * 0.6), eye_y1], fill=(16, 185, 129, 255))
    
    # Bridge Pillars / Lower automation tracks
    bw = int(canvas_size * 0.34)
    bh = int(canvas_size * 0.22)
    by0 = int(canvas_size * 0.60)
    by1 = by0 + bh
    
    # Left pillar
    draw.rounded_rectangle([cx - bw, by0, cx - int(bw * 0.35), by1], radius=int(scale * 2), fill=(16, 185, 129, 255))
    # Right pillar
    draw.rounded_rectangle([cx + int(bw * 0.35), by0, cx + bw, by1], radius=int(scale * 2), fill=(16, 185, 129, 255))
    # Connecting span
    draw.rectangle([cx - bw, by0, cx + bw, by0 + int(scale * 3)], fill=(56, 189, 248, 255))
    # Center bridge node
    cn_r = int(canvas_size * 0.04)
    draw.ellipse([cx - cn_r, by0 - cn_r, cx + cn_r, by0 + cn_r], fill=(255, 255, 255, 255))
    
    # Downsample with high quality Lanczos filter
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img

def main():
    icons_dir = os.path.dirname(os.path.abspath(__file__))
    sizes = [16, 32, 48, 128]
    for s in sizes:
        icon_path = os.path.join(icons_dir, f"icon{s}.png")
        icon_img = create_icon(s)
        icon_img.save(icon_path, "PNG")
        print(f"Generated {icon_path} ({s}x{s})")

if __name__ == "__main__":
    main()
