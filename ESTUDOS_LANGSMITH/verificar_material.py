"""Valida links/formatos e executa modos locais dos labs com tentativas de rede bloqueadas."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

COURSE = Path(__file__).resolve().parent
ROOT = COURSE.parent


def check_files() -> None:
    broken = []
    markdown = list(COURSE.glob("*.md"))
    for path in markdown:
        text = path.read_text()
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            local = target.split("#")[0]
            if not (path.parent / local).exists():
                broken.append(f"{path.name}: {target}")
    if broken:
        raise SystemExit("Links quebrados:\n" + "\n".join(broken))
    for path in (COURSE / "labs").glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    for path in (COURSE / "dados").glob("*.json*"):
        if path.suffix == ".jsonl":
            for line in path.read_text().splitlines():
                if line.strip():
                    json.loads(line)
        else:
            json.loads(path.read_text())
    print(f"OK: links de {len(markdown)} documentos, sintaxe Python e arquivos de dados.", flush=True)


def check_scripts() -> None:
    commands = [
        (["00_doctor.py"], 0), (["01_trace_python.py"], 0),
        *[(["02_dcra.py", "--case", case], 0) for case in ["low", "medium", "high", "unknown", "gap"]],
        *[(["02_dcra.py", "--case", "medium", "--review", action], 0)
          for action in ["approve", "reject", "return", "return-evidence"]],
        (["03_failures.py"], 0), (["04_feedback.py"], 0), (["05_dataset.py"], 0),
        (["06_evaluate.py"], 0), (["07_real_model.py"], 0), (["08_judge.py"], 0),
        (["09_costs.py"], 0), (["10_privacy.py"], 0), (["11_rag.py"], 0),
        (["12_regression_gate.py", "--candidate", "baseline"], 0),
        (["12_regression_gate.py", "--candidate", "bug"], 1),
        (["13_prompts.py"], 0), (["14_context.py"], 0), (["15_langfuse.py"], 0),
    ]
    with tempfile.TemporaryDirectory(prefix="dcra-labs-offline-") as tmp:
        marker = Path(tmp) / "network-attempts.txt"
        # sitecustomize é carregado em cada subprocesso Python antes do script do laboratório.
        (Path(tmp) / "sitecustomize.py").write_text(
            "import os, socket\n"
            "def blocked(*args, **kwargs):\n"
            "    with open(os.environ['DCRA_LAB_NETWORK_MARKER'], 'a') as f:\n"
            "        f.write('network attempt blocked\\n')\n"
            "    raise RuntimeError('Network disabled by lab validation')\n"
            "socket.socket.connect = blocked\n"
            "socket.socket.connect_ex = blocked\n"
            "socket.create_connection = blocked\n"
            "socket.getaddrinfo = blocked\n"
        )
        env = os.environ | {"PYTHONPATH": tmp, "DCRA_LAB_NETWORK_MARKER": str(marker),
                           "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}
        for args, expected in commands:
            command = [sys.executable, str(COURSE / "labs" / args[0]), *args[1:]]
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                        text=True, timeout=40, check=False)
            except subprocess.TimeoutExpired as exc:
                raise SystemExit(f"Timeout: {' '.join(args)}") from exc
            if result.returncode != expected:
                raise SystemExit(f"Falhou: {' '.join(args)}\n{result.stdout}\n{result.stderr}")
            if marker.exists():
                raise SystemExit(f"Tentativa inesperada de rede: {' '.join(args)}\n{result.stderr}")
            print(f"OK: {' '.join(args)} (exit {expected})", flush=True)
    print(f"OK: {len(commands)} comandos; nenhuma tentativa de rede detectada.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--links-only", action="store_true")
    args = p.parse_args()
    check_files()
    if not args.links_only:
        check_scripts()


if __name__ == "__main__":
    main()
