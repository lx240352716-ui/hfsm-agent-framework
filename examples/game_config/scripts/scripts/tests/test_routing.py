"""routing.json 合法性校验

检查项：
1. JSON 格式合法
2. 每个 type 必须有 description / roles / workflows
3. workflows 引用的文件必须存在
4. roles 必须是已知角色名
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(SCRIPT_DIR, "..", "configs")
ROUTING_PATH = os.path.join(CONFIGS_DIR, "routing.json")
WORKFLOW_DIR = os.path.join(CONFIGS_DIR, "workflows")

VALID_ROLES = {"combat", "numerical", "executor", "coordinator"}
REQUIRED_KEYS = {"description", "roles", "workflows"}

def run():
    errors = []

    # 1. JSON 格式
    try:
        with open(ROUTING_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"FAIL: routing.json parse error: {e}")
        return 1

    if "types" not in data:
        print("FAIL: routing.json missing 'types' key")
        return 1

    types = data["types"]
    print(f"routing.json: {len(types)} types defined\n")

    for name, cfg in types.items():
        # 2. 必需字段
        missing = REQUIRED_KEYS - set(cfg.keys())
        if missing:
            errors.append(f"  {name}: missing keys {missing}")

        # 3. workflows 存在性
        for wf in cfg.get("workflows", []):
            wf_path = os.path.join(WORKFLOW_DIR, wf)
            if not os.path.exists(wf_path):
                errors.append(f"  {name}: workflow '{wf}' not found at {wf_path}")

        # 4. roles 合法性
        for role in cfg.get("roles", []):
            if role not in VALID_ROLES:
                errors.append(f"  {name}: unknown role '{role}'")

        # 输出
        status = "OK" if not any(name in e for e in errors) else "FAIL"
        print(f"  [{status}] {name}: {cfg.get('description', '?')}")
        print(f"         roles={cfg.get('roles')}, workflows={cfg.get('workflows')}")

    print()
    if errors:
        print(f"FAIL: {len(errors)} errors")
        for e in errors:
            print(e)
        return 1
    else:
        print(f"ALL PASS: {len(types)} types validated")
        return 0

if __name__ == "__main__":
    sys.exit(run())
