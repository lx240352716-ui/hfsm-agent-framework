# -*- coding: utf-8 -*-
"""
demo_agent Hooks

Use ctx.input to access input data.
Return a dictionary to automatically persist to output.json.
"""

def on_enter_start(ctx):
    print(f"[demo_agent] Entering start state")
    return {"status": "started"}

def on_enter_process(ctx):
    print(f"[demo_agent] Processing data: {ctx.input}")
    return {"status": "processed", "result": "success"}

def on_enter_done(ctx):
    print(f"[demo_agent] Done")
    return {"status": "done"}
