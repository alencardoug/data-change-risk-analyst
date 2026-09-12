"""Cria/reutiliza dataset de estudo identificado pelo hash do arquivo local."""

from uuid import NAMESPACE_URL, uuid5

from _common import COURSE, digest, parser, read_cases, session, write_json


def publish_dataset(client, cases: list[dict], *, data_path=None,
                    prefix: str = "dcra-estudo-contratos", artifact: str = "05-dataset.json") -> dict:
    from langsmith.utils import LangSmithConflictError, LangSmithNotFoundError

    fingerprint = digest(data_path or (COURSE / "dados" / "casos.jsonl"))
    name = f"{prefix}-{fingerprint[:12]}"
    try:
        ds = client.read_dataset(dataset_name=name)
    except LangSmithNotFoundError:
        try:
            ds = client.create_dataset(name, description="Casos sintéticos do curso; gabarito manual.",
                                       metadata={"source_sha256": fingerprint})
        except LangSmithConflictError:
            ds = client.read_dataset(dataset_name=name)
    examples = [{
        "id": str(uuid5(NAMESPACE_URL, f"{name}/{case['id']}")),
        "inputs": case["inputs"], "outputs": case["outputs"],
        "metadata": case["metadata"] | {"case_id": case["id"]},
    } for case in cases]
    existing = {str(e.id): e for e in client.list_examples(dataset_id=ds.id)}
    expected_ids = {e["id"] for e in examples}
    if set(existing) - expected_ids:
        raise SystemExit("Dataset remoto tem casos extras. Use uma nova versão local; não sobrescreva.")
    for item in examples:
        previous = existing.get(item["id"])
        if previous and (previous.inputs != item["inputs"] or previous.outputs != item["outputs"]):
            raise SystemExit("Dataset remoto foi editado. Não vou misturar versões diferentes.")
    missing = [item for item in examples if item["id"] not in existing]
    if missing:
        client.create_examples(dataset_id=ds.id, examples=missing)
    # A versão "latest" vira o carimbo `as_of` que fixa o snapshot usado pelos experimentos.
    dataset_version = client.read_dataset_version(dataset_id=ds.id, tag="latest")
    info = {"dataset_name": name, "dataset_id": str(ds.id), "source_sha256": fingerprint,
            "as_of": dataset_version.as_of.isoformat(), "examples": len(examples)}
    write_json(artifact, info)
    print(f"Abra https://smith.langchain.com → Datasets & Experiments → {name}")
    return info


def main():
    args = parser(__doc__).parse_args()
    cases = read_cases()
    print(f"{len(cases)} casos: inputs, outputs de referência e metadata.")
    print(cases[0])
    with session(args, lab="05-dataset") as client:
        if client:
            publish_dataset(client, cases)
        else:
            print("Modo local: nenhum dataset remoto criado. Use --send para publicar os casos sintéticos.")


if __name__ == "__main__":
    main()
