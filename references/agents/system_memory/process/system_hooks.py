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
    """提取界面章节 -> 调 Stitch 生成 UI 图。

    Phase 3 实现。当前为占位，直接跳过。

    Returns:
        dict: {"trigger": "wireframed", "message": str}
    """
    draft_path = os.path.join(DATA_DIR, 'draft.md')

    # 提取界面章节（供未来 Stitch 使用）
    ui_sections = []
    if os.path.exists(draft_path):
        with open(draft_path, 'r', encoding='utf-8') as f:
            draft = f.read()
        # 找所有 ## 玩法界面 下的 ### 子章节
        ui_sections = _extract_ui_sections(draft)

    if ui_sections:
        # 保存界面描述供 Stitch 使用
        save_json(os.path.join(DATA_DIR, 'ui_sections.json'), {
            "sections": ui_sections,
            "timestamp": datetime.now().isoformat(),
        })

    return {
        "trigger": "wireframed",
        "message": f"[i] wireframe: {len(ui_sections)} UI section(s) extracted (Stitch not connected yet)",
        "ui_sections": ui_sections,
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
