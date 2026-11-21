"""Run the Lab 6 agent on an After-Hours acceptance check."""

import argparse
import os
from pathlib import Path

import core
import models


BACKLOG_TASKS = ("AH-T06", "AH-T07", "AH-T08", "AH-T09", "AH-T10")


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY in your terminal first.")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task_id",
        choices=("AH-T01", "AH-T02", "AH-T03", "AH-T04", "AH-T05", *BACKLOG_TASKS, "AH-BROWSER"),
    )
    task_id = parser.parse_args().task_id

    work = Path("/work")
    specification = (work / "D1-After-Hours-Tasks.md").read_text()
    task = specification.split(f"### {task_id}", 1)[1].split("\n##", 1)[0]
    if task_id == "AH-BROWSER":
        target, test_file = "app.py", "test_after_hours_app.py"
    elif task_id in BACKLOG_TASKS:
        target = "after_hours.py"
        test_file = f"test_{task_id.lower().replace('-', '_')}.py"
    else:
        target, test_file = "after_hours.py", "test_after_hours.py"
    acceptance_test = (work / "tests" / test_file).read_text()
    existing_code = ""
    tools = core.TOOLS
    write_tool = "write_file"
    if task_id in BACKLOG_TASKS:
        write_tool = "edit_service"
        tools = [tool for tool in tools if tool["name"] != "write_file"] + [{
            "name": write_tool,
            "description": "Replace one exact snippet in after_hours.py. Use a small, unique old snippet.",
            "input_schema": {
                "type": "object",
                "properties": {"old": {"type": "string"}, "new": {"type": "string"}},
                "required": ["old", "new"],
            },
        }]

        def edit_service(old, new):
            path = work / target
            source = path.read_text()
            if not old or source.count(old) != 1:
                return "No change. Supply an exact snippet that occurs once in after_hours.py."
            path.write_text(source.replace(old, new, 1))
            return "Updated after_hours.py."

        core.POLICY[write_tool] = "ask"
        core.HANDLERS[write_tool] = edit_service
        existing_code = (
            "\n\nCurrent after_hours.py (complete):\n"
            + (work / target).read_text()
            + "\nUse edit_service to save small, targeted changes to after_hours.py. "
            "To add a function, replace a unique nearby line with that line and the new function. "
            "Preserve existing behavior and run the tests before reporting completion."
        )
    meter = core.Meter()

    def call_gemini(system, messages):
        print(f"Waiting for Gemini (request {models.CALLS + 1})…", flush=True)
        return models.call_model(system, messages, tools=tools)

    def approve(name, arguments):
        if name == "edit_service" and write_tool == name:
            return core.ask_human(name, arguments)
        if name == write_tool == "write_file" and arguments.get("path") == target:
            return core.ask_human(name, arguments)
        return False

    try:
        result = core.react(
            str(work),
            f"Implement {task_id} in {target} using the "
            "contract below. The spec and complete test are included. Keep the "
            "test intact and run the tests before finishing."
            f"\n\n### {task_id}{task}\nAcceptance test:\n{acceptance_test}{existing_code}",
            model=call_gemini,
            approve=approve,
            meter=meter,
        )
    except TimeoutError:
        raise SystemExit(
            f"Gemini timed out. Received usage for {meter.calls} completed calls: "
            f"{meter.tokens_in} input + {meter.tokens_out} output tokens, "
            f"${meter.cost:.5f} at configured rates. Any approved edits remain in /work."
        ) from None

    if result["stop"] != "done (tests pass)":
        if result["summary"]:
            print(f"Agent's last message: {result['summary']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
