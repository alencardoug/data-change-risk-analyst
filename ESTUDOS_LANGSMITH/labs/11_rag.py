"""RAG de papel: separa erro de recuperação de erro de resposta, sem embeddings/LLM."""

from _common import parser, session, show_trace, write_json
from langsmith import trace, traceable

DOCS = {
    "prazo": "Pedidos podem ser devolvidos em até 7 dias após a entrega.",
    "frete": "O frete padrão demora de 3 a 5 dias úteis.",
}


@traceable(run_type="retriever", name="recuperar_politica")
def retrieve(question: str, mode: str) -> list[dict]:
    key = "frete" if mode == "bad_retrieval" else "prazo"
    return [{"id": key, "text": DOCS[key]}]


@traceable(name="responder_fixture")
def answer(docs: list[dict], mode: str) -> dict:
    if mode == "hallucination":
        return {"days": 90, "answer": "Você tem 90 dias para devolver.", "citations": ["prazo"]}
    if docs[0]["id"] == "prazo":
        return {"days": 7, "answer": "Até 7 dias após a entrega.", "citations": ["prazo"]}
    return {"days": None, "answer": "Não tenho a política de devolução no contexto.", "citations": []}


def rag(inputs: dict) -> dict:
    docs = retrieve(inputs["question"], inputs["mode"])
    result = answer(docs, inputs["mode"])
    return result | {"retrieved_ids": [doc["id"] for doc in docs]}


def score(output: dict) -> dict:
    # Oráculo estreito deste corpus, não um avaliador semântico genérico.
    return {"retrieval_recall_at_1": int("prazo" in output["retrieved_ids"]),
            "answer_correct": int(output["days"] == 7),
            "supported_or_abstained": int(output["days"] is None or (
                output["days"] == 7 and "prazo" in output["retrieved_ids"]
            ))}


def main():
    args = parser(__doc__).parse_args()
    rows = []
    with session(args, lab="11-rag") as client:
        for mode in ["good", "bad_retrieval", "hallucination"]:
            inputs = {"question": "Qual é o prazo de devolução?", "mode": mode}
            with trace(f"rag-{mode}", inputs=inputs) as run:
                output = rag(inputs)
                run.end(outputs=output)
            if client:
                show_trace(client, args.project, str(run.id), start_time=run.start_time)
            row = {"mode": mode, "outputs": output, "scores": score(output)}
            print(row)
            rows.append(row)
    write_json("11-rag.json", rows)


if __name__ == "__main__":
    main()
