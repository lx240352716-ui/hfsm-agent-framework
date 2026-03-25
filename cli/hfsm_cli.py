import os
import argparse
import json
import sys
from pathlib import Path

def init_project(args):
    """Initialize a new HFSM project"""
    project_name = args.name
    project_dir = Path(os.getcwd()) / project_name
    
    if project_dir.exists():
        print(f"Error: Directory '{project_name}' already exists.")
        return
        
    print(f"Initializing new HFSM project: {project_name}")
    project_dir.mkdir(parents=True)
    
    # Create agents directory
    (project_dir / "agents").mkdir()
    
    # Create agents.json
    agents_json_content = """{
    "agents": {},
    "layers": {}
}"""
    with open(project_dir / "agents.json", "w", encoding="utf-8") as f:
        f.write(agents_json_content)
        
    # Create .env
    env_content = f"WORKSPACE_DIR={project_dir.resolve()}\n"
    with open(project_dir / ".env", "w", encoding="utf-8") as f:
        f.write(env_content)
        
    # Create .gitignore
    gitignore_content = """# Data and outputs
agents/*/data/*.json
!agents/*/data/.gitkeep
output/
staging/

# Python
__pycache__/
*.py[cod]
.env
"""
    with open(project_dir / ".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)
        
    print(f"Project '{project_name}' created successfully.")
    print(f"Run `cd {project_name}` to get started.")

def add_agent(args):
    """Add a new agent to the current project"""
    agent_name = args.name
    project_dir = Path(os.getcwd())
    
    if not (project_dir / "agents.json").exists():
        print("Error: No agents.json found. Are you in a valid HFSM project directory?")
        return
        
    agent_dir = project_dir / "agents" / agent_name
    if agent_dir.exists():
        print(f"Error: Agent '{agent_name}' already exists.")
        return
        
    print(f"Adding agent: {agent_name}")
    
    # Create directories
    (agent_dir / "knowledge").mkdir(parents=True)
    (agent_dir / "process").mkdir(parents=True)
    (agent_dir / "data").mkdir(parents=True)
    
    # Create .gitkeep in data
    with open(agent_dir / "data" / ".gitkeep", "w") as f:
        f.write("")
        
    # Create workflow.py
    workflow_content = f'''# -*- coding: utf-8 -*-
"""
{agent_name} Workflow Definition
"""

name = "{agent_name}"
description = "Auto-generated agent"

initial = "start"

states = [
    {{"name": "start", "type": "script", "description": "Initial state"}},
    {{"name": "process", "type": "llm", "description": "Processing state"}},
    {{"name": "done", "type": "script", "description": "Done state"}},
]

transitions = [
    ["started", "start", "process"],
    ["processed", "process", "done"],
]

hooks = {{
    "on_enter_start": "{agent_name}_hooks.on_enter_start",
    "on_enter_process": "{agent_name}_hooks.on_enter_process",
    "on_enter_done": "{agent_name}_hooks.on_enter_done",
}}
'''
    with open(agent_dir / "process" / f"{agent_name}_workflow.py", "w", encoding="utf-8") as f:
        f.write(workflow_content)
        
    # Create hooks.py
    hooks_content = f'''# -*- coding: utf-8 -*-
"""
{agent_name} Hooks

Use ctx.input to access input data.
Return a dictionary to automatically persist to output.json.
"""

def on_enter_start(ctx):
    print(f"[{agent_name}] Entering start state")
    return {{"status": "started"}}

def on_enter_process(ctx):
    print(f"[{agent_name}] Processing data: {{ctx.input}}")
    return {{"status": "processed", "result": "success"}}

def on_enter_done(ctx):
    print(f"[{agent_name}] Done")
    return {{"status": "done"}}
'''
    with open(agent_dir / "process" / f"{agent_name}_hooks.py", "w", encoding="utf-8") as f:
        f.write(hooks_content)
        
    # Update agents.json
    agents_json_path = project_dir / "agents.json"
    with open(agents_json_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    config.setdefault("agents", {})[agent_name] = {
        "role": "sub",
        "workflow": f"agents/{agent_name}/process/{agent_name}_workflow.py",
        "description": "Auto-generated agent"
    }
    
    with open(agents_json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    print(f"Agent '{agent_name}' added successfully.")

def run_agent(args):
    """Run a specific agent from the current project"""
    from hfsm.config import Config
    from hfsm.registry import build_hfsm, load_workflow, bind_hooks
    from hfsm.machine import Machine
    from hfsm.runner import HookContext

    agent_name = args.name
    Config.init()  # Auto detect project root

    if args.purge:
        from hfsm.utils.cleaner import purge_all_runtime_data
        purge_all_runtime_data()

    # Load agents config and find the target agent
    agents_config = Config.load_agents_config()
    agent_cfg = agents_config.get('agents', {}).get(agent_name)
    if not agent_cfg:
        print(f"Error: Agent '{agent_name}' not found in agents.json")
        return

    # Load workflow module
    wf_path = agent_cfg.get('workflow', '')
    if not os.path.isabs(wf_path):
        wf_path = os.path.join(str(Config.get_root()), wf_path)
    if not os.path.exists(wf_path):
        print(f"Error: Workflow file not found: {wf_path}")
        return

    wf = load_workflow(agent_name, wf_path)

    # Build Machine
    machine = Machine(f"{agent_name}_machine", initial=getattr(wf, 'initial', 'start'))

    # Collect hook functions from workflow module
    hooks = getattr(wf, 'hooks', {})
    hook_fns = {}
    mod_dir = os.path.dirname(wf_path)

    for callback_name, func_ref in hooks.items():
        if '.' in func_ref:
            mod_name, fn_name = func_ref.rsplit('.', 1)
            hook_path = os.path.join(mod_dir, f'{mod_name}.py')
            if os.path.exists(hook_path):
                import importlib.util
                spec = importlib.util.spec_from_file_location(f"{agent_name}_{mod_name}", hook_path)
                hook_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(hook_mod)
                fn = getattr(hook_mod, fn_name, None)
                if fn:
                    # Wrap with HookContext injection
                    original_fn = fn
                    def make_wrapper(f, a_name):
                        def wrapper(context):
                            ctx = HookContext(a_name, machine_ctx=context)
                            return f(ctx)
                        return wrapper
                    hook_fns[callback_name] = make_wrapper(original_fn, agent_name)

    # Register states with their on_enter hooks
    for s in getattr(wf, 'states', []):
        hook_name = f"on_enter_{s['name']}"
        on_enter_fn = hook_fns.get(hook_name, None)
        machine.add_state(s['name'], on_enter=on_enter_fn, description=s.get('description', ''))

    # Register transitions
    for t in getattr(wf, 'transitions', []):
        machine.add_transition(trigger=t[0], source=t[1], dest=t[2])

    print(f"[*] Starting Agent: {agent_name}...")
    machine.start(context={})

    # Auto-run transitions
    while True:
        possible = [t for t in wf.transitions if t[1] == machine.current]
        if not possible:
            break
        t = possible[0]
        print(f"[Event] Sending trigger: {t[0]}")
        machine.send(t[0])

    print(f"[Done] Agent finished in state: {machine.current}")

    # Show output if any
    output_path = Config.get_agent_data_dir(agent_name) / 'output.json'
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            print(f"\n[Output] {agent_name} produced:")
            print(json.dumps(json.load(f), indent=4, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="HFSM Agent Framework CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("name", help="Project name")
    
    # Add agent command
    add_agent_parser = subparsers.add_parser("add-agent", help="Add a new agent to the project")
    add_agent_parser.add_argument("name", help="Agent name")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run an agent")
    run_parser.add_argument("name", help="Agent name to run")
    run_parser.add_argument("--purge", action="store_true", help="Clean runtime data before running")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_project(args)
    elif args.command == "add-agent":
        add_agent(args)
    elif args.command == "run":
        run_agent(args)

if __name__ == "__main__":
    main()