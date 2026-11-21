"""Run the Lab 6 agent on an After-Hours acceptance check."""

import argparse
import os
from pathlib import Path

import core
import models


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY in your terminal first.")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", choices=("AH-T01", "AH-T02", "AH-T03", "AH-T04", "AH-T05", "AH-BROWSER"))
    task_id = parser.parse_args().task_id

    work = Path("/work")
    specification = (work / "D1-After-Hours-Tasks.md").read_text()
    task = specification.split(f"### {task_id}", 1)[1].split("\n##", 1)[0]
    if task_id == "AH-BROWSER":
        target, test_file = "app.py", "test_after_hours_app.py"
    else:
        target, test_file = "after_hours.py", "test_after_hours.py"
    acceptance_test = (work / "tests" / test_file).read_text()
    meter = core.Meter()

    def call_gemini(system, messages):
        print(f"Waiting for Gemini (request {models.CALLS + 1})…", flush=True)
        return models.call_model(system, messages, tools=core.TOOLS)

    def approve(name, arguments):
        if name == "write_file" and arguments.get("path") == target:
            return core.ask_human(name, arguments)
        return False

    try:
        result = core.react(
            str(work),
            f"Implement {task_id} in {target} using the "
            "contract below. The spec and complete test are included. Keep the "
            "test intact and run the tests before finishing."
            f"\n\n### {task_id}{task}\nAcceptance test:\n{acceptance_test}",
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
        raise SystemExit(1)


if __name__ == "__main__":
    main()
