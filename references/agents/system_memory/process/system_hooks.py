# -*- coding: utf-8 -*-
"""
系统策划 Hooks -- 每个状态的具体执行逻辑。

数据传递方式：LLM 写文件 -> hooks 从文件读。
"""

import json
import os
import re
import sys
import shutil
from datetime import datetime

# -- 路径常量 --

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'references', 'scripts', 'core'
))

from constants import REFERENCES_DIR, AGENTS_DIR, OUTPUT_DIR, agent_paths
from hook_utils import load_md_batch, load_json, save_json, init_pending, append_pending

_p = agent_paths('system_memory')
AGENT_DIR = _p['agent_dir']
KNOWLEDGE_DIR = _p['knowledge_dir']
DATA_DIR = _p['data_dir']


# -- delegate 检测规则 --

DELEGATE_SECTIONS = {
    "numerical": ["## 数值设计"],
    "combat":    ["## 战斗设计", "## 关卡设计"],
}


# ============================================================
# on_enter: parse
# ============================================================

def on_enter_parse():
    """进入 parse 状态。加载 system_rules.md + manifest，理解需求。

    Returns:
        dict: {"knowledge": [...], "instruction": str}
    """
    knowledge = load_md_batch(KNOWLEDGE_DIR, ['system_rules.md'])

    # 初始化 data 目录
    os.makedirs(DATA_DIR, exist_ok=True)
    init_pending(DATA_DIR)

    return {
        "knowledge": knowledge,
        "instruction": (
            "你现在是系统策划。请阅读知识库和公有知识清单，然后理解用户的需求：\n"
            "1. 概述需求目标\n"
            "2. 从 wiki entity 中找出相关系统和表\n"
            "3. 判断是否需要数值策划/战斗策划协助\n"
            "理解完毕后说'已理解'，准备进入 draft 状态。"
        ),
    }


# ============================================================
# on_enter: draft
# ============================================================

def on_enter_draft():
    """进入 draft 状态。加载规则+案例，让 LLM 按模板写文档。

    LLM 产出：将文档写入 data/draft.md

    Returns:
        dict: {"knowledge": [...], "instruction": str}
    """
    knowledge = load_md_batch(KNOWLEDGE_DIR, [
        'system_rules.md',
        'system_examples.md',
    ])

    return {
        "knowledge": knowledge,
        "instruction": (
            "按照 system_rules.md 中的文档模板，撰写策划文档。\n"
            "规则：\n"
            "1. 参考 wiki entity 使用正确的表名和术语\n"
            "2. 界面描述要具体：元素列表、布局位置、交互行为\n"
            "3. 如果需要数值/战斗/关卡设计，写一个简要需求描述在对应章节\n"
            "4. 将完成的文档保存到 data/draft.md\n"
            "完成后说'草稿已完成'。"
        ),
    }


# ============================================================
# on_enter: delegate
# ============================================================

def on_enter_delegate():
    """检测 draft.md 中是否包含需要委托的章节。

    检测规则：
    - 有 '## 数值设计' -> 委托给 numerical
    - 有 '## 战斗设计' 或 '## 关卡设计' -> 委托给 combat

    产出：data/delegate_request.json
    返回：trigger 'need_sub' 或 'no_sub'

    Returns:
        dict: {"trigger": str, "delegates": dict}
    """
    draft_path = os.path.join(DATA_DIR, 'draft.md')
    if not os.path.exists(draft_path):
        return {"trigger": "no_sub", "error": "draft.md not found"}

    with open(draft_path, 'r', encoding='utf-8') as f:
        draft = f.read()

    delegates = {}

    for role, section_headers in DELEGATE_SECTIONS.items():
        for header in section_headers:
            if header in draft:
                # 提取该章节内容作为需求描述
                section_content = _extract_section(draft, header)
                if role not in delegates:
                    delegates[role] = []
                delegates[role].append({
                    "section": header.lstrip('#').strip(),
                    "content": section_content,
                })

    if delegates:
        # 保存委托请求
        request = {
            "timestamp": datetime.now().isoformat(),
            "delegates": delegates,
        }
        save_json(os.path.join(DATA_DIR, 'delegate_request.json'), request)

        # 创建 sub_results 目录
        os.makedirs(os.path.join(DATA_DIR, 'sub_results'), exist_ok=True)

        return {
            "trigger": "need_sub",
            "delegates": delegates,
            "message": f"[i] delegate: {', '.join(delegates.keys())}",
        }
    else:
        return {
            "trigger": "no_sub",
            "message": "[i] no delegation needed",
        }


# ============================================================
# on_enter: assemble
# ============================================================

def on_enter_assemble():
    """整合 draft.md + sub_results/ 为完整文档。

    读取 sub_results/ 目录下的 markdown 文件，替换 draft.md 中对应章节。

    Returns:
        dict: {"knowledge": [...], "instruction": str}
    """
    draft_path = os.path.join(DATA_DIR, 'draft.md')
    sub_dir = os.path.join(DATA_DIR, 'sub_results')

    # 加载 sub_results
    sub_contents = {}
    if os.path.isdir(sub_dir):
        for fname in os.listdir(sub_dir):
            if fname.endswith('.md'):
                fpath = os.path.join(sub_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    sub_contents[fname] = f.read()

    # 如有 sub_results，返回给 LLM 整合
    knowledge = load_md_batch(KNOWLEDGE_DIR, ['system_rules.md'])

    # 加载 draft
    draft_content = ""
    if os.path.exists(draft_path):
        with open(draft_path, 'r', encoding='utf-8') as f:
            draft_content = f.read()

    sub_text = ""
    for fname, content in sub_contents.items():
        sub_text += f"\n--- {fname} ---\n{content}\n"

    return {
        "knowledge": knowledge,
        "instruction": (
            "请整合以下内容为完整策划文档：\n\n"
            "## 当前草稿\n"
            f"{draft_content}\n\n"
            "## 补充内容\n"
            f"{sub_text}\n\n"
            "规则：\n"
            "1. 将补充内容替换到草稿对应章节\n"
            "2. 统一格式和用词\n"
            "3. 保存最终文档到 data/draft.md（覆盖）\n"
            "完成后说'文档已整合'。"
        ),
    }


# ============================================================
# on_enter: wireframe
# ============================================================

def on_enter_wireframe():
    """提取界面章节 -> 调 Stitch MCP API 生成 UI 线框图。

    流程：
    1. 读 data/ui_sections.json（由 LLM 在 wireframe 状态写入）
    2. 用 STITCH_API_KEY 调 Stitch MCP API（JSON-RPC 2.0）
    3. 创建 Stitch project → 对每个 UI section 调 generate_screen_from_text
    4. 下载截图 PNG 到 data/wireframes/{name}.png
    5. 返回 trigger: "wireframed" + 截图路径列表

    约注意：
    - generate_screen_from_text 每次约 60-90 秒，timeout 设 600s
    - API Key 从 .env 的 STITCH_API_KEY 读取
    - 如果 STITCH_API_KEY 未设置则降级为占位模式

    Returns:
        dict: {"trigger": "wireframed", "screenshots": [...], "project_url": str}
    """
    import urllib.request
    import urllib.error

    # ── 1. 读 ui_sections.json ──
    ui_sections_path = os.path.join(DATA_DIR, 'ui_sections.json')
    ui_data = load_json(ui_sections_path)
    ui_sections = ui_data.get('sections', []) if ui_data else []

    # ── 2. 读取 API Key ──
    api_key = _load_stitch_api_key()

    if not api_key:
        print('[WARN] STITCH_API_KEY not set, wireframe skipped')
        return {
            "trigger": "wireframed",
            "screenshots": [],
            "message": "[WARN] STITCH_API_KEY not set. Set in .env to enable wireframe.",
        }

    if not ui_sections:
        print('[i] wireframe: no UI sections found in ui_sections.json')
        return {
            "trigger": "wireframed",
            "screenshots": [],
            "message": "[i] No UI sections extracted from draft.",
        }

    # ── 3. 确保输出目录 ──
    wf_dir = os.path.join(DATA_DIR, 'wireframes')
    os.makedirs(wf_dir, exist_ok=True)

    MCP_URL = 'https://stitch.googleapis.com/mcp'
    MCP_HEADERS = {'X-Goog-Api-Key': api_key, 'Content-Type': 'application/json'}
    _req_id = [0]

    def _mcp(tool_name, arguments, timeout=600):
        _req_id[0] += 1
        payload = {
            "jsonrpc": "2.0", "method": "tools/call", "id": _req_id[0],
            "params": {"name": tool_name, "arguments": arguments}
        }
        req = urllib.request.Request(
            MCP_URL, data=json.dumps(payload).encode(),
            headers=MCP_HEADERS, method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            if 'error' in result:
                raise RuntimeError(f"Stitch MCP error: {result['error']}")
            return result.get('result', {})

    # ── 4. 创建或复用 Stitch 项目 ──
    task_name = ui_data.get('task_name', 'activity')
    # 如果 ui_sections.json 里有之前记录的 project_id，直接复用（跳过创建+预热）
    existing_pid = ui_data.get('stitch_project_id', '')
    if existing_pid:
        project_id = existing_pid
        print(f'[i] Stitch: reusing existing project_id={project_id}')
    else:
        print(f'[+] Stitch: creating project [{task_name}]...')
        try:
            proj_result = _mcp('create_project', {'title': task_name}, timeout=30)
            struct = proj_result.get('structuredContent', {})
            project_name = struct.get('name', '')  # "projects/XXXXXXX"
            project_id = project_name.split('/')[-1] if '/' in project_name else project_name
            print(f'[OK] project_id={project_id}')
        except Exception as e:
            print(f'[ERR] Stitch create_project failed: {e}')
            return {
                "trigger": "wireframed",
                "screenshots": [],
                "message": f"[ERR] Stitch create_project failed: {e}",
            }

        # 新项目预热：Stitch 第一次 generate 总是创建 design system 而非 screen
        # 先发一个预热请求吸收 design system 创建，后续 generate 才会返回真实 screen
        print(f'[+] Stitch: warming up design system (new project)...')
        try:
            _mcp('generate_screen_from_text', {
                'projectId': project_id,
                'prompt': '[Mobile] Light mode. Single empty placeholder screen.',
                'deviceType': 'MOBILE',
            }, timeout=300)
            print(f'[OK] design system initialized')
        except Exception as e:
            print(f'[WARN] warm-up failed (continuing): {e}')



    # ── 5. 逐个生成界面 ──
    screenshots = []
    style_guide = ui_data.get('style_guide', '')
    for i, section in enumerate(ui_sections):
        name = section.get('name', f'screen_{i+1}')
        description = section.get('description', section.get('content', ''))
        prompt = _build_stitch_prompt(name, description, style_guide)

        print(f'[+] Stitch: generating screen {i+1}/{len(ui_sections)}: {name}...')
        try:
            r = _mcp('generate_screen_from_text', {
                'projectId': project_id,
                'prompt': prompt,
                'deviceType': 'MOBILE',
            }, timeout=600)

            # 提取截图 downloadUrl
            screenshot_url = _extract_screenshot_url(r)

            # 第一次 generate 可能只返回 designSystem（Stitch 自动建立设计体系），
            # 此时需要通过 list_screens 查询刚生成的 screen 的截图 URL
            if not screenshot_url:
                print(f'[i] no screenshot in response (may be design system init), '
                      f'falling back to list_screens...')
                try:
                    ls = _mcp('list_screens', {'projectId': project_id}, timeout=30)
                    screens = (_extract_nested(ls, 'structuredContent', 'screens')
                               or _extract_nested(ls, 'screens'))
                    if screens:
                        # 取最新 screen
                        latest = screens[-1]
                        screen_id = (latest.get('id') or
                                     latest.get('name', '').split('/')[-1])
                        sg = _mcp('get_screen', {
                            'projectId': project_id,
                            'screenId': screen_id,
                        }, timeout=30)
                        screenshot_url = _extract_screenshot_url(sg)
                except Exception as e:
                    print(f'[WARN] list_screens fallback failed: {e}')

            if screenshot_url:
                safe_name = name.replace('/', '_').replace(' ', '_')
                png_path = os.path.join(wf_dir, f'{safe_name}.png')
                _download_file(screenshot_url, png_path)
                screenshots.append({
                    "name": name,
                    "path": png_path,
                    "url": screenshot_url,
                })
                print(f'[OK] saved: {png_path}')
            else:
                print(f'[WARN] no screenshot URL for screen: {name}')

        except Exception as e:
            print(f'[ERR] Stitch generate failed for {name}: {e}')
            continue

    # ── 6. 保存结果 ──
    result_data = {
        "project_id": project_id,
        "project_url": f"https://stitch.withgoogle.com/project/{project_id}",
        "screenshots": screenshots,
        "timestamp": datetime.now().isoformat(),
    }
    save_json(os.path.join(DATA_DIR, 'wireframe_result.json'), result_data)

    return {
        "trigger": "wireframed",
        "project_url": result_data["project_url"],
        "screenshots": [s["path"] for s in screenshots],
        "message": f"[OK] {len(screenshots)}/{len(ui_sections)} screens generated",
    }



# ============================================================
# on_enter: export
# ============================================================

def on_enter_export():
    """导出策划文档到 output/ 目录。

    产出：
    - output/<task_name>/design.md
    - output/<task_name>/metadata.json

    Returns:
        dict: {"status": str, "output_dir": str}
    """
    draft_path = os.path.join(DATA_DIR, 'draft.md')
    if not os.path.exists(draft_path):
        return {"status": "ERR", "error": "draft.md not found"}

    with open(draft_path, 'r', encoding='utf-8') as f:
        draft = f.read()

    # 从 draft 第一行提取任务名
    first_line = draft.split('\n')[0].lstrip('#').strip()
    task_name = first_line or datetime.now().strftime("task_%Y%m%d_%H%M%S")
    # 文件名安全处理
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', task_name)

    # 创建输出目录
    out_dir = os.path.join(OUTPUT_DIR, safe_name)
    os.makedirs(out_dir, exist_ok=True)

    # 复制 design.md
    design_path = os.path.join(out_dir, 'design.md')
    with open(design_path, 'w', encoding='utf-8') as f:
        f.write(draft)

    # 导出 design.docx (md2word)
    docx_path = os.path.join(out_dir, 'design.docx')
    docx_ok = False
    try:
        from md2word import convert_file
        convert_file(design_path, docx_path)
        docx_ok = True
    except ImportError:
        pass  # md2word not installed
    except Exception as e:
        print(f"[WARN] docx export failed: {e}")
        docx_ok = False

    # 复制 wireframe 图片（如有）
    wireframe_dir = os.path.join(DATA_DIR, 'wireframes')
    if os.path.isdir(wireframe_dir):
        out_wf = os.path.join(out_dir, 'wireframes')
        os.makedirs(out_wf, exist_ok=True)
        for fname in os.listdir(wireframe_dir):
            shutil.copy2(os.path.join(wireframe_dir, fname), out_wf)

    # 写 metadata
    output_files = ["design.md"]
    if docx_ok:
        output_files.append("design.docx")
    metadata = {
        "task_name": task_name,
        "timestamp": datetime.now().isoformat(),
        "source": "system_designer",
        "files": output_files,
    }
    save_json(os.path.join(out_dir, 'metadata.json'), metadata)

    # 追加案例
    now = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n\n### {task_name} ({now})\n\n"
    entry += f"- 输出: {out_dir}\n"
    append_pending(DATA_DIR, "system_examples.md", entry)

    return {
        "status": "OK",
        "output_dir": out_dir,
        "files": output_files,
        "message": f"[OK] exported to {out_dir}" + (" (docx)" if docx_ok else " (md only)"),
    }


# ============================================================
# 辅助函数
# ============================================================

def _extract_section(text, header):
    """提取 markdown 中指定 ## 章节的内容。"""
    lines = text.split('\n')
    in_section = False
    result = []
    header_level = len(header) - len(header.lstrip('#'))  # ## = 2

    for line in lines:
        if line.strip() == header.strip():
            in_section = True
            continue
        elif in_section:
            # 遇到同级或更高级标题则结束
            if line.startswith('#'):
                current_level = len(line.split(' ')[0])
                if current_level <= header_level:
                    break
            result.append(line)

    return '\n'.join(result).strip()


def _extract_ui_sections(text):
    """提取 ## 玩法界面 下的所有 ### 子章节。"""
    sections = []
    lines = text.split('\n')
    in_ui = False
    current_name = None
    current_lines = []

    for line in lines:
        if line.startswith('## 玩法界面'):
            in_ui = True
            continue
        elif in_ui and line.startswith('## ') and '玩法界面' not in line:
            # 遇到下一个 ## 章节，结束
            if current_name:
                sections.append({
                    "name": current_name,
                    "description": '\n'.join(current_lines).strip(),
                })
            break
        elif in_ui and line.startswith('### '):
            if current_name:
                sections.append({
                    "name": current_name,
                    "description": '\n'.join(current_lines).strip(),
                })
            current_name = line.lstrip('#').strip()
            current_lines = []
        elif in_ui and current_name:
            current_lines.append(line)

    # 末尾
    if current_name:
        sections.append({
            "name": current_name,
            "description": '\n'.join(current_lines).strip(),
        })

    return sections


def _load_stitch_api_key():
    """从 .env 文件加载 STITCH_API_KEY。"""
    # 先查环境变量
    key = os.environ.get('STITCH_API_KEY', '')
    if key:
        return key
    # 再查 .env 文件
    workspace = os.environ.get('WORKSPACE_DIR') or os.path.normpath(
        os.path.join(AGENT_DIR, '..', '..', '..')
    )
    env_path = os.path.join(workspace, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('STITCH_API_KEY='):
                        return line.strip().split('=', 1)[1]
        except Exception:
            pass
    return ''


def _build_stitch_prompt(screen_name, description, style_guide=''):
    """将界面描述转为 Stitch 结构化 prompt。

    Stitch 推荐格式: [Device] [Mode] [Screen Type] [Style] [Layout] [Components]
    """
    style = style_guide or 'Japanese anime/manga, vibrant, One Piece pirate theme, dark background, parchment panels, gold accents'
    prompt = (
        f"[Device] Mobile [Mode] Dark [Screen Type] Game Activity Screen "
        f"[Style] {style} "
        f"[Screen Name] {screen_name} "
        f"[Layout and Components] {description}"
    )
    return prompt


def _extract_screenshot_url(mcp_result):
    """从 Stitch MCP 返回中提取截图 downloadUrl。

    响应结构:
    result.content[0].text = JSON string with outputComponents[0].design.screens[0].screenshot.downloadUrl
    或 result.structuredContent 直接有该结构
    """
    # 尝试从 structuredContent
    struct = mcp_result.get('structuredContent', {})
    try:
        return (struct.get('outputComponents', [{}])[0]
                .get('design', {})
                .get('screens', [{}])[0]
                .get('screenshot', {})
                .get('downloadUrl', ''))
    except (IndexError, AttributeError):
        pass

    # 尝试从 content[0].text（JSON 字符串）
    content = mcp_result.get('content', [])
    for item in content:
        if isinstance(item, dict) and item.get('type') == 'text':
            try:
                data = json.loads(item['text'])
                url = (data.get('outputComponents', [{}])[0]
                       .get('design', {})
                       .get('screens', [{}])[0]
                       .get('screenshot', {})
                       .get('downloadUrl', ''))
                if url:
                    return url
            except Exception:
                pass
    return ''


def _download_file(url, dest_path):
    """下载文件到本地路径。"""
    import urllib.request
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(dest_path, 'wb') as f:
            f.write(resp.read())


def _extract_nested(obj, *keys):
    """安全地从嵌套 dict 中提取值，任意层级 KeyError 返回 None。"""
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj

