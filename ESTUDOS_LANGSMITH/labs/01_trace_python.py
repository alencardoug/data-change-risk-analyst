"""Trace de Python puro: raiz + duas etapas, sem LangChain e sem modelo."""

from _common import parser, session, show_trace, write_json
from langsmith import trace, traceable


@traceable(run_type="tool", name="consultar_cardapio")
def menu(item: str) -> dict:
    return {"item": item, "preco_reais": 18, "disponivel": True}


@traceable(name="calcular_total")
def total(price: int, quantity: int) -> int:
    return price * quantity


def order(inputs: dict) -> dict:
    item = menu(inputs["item"])
    return {"total_reais": total(item["preco_reais"], inputs["quantidade"]), "moeda": "BRL"}


def main():
    args = parser(__doc__).parse_args()
    inputs = {"item": "risoto-de-dados", "quantidade": 2}
    with session(args, lab="01-python") as client:
        # `trace` abre o run raiz; as funções @traceable chamadas aqui dentro viram filhas dele.
        with trace("pedido-restaurante", inputs=inputs, metadata={"scenario": "pedido-valido"}) as run:
            result = order(inputs)
            run.end(outputs=result)
        if client:
            show_trace(client, args.project, str(run.id), start_time=run.start_time)
        print(result)
        # Endereço completo do run (projeto + start_time + id): o lab 04 precisa dele para anexar feedback.
        write_json("01-trace.json", {"outputs": result, "run_id": str(run.id), "project": args.project,
                                     "start_time": run.start_time.isoformat(), "sent": args.send})


if __name__ == "__main__":
    main()
