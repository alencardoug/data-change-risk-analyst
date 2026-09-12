"""Redação de um e-mail sintético nos I/O de UMA função; não é filtro universal."""

import re

from _common import parser, session, show_trace, write_json
from langsmith import trace, traceable

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
        # O run raiz recebe SOMENTE entrada e saída já redigidas; `contact` continua vendo o e-mail
        # sintético e aplica os próprios processadores ao seu run filho.
        with trace("privacidade", inputs=redact(raw)) as run:
            output = redact(contact(raw))
            run.end(outputs=output)
        if client:
            show_trace(client, args.project, str(run.id), start_time=run.start_time)
    print("Entrada original local:", raw)
    print("Saída local de contact (sem tracing):")
    # Não chamamos novamente a função decorada fora da session para evitar um root extra.
    print({"ack": f"Recebido de {raw['email']}"})
    print("Payload do wrapper enviado/mostrado:", output)
    write_json("10-privacidade.json", {"synthetic": True, "redacted": output})


if __name__ == "__main__":
    main()
