"""Contexto entre threads: demonstra a perda e a propagação explícita."""

from concurrent.futures import ThreadPoolExecutor
from contextvars import Context, ContextVar, copy_context

from _common import parser, session, show_trace, write_json
from langsmith import trace, traceable

CASE = ContextVar("lab_case", default="sem-contexto")


@traceable(name="worker")
def worker(value: int) -> dict:
    return {"case_id": CASE.get(), "result": value * 2}


def pipeline(inputs: dict) -> dict:
    token = CASE.set(inputs["case_id"])
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            # Context() vazio simula processo/thread sem o contexto do chamador, em qualquer Python.
            lost = pool.submit(Context().run, worker, 10).result()
            propagated = pool.submit(copy_context().run, worker, 10).result()
        return {"lost": lost, "propagated": propagated}
    finally:
        CASE.reset(token)


def main():
    args = parser(__doc__).parse_args()
    with session(args, lab="14-contexto") as client:
        inputs = {"case_id": "caso-sintetico-42"}
        with trace("contexto-threads", inputs=inputs, metadata={"thread_id": "caso-sintetico-42"}) as run:
            output = pipeline(inputs)
            run.end(outputs=output)
        if client:
            show_trace(client, args.project, str(run.id), start_time=run.start_time)
        print(output)
        write_json("14-contexto.json", output)


if __name__ == "__main__":
    main()
