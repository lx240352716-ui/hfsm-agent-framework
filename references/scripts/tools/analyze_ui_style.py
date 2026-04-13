# -*- coding: utf-8 -*-
"""
UI 风格解析器 -- 从 UI 参考图目录提取项目视觉风格，生成 ui_style.md 知识文件。

用法:
    python analyze_ui_style.py <image_dir> [--output <output_path>]

流程:
    1. 扫描目录下所有图片 (png/jpg/jpeg/webp)
    2. Pillow 提取每张图的主色调 (K-Means Top 5)
    3. Gemini Vision API 分析每张图的 UI 语义 (布局/组件/字体/装饰风格)
    4. 合并所有分析结果，生成 ui_style.md

依赖:
    pip install google-genai Pillow scikit-learn numpy
"""

import argparse
import base64
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# ── Pillow 取色 ──

def extract_dominant_colors(image_path, n_colors=5):
    """用 K-Means 从图片提取 n 个主色调，返回 [(hex, percentage), ...]"""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        print('[ERR] pip install Pillow numpy')
        return []

    img = Image.open(image_path).convert('RGB')
    # 缩小图片加速聚类
    img = img.resize((150, 150))
    pixels = np.array(img).reshape(-1, 3).astype(float)

    try:
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=n_colors, n_init=10, random_state=42)
        km.fit(pixels)
        counts = Counter(km.labels_)
        total = sum(counts.values())
        centers = km.cluster_centers_.astype(int)
        result = []
        for idx in sorted(counts, key=counts.get, reverse=True):
            r, g, b = centers[idx]
            hex_color = f'#{r:02x}{g:02x}{b:02x}'
            pct = counts[idx] / total * 100
            result.append((hex_color, round(pct, 1)))
        return result
    except ImportError:
        # 无 sklearn 时用简单直方图取色
        from PIL import ImageStat
        stat = ImageStat.Stat(img)
        r, g, b = [int(x) for x in stat.mean]
        return [(f'#{r:02x}{g:02x}{b:02x}', 100.0)]


# ── Gemini Vision 分析 ──

def load_gemini_key():
    """从 .env 加载 GEMINI_API_KEY"""
    key = os.environ.get('GEMINI_API_KEY', '')
    if key:
        return key
    # 遍历可能的 .env 路径
    for env_path in [
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'),
        r'G:\op_design\.env',
    ]:
        env_path = os.path.normpath(env_path)
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('GEMINI_API_KEY='):
                        return line.strip().split('=', 1)[1]
    return ''


def analyze_image_with_gemini(image_path, api_key):
    """用 Gemini Vision API 分析单张 UI 图片，返回结构化描述。"""
    from google import genai

    client = genai.Client(api_key=api_key)

    # 读取图片 base64
    with open(image_path, 'rb') as f:
        image_data = f.read()

    prompt = """Analyze this game UI screenshot as a professional UI/UX designer.
Extract the following information in JSON format:

{
  "screen_type": "what type of screen this is (e.g. main menu, battle, shop, popup, settings)",
  "layout_pattern": "describe the layout structure (e.g. top bar + center content + bottom nav)",
  "color_scheme": {
    "primary": "dominant color description and approximate hex",
    "secondary": "secondary color",
    "accent": "accent/highlight color",
    "background": "background color/gradient"
  },
  "typography": {
    "style": "font style description (bold, thin, pixel, rounded, serif, etc.)",
    "hierarchy": "how text sizes are used (large title, medium body, small labels)"
  },
  "components": ["list of UI components visible: buttons, cards, lists, tabs, icons, etc."],
  "decorative_elements": ["borders, shadows, gradients, glow effects, ornaments, etc."],
  "overall_style": "one-line summary of the visual style (e.g. 'vibrant anime style with gold accents and card-based layout')",
  "design_era": "modern/retro/pixel/cartoon/realistic/anime"
}

Respond ONLY with valid JSON, no markdown formatting."""

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            {
                'inline_data': {
                    'mime_type': _get_mime_type(image_path),
                    'data': base64.b64encode(image_data).decode('utf-8'),
                }
            },
            prompt,
        ],
    )

    # 解析 JSON
    text = response.text.strip()
    # 去掉可能的 markdown 包裹
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_analysis": text}


def _get_mime_type(path):
    ext = Path(path).suffix.lower()
    return {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
    }.get(ext, 'image/png')


# ── 合并分析 + 生成 md ──

def merge_analyses(analyses):
    """合并多张图的分析结果，提取共性风格。"""
    all_styles = [a.get('overall_style', '') for a in analyses if a.get('overall_style')]
    all_eras = [a.get('design_era', '') for a in analyses if a.get('design_era')]
    all_components = []
    for a in analyses:
        all_components.extend(a.get('components', []))

    # 统计频率
    era_counts = Counter(all_eras)
    comp_counts = Counter(all_components)

    return {
        'dominant_era': era_counts.most_common(1)[0][0] if era_counts else 'unknown',
        'style_descriptions': all_styles,
        'common_components': [c for c, _ in comp_counts.most_common(15)],
        'era_distribution': dict(era_counts),
    }


def generate_style_md(image_results, merged, output_path):
    """生成 ui_style.md 知识文件。"""
    lines = []
    lines.append('# UI Style Guide')
    lines.append('')
    lines.append(f'> Auto-generated from {len(image_results)} UI reference images')
    lines.append(f'> Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append('')

    # 整体风格
    lines.append('## Overall Style')
    lines.append('')
    lines.append(f'- **Design Era**: {merged["dominant_era"]}')
    lines.append(f'- **Era Distribution**: {merged["era_distribution"]}')
    lines.append('')
    lines.append('### Style Descriptions')
    lines.append('')
    for s in merged['style_descriptions']:
        lines.append(f'- {s}')
    lines.append('')

    # 色彩汇总
    lines.append('## Color Palette')
    lines.append('')
    all_colors = []
    for r in image_results:
        all_colors.extend(r.get('dominant_colors', []))
    # 按出现频率排序（hex 合并）
    color_freq = Counter()
    for hex_c, pct in all_colors:
        color_freq[hex_c] += pct
    lines.append('| Color | Hex | Weight |')
    lines.append('|-------|-----|--------|')
    for hex_c, weight in color_freq.most_common(10):
        lines.append(f'| ![](color:{hex_c}) | `{hex_c}` | {weight:.0f} |')
    lines.append('')

    # 常用组件
    lines.append('## Common Components')
    lines.append('')
    for comp in merged['common_components']:
        lines.append(f'- {comp}')
    lines.append('')

    # 逐图详细分析
    lines.append('## Per-Image Analysis')
    lines.append('')
    for r in image_results:
        name = r.get('filename', 'unknown')
        analysis = r.get('analysis', {})
        lines.append(f'### {name}')
        lines.append('')
        lines.append(f'- **Screen Type**: {analysis.get("screen_type", "N/A")}')
        lines.append(f'- **Layout**: {analysis.get("layout_pattern", "N/A")}')
        lines.append(f'- **Style**: {analysis.get("overall_style", "N/A")}')

        colors = analysis.get('color_scheme', {})
        if colors:
            lines.append(f'- **Colors**: primary={colors.get("primary","")}, '
                         f'accent={colors.get("accent","")}, bg={colors.get("background","")}')

        typo = analysis.get('typography', {})
        if typo:
            lines.append(f'- **Typography**: {typo.get("style", "")}')

        decos = analysis.get('decorative_elements', [])
        if decos:
            lines.append(f'- **Decorations**: {", ".join(decos[:5])}')

        # 主色调
        dom = r.get('dominant_colors', [])
        if dom:
            hex_list = ' '.join([f'`{h}`({p}%)' for h, p in dom[:5]])
            lines.append(f'- **Dominant Colors**: {hex_list}')
        lines.append('')

    md_content = '\n'.join(lines)
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    return md_content


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description='[i] UI Style Analyzer')
    parser.add_argument('image_dir', help='Directory containing UI reference images')
    parser.add_argument('--output', '-o', default=None,
                        help='Output path for ui_style.md (default: knowledge/ui_style.md)')
    args = parser.parse_args()

    image_dir = args.image_dir
    if not os.path.isdir(image_dir):
        print(f'[ERR] Directory not found: {image_dir}')
        sys.exit(1)

    # 默认输出路径
    output_path = args.output or os.path.join(
        os.path.dirname(__file__), '..', '..', '..', '..', 'knowledge', 'ui_style.md'
    )
    output_path = os.path.normpath(output_path)

    # 扫描图片
    exts = {'.png', '.jpg', '.jpeg', '.webp'}
    images = sorted([
        os.path.join(image_dir, f) for f in os.listdir(image_dir)
        if Path(f).suffix.lower() in exts
    ])

    if not images:
        print(f'[ERR] No images found in {image_dir}')
        sys.exit(1)

    print(f'[+] Found {len(images)} images in {image_dir}')

    # 加载 API key
    api_key = load_gemini_key()
    if not api_key:
        print('[ERR] GEMINI_API_KEY not found in .env or environment')
        sys.exit(1)

    # 逐图分析
    image_results = []
    for i, img_path in enumerate(images):
        filename = os.path.basename(img_path)
        print(f'[{i+1}/{len(images)}] Analyzing {filename}...')

        # 1. Pillow 取色
        colors = extract_dominant_colors(img_path, n_colors=5)

        # 2. Gemini Vision 分析
        try:
            analysis = analyze_image_with_gemini(img_path, api_key)
            print(f'  [OK] {analysis.get("overall_style", "analyzed")}')
        except Exception as e:
            print(f'  [ERR] Gemini failed: {e}')
            analysis = {}

        image_results.append({
            'filename': filename,
            'path': img_path,
            'dominant_colors': colors,
            'analysis': analysis,
        })

    # 合并 + 生成 md
    all_analyses = [r['analysis'] for r in image_results if r['analysis']]
    merged = merge_analyses(all_analyses)

    generate_style_md(image_results, merged, output_path)
    print(f'\n[OK] Generated: {output_path}')
    print(f'[i] Analyzed {len(image_results)} images, '
          f'dominant era: {merged["dominant_era"]}')


if __name__ == '__main__':
    main()
