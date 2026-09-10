"""Compara baseline e bug localmente ou como experimentos no LangSmith."""

import importlib
import json
from functools import partial

from _common import ARTIFACTS, manifest, parser, read_cases, session, write_json
from _evaluators import EVALUATORS, SUMMARY_EVALUATORS, high_risk_recall


def evaluate_local(cases: list[dict], variant: str) -> dict:
    from _dcra import target

    rows = []
    for case in cases:
        outputs = target(case["inputs"], variant=variant)
        scores = {m["key"]: m["score"] for ev in EVALUATORS for m in [ev(outputs, case["outputs"]) ]}
        rows.append({"case_id": case["id"], "slice": case["metadata"]["slice"],
                     "outputs": outputs, "reference": case["outputs"], "scores": scores})
    means = {ev.__name__: sum(r["scores"][ev.__name__] for r in rows) / len(rows) for ev in EVALUATORS}
    return {"variant": variant, "n": len(rows), "metrics": means,
            "high_risk_recall": high_risk_recall(rows), "rows": rows, "manifest": manifest()}


def main():
    p = parser(__doc__)
    p.add_argument("--variant", choices=["baseline", "bug", "both"], default="both")
    args = p.parse_args()
    variants = ["baseline", "bug"] if args.variant == "both" else [args.variant]
    with session(args, lab="06-eval") as client:
        from _dcra import target

        if client:
            path = ARTIFACTS / "05-dataset.json"
            if not path.exists():
                raise SystemExit("Execute 05_dataset.py --send antes da avaliação remota.")
            info = json.loads(path.read_text())
            # Valida/reutiliza a versão do arquivo atual antes de fixar o snapshot para ambos.
            current = importlib.import_module("05_dataset").publish_dataset(client, read_cases())
            if current["source_sha256"] != info["source_sha256"]:
                raise SystemExit("Arquivo de dados mudou. Dataset atualizado; execute este comando de novo.")
            examples = list(client.list_examples(dataset_id=info["dataset_id"], as_of=info["as_of"]))
            for variant in variants:
                results = client.evaluate(
                    partial(target, variant=variant), data=examples, evaluators=EVALUATORS,
                    summary_evaluators=SUMMARY_EVALUATORS,
                    experiment_prefix=f"dcra-{variant}", max_concurrency=1, num_repetitions=1,
                    metadata={"variant": variant, "dataset_as_of": info["as_of"],
                              "dataset_sha256": info["source_sha256"], "evaluator_version": "contratos-v1"},
                    description="Grafo real com modelo fixture; mede contratos, não qualidade do LLM.",
                )
                results.wait()
                print(f"Experimento: {results.experiment_name}")
        else:
            for variant in variants:
                result = evaluate_local(read_cases(), variant)
                print(variant, result["metrics"], f"recall HIGH={result['high_risk_recall']}")
                write_json(f"06-{variant}.json", result)


if __name__ == "__main__":
    main()
