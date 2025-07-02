import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from pydantic import BaseModel, field_validator
from rich import print
from rich.progress import track


class BenchmarkResult(BaseModel):
    language: str
    format: str
    time: timedelta
    cores: int
    sample: int
    pi: float

    @field_validator("time", mode="before")
    def convert_ns_to_timedelta(cls, v):
        if isinstance(v, (int, float)):
            return timedelta(microseconds=v / 1_000)  # ns to µs
        return v


def escalating_sequence():
    base = 10
    while True:
        for i in range(1, 10):
            yield i * base
        base *= 10


def is_graphable(group: tuple, element: BenchmarkResult, limit: timedelta) -> bool:
    return (
        element.language == group[0]
        and element.format == group[1]
        and element.time < limit
    )


def create_graph(groups, entries, limit, image=None, show=True):
    colors = {
        "python": "tab:blue",
        "python (numba)": "tab:orange",
        "zig": "tab:green",
        "rust": "tab:red",
        "julia": "tab:purple",
        "pypy": "tab:brown",
        "golang": "tab:pink",
    }

    line_styles = {"single threaded": "dashed", "multi threaded": "solid"}
    plt.figure(figsize=(12, 6))
    for group in groups:
        samples = [e.sample for e in entries if is_graphable(group, e, limit)]
        time_ = [
            e.time.total_seconds() for e in entries if is_graphable(group, e, limit)
        ]
        # print(samples)
        plt.plot(
            time_,
            samples,
            label=f"{group[0]} - {group[1]}",
            color=colors[group[0]],
            linestyle=line_styles[group[1]],
        )

    plt.title(f"Sample size in Monte Carlo Pi in {limit.total_seconds()}seconds")
    plt.xlabel("Time Taken")
    plt.ylabel("Sample Size")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    if show:
        plt.show()

    if image is not None:
        plt.savefig(image)


def better_fit(
    retry: int, past: int, future: int, script: str, limit: timedelta
) -> BenchmarkResult:

    maybe = None
    value = past + ((future - past) / 2)
    while retry > 0:
        result = subprocess.run(script + [str(int(value))], capture_output=True)
        # print(result)
        data = json.loads(result.stdout.decode())
        a = BenchmarkResult(**data)
        if a.time < limit:
            maybe = a
            value = a.sample + ((future - a.sample) / 2)
        else:
            value = past + ((a.sample - past) / 2)
        retry -= 1

    return maybe

    pass


def process_sripts(scripts, limit):
    seq = escalating_sequence()
    block = next(seq)
    past = 0
    current_round = scripts
    next_round = []
    groups = set()
    retry = 3

    process = True
    entries = []
    while process:
        for script in track(
            current_round,
            description=f"Processing sample size: {block:,}, scripts: {len(current_round)}",
        ):
            # print(script)
            result = subprocess.run(script + [str(block)], capture_output=True)
            # print(result)
            data = json.loads(result.stdout.decode())
            a = BenchmarkResult(**data)
            entries.append(a)
            groups.add((a.language, a.format))
            if a.time < limit:
                next_round.append(script)
            else:
                maybe = better_fit(retry, past, block, script, limit)
                if maybe is not None:
                    entries.append(maybe)

        current_round = next_round
        next_round = []
        if len(current_round) == 0:
            process = False
        past = block
        block = next(seq)

    return groups, entries


def file_name(limit: timedelta, path: str) -> str:
    return f"{path}/{limit.total_seconds()}_{datetime.now().timestamp()}.png"


def create_limit(milliseconds=None, seconds=None, minutes=None) -> timedelta:
    if milliseconds is None:
        milliseconds = 0

    if seconds is None:
        seconds = 0

    if minutes is None:
        minutes = 0

    return timedelta(minutes=minutes, seconds=seconds, milliseconds=milliseconds)


if __name__ == "__main__":
    # TODO: Set up some argparse here to allow the selection of time limit and single vs multi threaded scripts

    scripts = [
        ["python", "./src/monte_carlo_pi/python_pure.py", "python"],
        ["pypy", "./src/monte_carlo_pi/python_pure.py", "pypy"],
        ["python", "./src/monte_carlo_pi/python_numba.py"],
        ["go", "run", "./src/monte_carlo_pi/main.go", "single"],
        ["cargo", "run", "--release", "single"],
        ["zig-out/bin/main", "single"],
        ["julia", "./src/monte_carlo_pi/main.jl", "single"],
        ["python", "./src/monte_carlo_pi/python_pure_mp.py", "python"],
        ["pypy", "./src/monte_carlo_pi/python_pure_mp.py", "pypy"],
        ["python", "./src/monte_carlo_pi/python_numba_mp.py"],
        ["go", "run", "./src/monte_carlo_pi/main.go", "multi"],
        ["cargo", "run", "--release", "multi"],
        ["zig-out/bin/main", "multi"],
        ["julia", "-t", str(os.cpu_count()), "./src/monte_carlo_pi/main.jl", "multi"],
    ]
    limits = [
        timedelta(milliseconds=50),
        timedelta(milliseconds=500),
        timedelta(seconds=5),
        timedelta(minutes=1),
    ]

    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", help="Where to save the images to.")
    parser.add_argument(
        "--full-run",
        action="store_true",
        help="Run the full range of limit test.",
    )
    parser.add_argument(
        "--milliseconds", type=int, help="Set the milliseconds for none full runs"
    )
    parser.add_argument(
        "--seconds", type=int, help="Set the seconds for none full runs"
    )
    parser.add_argument(
        "--minutes", type=int, help="Set the minutes for none full runs"
    )

    args = parser.parse_args()

    if args.full_run:
        if args.out_dir is None:
            raise Exception("The out dir needs to be set full-run")
        for limit in limits:
            groups, entries = process_sripts(scripts, limit)
            create_graph(
                groups, entries, limit, show=False, image=file_name(limit, args.out_dir)
            )
        exit()

    print(args)

    limit = create_limit(
        milliseconds=args.milliseconds, seconds=args.seconds, minutes=args.minutes
    )

    groups, entries = process_sripts(scripts, limit)
    create_graph(groups, entries, limit)
