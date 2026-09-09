"""Eval de interpretação: modelo real, referências manuais e duas versões de prompt."""

import hashlib
import importlib
import json

from _common import COURSE, configure, manifest, parser, real_model, require_real, session, write_json

CANDIDATE = (
    "Extract a data schema change. Accept English and Brazilian Portuguese. "
    "Supported operations: DROP_COLUMN, ALTER_COLUMN and ADD_INDEX. "
    "Copy table and column identifiers exactly. Do not invent identifiers. "
    "For ADD_INDEX preserve the order of index_columns; target_column should be null. "
    "For DROP_COLUMN and ALTER_COLUMN index_columns must be empty. "
    "For ALTER_COLUMN describe the requested change in alter_detail."
)
FIELDS = ["operation", "target_table", "target_column", "index_columns"]


def exact_structure(outputs: dict, reference_outputs: dict) -> dict:
    correct = not outputs.get("error") and all(
        outputs.get(field) == reference_outputs.get(field) for field in FIELDS
    )
    return {"key": "structure_exact", "score": int(correct)}


def make_target(model, variant: str, prompt: str):
    from langsmith import traceable

    from dcra.domain.models import StructuredChange
    from dcra.llm.factory import interpret

    @traceable(name=f"interpretacao-{variant}")
    def target(inputs: dict) -> dict:
        # A referência não é recebida. Erros de rede continuam erros de execução.
        if variant == "baseline":
            sc = interpret(model, inputs["text"])
        else:
            sc = model.with_structured_output(StructuredChange).invoke(
                [("system", prompt), ("human", inputs["text"])]
            )
            sc = StructuredChange.model_validate(sc)
        return {field: sc.model_dump(mode="json")[field] for field in FIELDS}

    return target


def main():
    p = parser(__doc__)
    p.add_argument("--real", action="store_true")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--variant", choices=["baseline", "candidate", "both"], default="baseline")
    args = p.parse_args()
    configure(args)
    path = COURSE / "dados" / "interpretacao.jsonl"
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not 1 <= args.limit <= len(cases) or not 1 <= args.repetitions <= 3:
        raise SystemExit(f"Use --limit entre 1 e {len(cases)} e --repetitions entre 1 e 3.")
    variants = ["baseline", "candidate"] if args.variant == "both" else [args.variant]
    calls = args.limit * args.repetitions * len(variants)
    print(f"{calls} execuções de target; retries podem ampliar chamadas.")
    if not args.real:
        print("Ensaio sem rede/modelo. Adicione --real para executar; --send também publica resultados.")
        print("Primeira entrada:", cases[0]["inputs"])
        return
    require_real(args)
    with session(args, lab="07-modelo-real") as client:
        from dcra.llm.factory import _INTERPRET_SYS

        model = real_model()
        data = None
        if client:
            info = importlib.import_module("05_dataset").publish_dataset(
                client, cases, data_path=path, prefix="dcra-estudo-interpretacao", artifact="07-dataset.json"
            )
            by_case = {e.metadata["case_id"]: e for e in client.list_examples(
                dataset_id=info["dataset_id"], as_of=info["as_of"]
            )}
            data = [by_case[case["id"]] for case in cases[:args.limit]]
        for variant in variants:
            prompt = _INTERPRET_SYS if variant == "baseline" else CANDIDATE
            metadata = {"variant": variant, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                        "model": model.model_name if hasattr(model, "model_name") else str(type(model)),
                        "purpose": "interpretation_eval"}

            target = make_target(model, variant, prompt)

            if client:
                result = client.evaluate(target, data=data, evaluators=[exact_structure],
                                         experiment_prefix=f"interpretacao-{variant}",
                                         metadata=metadata, max_concurrency=1,
                                         num_repetitions=args.repetitions)
                result.wait()
                print("Experimento:", result.experiment_name)
            else:
                rows = []
                for repeat in range(args.repetitions):
                    for case in cases[:args.limit]:
                        output = target(case["inputs"])
                        rows.append({"id": case["id"], "repeat": repeat, "outputs": output,
                                     "score": exact_structure(output, case["outputs"])["score"]})
                print(variant, "structure_exact=", sum(row["score"] for row in rows) / len(rows))
                write_json(f"07-{variant}.json", {"rows": rows, "metadata": metadata, "manifest": manifest()})
        write_json("07-manifesto.json", manifest())


if __name__ == "__main__":
    main()
