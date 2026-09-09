"""Trace de Python puro: raiz + duas etapas, sem LangChain e sem modelo."""

from _common import parser, session, traced_call, write_json
from langsmith import traceable


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
    with session(args, lab="01-python") as client:
        result, run_id = traced_call(client, args.project, "pedido-restaurante", order,
                                    {"item": "risoto-de-dados", "quantidade": 2},
                                    metadata={"scenario": "pedido-valido"})
        print(result)
        write_json("01-trace.json", {"outputs": result, "run_id": run_id, "sent": args.send})


if __name__ == "__main__":
    main()
