"""Opcional e independente: mesmo pedido do lab 01 com observações do Langfuse."""

import argparse
import os
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--send", action="store_true")
    args = p.parse_args()
    if not args.send:
        print("Ensaio: pedido → consultar_cardapio → calcular_total → R$36. Sem rede/dependências extras.")
        print("Para enviar, siga 21-langfuse-otel.md e rode novamente com --send no ambiente separado.")
        return
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    for key in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"]:
        if not os.getenv(key) or "..." in os.environ[key]:
            raise SystemExit(f"Configure {key} para o workspace de estudo.")
    from langfuse import get_client

    client = get_client()
    try:
        with client.start_as_current_observation(name="pedido-restaurante", as_type="span",
                                                 input={"item": "risoto-de-dados", "quantidade": 2},
                                                 metadata={"synthetic": True}) as root:
            with client.start_as_current_observation(name="consultar_cardapio", as_type="tool") as tool:
                price = 18
                tool.update(output={"preco_reais": price})
            with client.start_as_current_observation(name="calcular_total", as_type="span") as calc:
                result = price * 2
                calc.update(output={"total_reais": result})
            root.update(output={"total_reais": result})
        print("R$36. Abra seu projeto de estudo na região configurada do Langfuse → Traces.")
    finally:
        client.flush()


if __name__ == "__main__":
    main()
