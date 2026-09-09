"""Redação de um e-mail sintético nos I/O de UMA função; não é filtro universal."""

import re

from _common import parser, session, traced_call, write_json
from langsmith import traceable

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(value):
    if isinstance(value, str):
        return EMAIL.sub("[EMAIL_REMOVIDO]", value)
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


@traceable(name="contato-redigido", process_inputs=redact, process_outputs=redact)
def contact(inputs: dict) -> dict:
    return {"ack": f"Recebido de {inputs['email']}"}


def main():
    args = parser(__doc__).parse_args()
    raw = {"email": "pessoa@example.com"}
    with session(args, lab="10-privacidade") as client:
        # O wrapper externo também recebe SOMENTE a entrada já redigida.
        # A função contact usa o raw sintético dentro da closure e seus próprios processadores.
        def outer(inputs):
            output = contact(raw)
            return redact(output)

        output, _ = traced_call(client, args.project, "privacidade", outer, redact(raw))
    print("Entrada original local:", raw)
    print("Saída local de contact (sem tracing):")
    # Não chamamos novamente a função decorada fora da session para evitar um root extra.
    print({"ack": f"Recebido de {raw['email']}"})
    print("Payload do wrapper enviado/mostrado:", output)
    write_json("10-privacidade.json", {"synthetic": True, "redacted": output})


if __name__ == "__main__":
    main()
