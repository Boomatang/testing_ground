import json
import multiprocessing as mp
import random
import sys
import time
from datetime import timedelta
from multiprocessing import Pool


def monte_carlo_pi(nsample):
    acc = 0
    for _ in range(nsample):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        if (x * x + y * y) <= 1:
            acc += 1

    return acc


if __name__ == "__main__":
    n = int(sys.argv[2])
    language = sys.argv[1]
    start = time.perf_counter_ns()
    cpu = mp.cpu_count()
    block = n // cpu
    enties = [block for _ in range(cpu)]

    with Pool(cpu) as p:
        acc = p.map(monte_carlo_pi, enties)

    result = 4 * sum(acc) / n

    end = time.perf_counter_ns() - start

    data = {
        "language": language,
        "format": "multi threaded",
        "time": end,
        "cores": cpu,
        "sample": n,
        "pi": result,
    }

    print(json.dumps(data))
    print(timedelta(milliseconds=data["time"] / 1_000_000), file=sys.stderr)
