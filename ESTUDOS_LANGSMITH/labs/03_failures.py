"""Erros e lentidão injetados localmente: não dependem de derrubar serviços."""

import time
from uuid import uuid4

from _common import parser, session, show_trace, write_json
from langsmith import traceable


@traceable(run_type="tool", name="ler_catalogo")
def read_catalog(mode: str, attempt: int) -> dict:
    time.sleep(0.18 if mode == "slow" else 0.02)
    if mode in {"fallback", "crash"} or (mode == "retry" and attempt == 1):
        raise TimeoutError("timeout sintético do laboratório")
    return {"dependency_count": 2, "status": "OBTAINED"}


def pipeline(inputs: dict) -> dict:
    for attempt in range(1, 3):
        try:
            result = read_catalog(inputs["mode"], attempt)
            return result | {"attempts": attempt, "degraded": False}
        except TimeoutError:
            if attempt == 2:
                if inputs["mode"] == "crash":
                    raise
                return {"status": "UNAVAILABLE", "dependency_count": None,
                        "attempts": attempt, "degraded": True}
    raise AssertionError("inalcançável")


def main():
    args = parser(__doc__).parse_args()
    rows = []
    with session(args, lab="03-falhas") as client:
        for mode in ["slow", "retry", "fallback", "crash"]:
            run_id = str(uuid4())
            start = time.perf_counter()
            try:
                output = traceable(pipeline, name=f"falha-{mode}")(
                    {"mode": mode}, langsmith_extra={"run_id": run_id, "metadata": {"scenario": mode}}
                )
            except TimeoutError:
                output = {"error": "TimeoutError", "expected": True}
            elapsed = round(time.perf_counter() - start, 3)
            rows.append({"mode": mode, "seconds": elapsed, "outputs": output, "run_id": run_id})
            print(mode, output, f"{elapsed}s")
            if client:
                show_trace(client, args.project, run_id)
    write_json("03-falhas.json", rows)


if __name__ == "__main__":
    main()
