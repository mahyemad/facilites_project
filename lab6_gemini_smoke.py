"""Read the D1 task specs with the Lab 6 loop and Lab 9 Gemini adapter."""

import os
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

import core
import models


def main(project: Path) -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY before starting the container.")

    read_tools = [tool for tool in core.TOOLS if tool["name"] == "read_file"]
    core.POLICY = {"read_file": "allow"}
    spec = "D1-After-Hours-Tasks.md"

    def call_gemini(system, messages):
        print(f"Waiting for Gemini (request {models.CALLS + 1})…", flush=True)
        try:
            return models.call_model(system, messages, tools=read_tools)
        except TimeoutError:
            raise SystemExit(
                "Gemini did not respond within 120 seconds. No response or token "
                "count was received for this request."
            ) from None

    with TemporaryDirectory() as directory:
        copyfile(project / spec, Path(directory) / spec)
        result = core.react(
            directory,
            f"Read {spec} using read_file and summarize AH-T01 through AH-T05.",
            model=call_gemini,
            system="You are checking that you can read a project specification.",
            verify_done=False,
            quiet=True,
        )

    print(result["summary"])
    print(
        f"Stopped: {result['stop']} | {result['calls']} calls | "
        f"{result['tokens_in']} input tokens | {result['tokens_out']} output tokens | "
        f"${result['cost']:.5f} at configured rates"
    )


if __name__ == "__main__":
    main(Path("/project"))
