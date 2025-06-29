import json
import random
import sys
import time
from datetime import timedelta

from numba import njit


@njit
def monte_carlo_pi(nsample):
    acc = 0
    for _ in range(nsample):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        if (x * x + y * y) <= 1:
            acc += 1

    return 4 * acc / nsample


if __name__ == "__main__":
    n = int(sys.argv[1])
    start = time.perf_counter_ns()
    result = monte_carlo_pi(n)
    end = time.perf_counter_ns() - start

    data = {
        "language": "python (numba)",
        "format": "single threaded",
        "time": end,
        "cores": 1,
        "sample": n,
        "pi": result,
    }

    print(json.dumps(data))
    print(timedelta(milliseconds=data["time"] / 1_000_000), file=sys.stderr)
