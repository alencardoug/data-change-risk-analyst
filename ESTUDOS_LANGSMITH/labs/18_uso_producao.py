"""Uso real do app publicado, lido do banco em modo somente leitura: casos, risco, decisões e espera."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime

from _common import ROOT, write_json

# Cada consulta responde a uma pergunta e diz qual é o seu denominador. `analysis_record` guarda
# um registro por caso FINALIZADO (finalize em nodes.py); casos parados na revisão só existem
# nos checkpoints do LangGraph. Contar uma tabela e chamar de "uso" esconde essa diferença.
#
# Duas armadilhas conferidas contra um banco de desenvolvimento:
# - `created_at` do registro é a hora da FINALIZAÇÃO, não do pedido; a hora do pedido está em
#   change_request.submitted_at. Medir espera humana por created_at dá um número negativo.
# - um registro sem avaliação de risco (risk_assessments vazio) devolve NULL na categoria;
#   NULL não é LOW, e o SQL o nomeia como tal.
PEDIDO_EM = "(change_request->>'submitted_at')::timestamptz"
DECIDIDO_EM = "(review_actions->-1->>'decided_at')::timestamptz"
JANELA = f"{PEDIDO_EM} >= now() - make_interval(days => %(dias)s)"

CONSULTAS: dict[str, tuple[str, str]] = {
    "casos_por_dia": (
        "Casos concluídos, por dia do PEDIDO, na janela. Um caso = um registro finalizado.",
        f"SELECT date_trunc('day', {PEDIDO_EM})::date AS dia, count(*) AS casos "
        f"FROM analysis_record WHERE {JANELA} GROUP BY 1 ORDER BY 1 DESC",
    ),
    "risco_final": (
        "Categoria final de risco: a última avaliação de cada caso. Sem avaliação não é LOW.",
        "SELECT coalesce(risk_assessments->-1->>'category', 'SEM_AVALIACAO') AS risco, count(*) AS casos "
        f"FROM analysis_record WHERE {JANELA} GROUP BY 1 ORDER BY 2 DESC",
    ),
    "desfechos": (
        "Desfecho e se houve revisão humana. AUTO_FINALIZED só ocorre em LOW.",
        f"SELECT outcome, reviewed, count(*) AS casos FROM analysis_record WHERE {JANELA} "
        "GROUP BY 1, 2 ORDER BY 3 DESC",
    ),
    "devolucoes": (
        "Casos devolvidos pelo revisor (RETURN) e quantas versões de recomendação foram necessárias.",
        "SELECT count(*) FILTER (WHERE review_actions @> '[{\"decision\": \"RETURN\"}]') AS com_devolucao, "
        "count(*) AS revisados, max(final_recommendation_version) AS max_versoes "
        f"FROM analysis_record WHERE reviewed AND {JANELA}",
    ),
    "espera_humana_s": (
        "Segundos entre o pedido e a última decisão humana, só nos casos revisados E concluídos. "
        "Quem ainda espera não está aqui; é o lado que 'iniciados_vs_concluidos' mostra.",
        "SELECT count(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY espera) AS p50_s, "
        "percentile_cont(0.95) WITHIN GROUP (ORDER BY espera) AS p95_s, max(espera) AS max_s "
        f"FROM (SELECT extract(epoch FROM {DECIDIDO_EM} - {PEDIDO_EM}) AS espera "
        f"      FROM analysis_record WHERE reviewed AND {JANELA}) AS esperas",
    ),
    "tempo_ate_concluir_s": (
        "Segundos do pedido à finalização. Sem revisão é tempo de máquina; com revisão inclui a espera "
        "humana. Por isso os dois grupos não se somam nem se comparam.",
        f"SELECT reviewed, count(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY total) AS p50_s, "
        "percentile_cont(0.95) WITHIN GROUP (ORDER BY total) AS p95_s "
        f"FROM (SELECT reviewed, extract(epoch FROM finalized_at - {PEDIDO_EM}) AS total "
        f"      FROM analysis_record WHERE {JANELA}) AS totais GROUP BY reviewed ORDER BY reviewed",
    ),
    "iniciados_vs_concluidos": (
        "Threads com checkpoint (casos iniciados, de qualquer data) contra registros finalizados. "
        "A diferença são casos parados na revisão, abandonados ou que falharam antes do fim.",
        "SELECT (SELECT count(DISTINCT thread_id) FROM checkpoints) AS iniciados, "
        "(SELECT count(*) FROM analysis_record) AS concluidos",
    ),
}


def executar(database_url: str, dias: int) -> dict:
    """Roda as consultas numa transação somente leitura; nunca escreve no banco do produto."""
    import psycopg
    from psycopg.rows import dict_row

    resultado: dict = {}
    with psycopg.connect(database_url, connect_timeout=10, row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            for nome, (_, sql) in CONSULTAS.items():
                cur.execute(sql, {"dias": dias})
                resultado[nome] = [dict(row) for row in cur.fetchall()]
    return resultado


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", action="store_true", help="Executa contra DATABASE_URL do .env (somente leitura).")
    p.add_argument("--dias", type=int, default=30)
    args = p.parse_args()
    if args.dias < 1:
        raise SystemExit("--dias precisa ser pelo menos 1.")
    if not args.db:
        for nome, (pergunta, sql) in CONSULTAS.items():
            # Impresso pronto para colar no editor SQL do Neon ou no psql.
            print(f"-- {nome}: {pergunta}\n{sql.replace('%(dias)s', str(args.dias))};\n")
        print("Nada foi consultado. Com --db, as consultas rodam em DATABASE_URL, "
              "em transação somente leitura.")
        return
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    url = os.getenv("DATABASE_URL", "")
    if not url or "<" in url:
        raise SystemExit("Defina DATABASE_URL no .env (para produção, a string do Neon com sslmode=require).")
    resultado = {"consultado_em": datetime.now(UTC).isoformat(), "dias": args.dias,
                 "banco": url.split("@")[-1].split("?")[0] if "@" in url else "(sem host)",
                 "resultados": executar(url, args.dias)}
    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    write_json("18-uso.json", resultado)


if __name__ == "__main__":
    main()
