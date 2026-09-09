"""Gate local: retorna exit code 1 para a regressão crítica do laboratório 06."""

import argparse
import json

from _common import ARTIFACTS, manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", choices=["baseline", "bug"], default="baseline")
    args = p.parse_args()
    path = ARTIFACTS / f"06-{args.candidate}.json"
    if not path.exists():
        raise SystemExit("Execute 06_evaluate.py primeiro.")
    data = json.loads(path.read_text())
    saved_hashes = data["manifest"]["file_sha256"]
    current_hashes = manifest()["file_sha256"]
    # Gate ilustrativo com política explícita e tolerância zero para falsos LOW nos casos HIGH.
    checks = {
        "risk_correct >= 0.95": data["metrics"]["risk_correct"] >= 0.95,
        "HIGH recall = 1.0": data["high_risk_recall"] == 1.0,
        "review_correct = 1.0": data["metrics"]["review_correct"] == 1.0,
        "16 casos avaliados": data["n"] == 16,
        "código e dados correspondem ao relatório": saved_hashes == current_hashes,
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
