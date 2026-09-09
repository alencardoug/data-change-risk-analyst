"""Anexa ao trace do laboratório 01 uma nota calculada em código."""

import json

from _common import ARTIFACTS, parser, session


def main():
    args = parser(__doc__).parse_args()
    path = ARTIFACTS / "01-trace.json"
    if not path.exists():
        raise SystemExit("Execute primeiro 01_trace_python.py (com --send se quiser anexar feedback remoto).")
    saved = json.loads(path.read_text())
    score = int(saved["outputs"]["total_reais"] == 36)
    print(f"lab_total_correto={score}; origem=API/código, não anotação humana")
    with session(args, lab="04-feedback") as client:
        if client:
            if not saved["sent"]:
                raise SystemExit("O trace anterior era local. Rode 01_trace_python.py --send primeiro.")
            feedback = client.create_feedback(
                saved["run_id"], key="lab_total_correto", score=score,
                comment="Critério sintético: dois itens de R$18 devem somar R$36.",
                feedback_source_type="api",
            )
            print(f"Feedback criado: {feedback.id}. Abra o trace do laboratório 01.")


if __name__ == "__main__":
    main()
