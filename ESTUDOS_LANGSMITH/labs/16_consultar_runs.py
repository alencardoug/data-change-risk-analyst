"""De traces a métricas: denominadores, percentis e tempo próprio, com as consultas equivalentes."""

import json
from datetime import UTC, datetime, timedelta
from math import ceil

from _common import COURSE, parser, session, write_json

# Consultas do SDK instalado; a sintaxe do filtro vem da docstring de Client.list_runs.
CONSULTAS = {
    "raízes do projeto": 'list_runs(project_name=..., is_root=True)',
    "somente falhas": 'list_runs(project_name=..., error=True)',
    "uma operação": 'list_runs(project_name=..., filter=\'eq(name, "collect_deps")\')',
    "chamadas de ferramenta": 'list_runs(project_name=..., filter=\'eq(run_type, "tool")\')',
    "lentas e do tipo chain": 'list_runs(..., filter=\'and(eq(run_type, "chain"), gt(latency, 10))\')',
}


def ms(row: dict) -> float:
    fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
    inicio = datetime.strptime(row["start"].replace("Z", "+0000"), fmt)
    fim = datetime.strptime(row["end"].replace("Z", "+0000"), fmt)
    return (fim - inicio).total_seconds() * 1000


def percentil(valores: list[float], p: int) -> float | None:
    """Nearest-rank. Devolve None sem observações; n pequeno não vira precisão teatral."""
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[min(ceil(p / 100 * len(ordenados)), len(ordenados)) - 1]


def uniao_ms(intervalos: list[tuple[float, float]]) -> float:
    """Filhos concorrentes ocupam o mesmo intervalo uma vez só."""
    total, fim_atual = 0.0, None
    for inicio, fim in sorted(intervalos):
        if fim_atual is None or inicio > fim_atual:
            total += fim - inicio
            fim_atual = fim
        elif fim > fim_atual:
            total += fim - fim_atual
            fim_atual = fim
    return total


def analisar(runs: list[dict], operacao: str = "collect_deps") -> dict:
    raizes = [r for r in runs if r["parent"] is None]
    tentativas = [r for r in runs if r["name"] == operacao]
    por_trace = {r["trace"] for r in tentativas if r["error"]}
    resolvidas = {r["trace"] for r in tentativas if not r["error"]}
    duracoes = {}
    for r in runs:
        duracoes.setdefault(r["name"], []).append(ms(r))
    tempos = []
    for raiz in raizes:
        filhos = [r for r in runs if r["parent"] == raiz["id"]]
        base = datetime.strptime(raiz["start"].replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S.%f%z")
        janelas = [
            ((datetime.strptime(f["start"].replace("Z", "+0000"),
                                "%Y-%m-%dT%H:%M:%S.%f%z") - base).total_seconds() * 1000,
             (datetime.strptime(f["end"].replace("Z", "+0000"),
                                "%Y-%m-%dT%H:%M:%S.%f%z") - base).total_seconds() * 1000)
            for f in filhos
        ]
        tempos.append({
            "trace": raiz["trace"], "raiz_ms": round(ms(raiz), 1),
            "soma_ingenua_dos_filhos_ms": round(sum(ms(f) for f in filhos), 1),
            "ocupacao_real_dos_filhos_ms": round(uniao_ms(janelas), 1),
            "tempo_proprio_ms": round(ms(raiz) - uniao_ms(janelas), 1),
        })
    return {
        "denominadores": {
            "runs": len(runs), "runs_com_erro": sum(1 for r in runs if r["error"]),
            "raizes": len(raizes), "raizes_com_erro": sum(1 for r in raizes if r["error"]),
            "erro_por_pedido": round(sum(1 for r in raizes if r["error"]) / len(raizes), 4),
            "erro_por_run": round(sum(1 for r in runs if r["error"]) / len(runs), 4),
            f"tentativas_de_{operacao}": len(tentativas),
            f"erro_por_tentativa_de_{operacao}": round(
                sum(1 for r in tentativas if r["error"]) / len(tentativas), 4),
            f"pedidos_em_que_{operacao}_nunca_obteve_resposta": len(por_trace - resolvidas),
        },
        "latencia": {
            nome: {"n": len(v), "p50_ms": percentil(v, 50), "p95_ms": percentil(v, 95),
                   "metodo": "nearest-rank"}
            for nome, v in sorted(duracoes.items())
        },
        "tempo_proprio": tempos,
    }


def coletar_remoto(client, projeto: str, dias: int) -> list[dict]:
    """list_runs está DEPRECADO no SDK instalado (ver capítulo 22); migração: Client.runs.query."""
    inicio = datetime.now(UTC) - timedelta(days=dias)
    linhas = []
    for run in client.list_runs(project_name=projeto, start_time=inicio, limit=500):
        if run.end_time is None:
            continue
        linhas.append({
            "trace": str(run.trace_id), "id": str(run.id),
            "parent": str(run.parent_run_id) if run.parent_run_id else None,
            "name": run.name, "run_type": run.run_type,
            "start": run.start_time.isoformat(), "end": run.end_time.isoformat(),
            "error": run.error,
        })
    return linhas


def main():
    p = parser(__doc__)
    p.add_argument("--dias", type=int, default=1, help="Janela consultada no modo --send.")
    p.add_argument("--operacao", default="collect_deps")
    args = p.parse_args()
    with session(args, lab="16-consultar") as client:
        if client:
            runs = coletar_remoto(client, args.project, args.dias)
            if not runs:
                raise SystemExit(f"Nenhum run concluído em '{args.project}' nos últimos "
                                 f"{args.dias} dia(s). Rode os labs com --send antes.")
            origem = f"{args.project}, últimos {args.dias} dia(s)"
        else:
            path = COURSE / "dados" / "runs.jsonl"
            runs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            origem = "dados/runs.jsonl (árvore sintética)"
        # As datas remotas trazem offset explícito; normalizamos para o mesmo formato local.
        for r in runs:
            for campo in ("start", "end"):
                r[campo] = r[campo].replace("+00:00", "Z")
                if "." not in r[campo]:
                    r[campo] = r[campo].replace("Z", ".000Z")
        resultado = {"origem": origem, **analisar(runs, args.operacao)}
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        print("\nConsultas equivalentes na UI e no SDK:")
        for pergunta, consulta in CONSULTAS.items():
            print(f"  {pergunta:26} {consulta}")
        write_json("16-consultas.json", resultado)


if __name__ == "__main__":
    main()
