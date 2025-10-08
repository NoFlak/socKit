"""Command execution helpers with logging and timeout handling."""

from __future__ import annotations

import subprocess
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

from config import load_config
from logging_utils import write_action


@dataclass
class CommandResult:
    description: str
    output: str
    return_code: int
    duration: float

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


def execute_command(
    command: str,
    description: str,
    *,
    timeout: Optional[int] = None,
    shell: bool = True,
) -> Optional[CommandResult]:
    """Execute a command and stream output while logging results."""

    config = load_config()
    effective_timeout = timeout or config.timeout
    print(f"\n[EXEC] {description}")
    print(f"[CMD ] {command}")

    start_time = time.monotonic()
    try:
        process = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        message = f"Failed to start command '{description}': {exc}"
        print(f"[ERROR] {message}")
        write_action(message, level="ERROR", context={"command": command})
        return None

    output_lines = []
    try:
        while True:
            if process.stdout is None:
                break
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end="")
                output_lines.append(line.rstrip())
            if effective_timeout and (time.monotonic() - start_time) > effective_timeout:
                process.kill()
                raise subprocess.TimeoutExpired(command, effective_timeout)
        process.wait()
    except subprocess.TimeoutExpired:
        process.kill()
        message = f"Command '{description}' timed out after {effective_timeout} seconds."
        print(f"[ERROR] {message}")
        write_action(message, level="ERROR", context={"command": command, "timeout": effective_timeout})
        return None

    duration = time.monotonic() - start_time
    combined_output = "\n".join(output_lines)
    result = CommandResult(description=description, output=combined_output, return_code=process.returncode, duration=duration)

    if result.succeeded:
        write_action(
            f"{description} completed successfully.",
            level="INFO",
            context={"command": command, "duration": f"{duration:.2f}s"},
            detailed_results=combined_output,
        )
        print(f"[SUCCESS] {description} finished in {duration:.2f}s")
    else:
        message = f"Command '{description}' exited with code {result.return_code}."
        print(f"[ERROR] {message}")
        write_action(
            message,
            level="ERROR",
            context={"command": command, "duration": f"{duration:.2f}s"},
            detailed_results=combined_output,
        )

    return result


def execute_command_async(
    command: str,
    description: str,
    *,
    timeout: Optional[int] = None,
    shell: bool = True,
) -> Future[Optional[CommandResult]]:
    """Execute a command asynchronously in a background thread."""

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(execute_command, command, description, timeout=timeout, shell=shell)
    print(f"[ASYNC] {description} running in the background...")
    return future