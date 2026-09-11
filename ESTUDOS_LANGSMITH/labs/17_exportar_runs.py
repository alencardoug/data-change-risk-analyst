"""Exporta runs e feedback de uma janela fechada para JSONL, com manifesto; reexecutar não duplica."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from _common import ARTIFACTS, COURSE, ROOT, digest, manifest, parser, session

JANELA_LOCAL = ("2026-09-09T10:00:00Z", "2026-09-09T10:08:00Z")  # tA e tB dentro; tC (10:09) fora.
LOTE_FEEDBACK = 100


def instante(valor: str | datetime) -> datetime:
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    return valor if valor.tzinfo else valor.replace(tzinfo=UTC)


def iso_z(momento: datetime) -> str:
    """Formato que a linguagem de consulta documenta: ISO 8601 com sufixo Z."""
    return momento.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def na_janela(run: dict, desde: datetime, ate: datetime) -> bool:
    """Intervalo fechado à esquerda e aberto à direita: duas janelas contíguas não compartilham run."""
    return desde <= instante(run["start_time"]) < ate


def filtro_janela(desde: datetime, ate: datetime) -> str:
    """Os dois limites vão ao servidor; a checagem local continua como verificação."""
    return f'and(gte(start_time, "{iso_z(desde)}"), lt(start_time, "{iso_z(ate)}"))'


def normalizar_local(row: dict) -> dict:
    """dados/runs.jsonl usa nomes curtos; a exportação usa os nomes do SDK."""
    return {"id": row["id"], "trace_id": row["trace"], "parent_run_id": row["parent"],
            "name": row["name"], "run_type": row["run_type"], "start_time": row["start"],
            "end_time": row["end"], "error": row["error"],
            "status": "error" if row["error"] else "success", "tags": [],
            "inputs": None, "outputs": None}


def normalizar_remoto(run) -> dict:
    return {"id": str(run.id), "trace_id": str(run.trace_id),
            "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
            "name": run.name, "run_type": run.run_type,
            "start_time": instante(run.start_time).isoformat(),
            "end_time": instante(run.end_time).isoformat() if run.end_time else None,
            "error": run.error, "status": run.status, "tags": list(run.tags or []),
            "total_tokens": run.total_tokens,
            "total_cost": str(run.total_cost) if run.total_cost is not None else None,
            "inputs": run.inputs, "outputs": run.outputs}


def normalizar_feedback(fb) -> dict:
    fonte = getattr(fb, "feedback_source", None)
    return {"id": str(fb.id), "run_id": str(fb.run_id), "key": fb.key, "score": fb.score,
            "value": fb.value, "comment": fb.comment,
            "created_at": instante(fb.created_at).isoformat() if fb.created_at else None,
            "source": getattr(fonte, "type", None)}


def classe_do_erro(erro: str | None) -> str | None:
    """'TimeoutError: catalogo nao respondeu' → 'TimeoutError'. A mensagem pode conter entrada do usuário."""
    if not erro:
        return None
    return re.split(r"[:(\n]", erro.strip(), maxsplit=1)[0].strip() or "erro"


def minimizar_run(run: dict) -> dict:
    return {**run, "inputs": None, "outputs": None, "error": classe_do_erro(run.get("error"))}


def minimizar_feedback(fb: dict) -> dict:
    return {**fb, "comment": None, "value": None}


def ler_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def acrescentar(path: Path, linhas: Iterable[dict]) -> dict:
    """Grava apenas ids ausentes do arquivo; uma reexecução ou retomada não duplica."""
    existentes = {linha["id"] for linha in ler_jsonl(path)}
    vistos: set[str] = set()
    novos = repetidos = 0
    with path.open("a") as fh:
        for linha in linhas:
            if linha["id"] in existentes or linha["id"] in vistos:
                repetidos += 1
                continue
            vistos.add(linha["id"])
            fh.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")
            novos += 1
    return {"novos": novos, "ja_presentes": repetidos}


def identidade(*, origem: str, desde: datetime, ate: datetime, conteudo: bool, feedback: bool) -> dict:
    """O que torna duas exportações comparáveis. Mudou qualquer campo, é outra exportação."""
    return {"origem": origem, "desde": desde.isoformat(), "ate": ate.isoformat(),
            "conteudo": conteudo, "feedback": feedback}


def slug(ident: dict) -> str:
    origem = re.sub(r"[^a-z0-9]+", "-", ident["origem"].lower()).strip("-")
    janela = f"{iso_z(instante(ident['desde']))}_{iso_z(instante(ident['ate']))}".replace(":", "")
    sufixo = ("-conteudo" if ident["conteudo"] else "") + ("" if ident["feedback"] else "-sem-feedback")
    return f"{origem}-{janela}{sufixo}"


def conferir_destino(destino: Path, ident: dict) -> dict | None:
    """Recusa misturar exportações diferentes no mesmo diretório; devolve o manifesto anterior compatível."""
    manifesto = destino / "manifesto.json"
    if manifesto.exists():
        anterior = json.loads(manifesto.read_text())
        if anterior.get("identidade") != ident:
            raise SystemExit(
                f"{destino} já contém uma exportação com outra identidade:\n"
                f"  existente: {anterior.get('identidade')}\n  pedida:    {ident}\n"
                "Use outro --destino; misturar origens, janelas ou opções deixaria o manifesto falso.")
        return anterior
    if any(destino.glob("*.jsonl")):
        raise SystemExit(f"{destino} tem arquivos JSONL sem manifesto; escolha um diretório vazio.")
    return None


def exportar(runs: Iterable[dict], *, desde: datetime, ate: datetime, destino: Path, maximo: int,
             conteudo: bool = False,
             feedback: Callable[[list[str]], Iterable[dict]] | None = None) -> dict:
    """Filtra pela janela, aplica o teto e só então grava. Acima do teto, não grava nada."""
    if maximo < 1:
        raise ValueError("--max precisa ser pelo menos 1.")
    selecionados, fora = [], 0
    for run in runs:
        if na_janela(run, desde, ate):
            selecionados.append(run)
        else:
            fora += 1
    if len(selecionados) > maximo:
        return {"truncado": True, "maximo": maximo, "runs": {"na_janela_ate_o_teto": maximo + 1,
                                                              "fora_da_janela": fora}}
    if not conteudo:
        selecionados = [minimizar_run(run) for run in selecionados]
    destino.mkdir(parents=True, exist_ok=True)
    resultado = {"truncado": False, "maximo": maximo,
                 "runs": {**acrescentar(destino / "runs.jsonl", selecionados), "fora_da_janela": fora}}
    if feedback is not None:
        linhas = feedback([run["id"] for run in selecionados])
        if not conteudo:
            linhas = [minimizar_feedback(fb) for fb in linhas]
        resultado["feedback"] = acrescentar(destino / "feedback.jsonl", linhas)
    return resultado


def reconciliar(destino: Path) -> dict:
    """Lê o que foi gravado e confere o que um consumidor vai precisar saber."""
    runs = ler_jsonl(destino / "runs.jsonl")
    feedback = ler_jsonl(destino / "feedback.jsonl")
    ids = [run["id"] for run in runs]
    inicios = sorted(instante(run["start_time"]) for run in runs)
    return {
        "runs": len(runs), "ids_unicos": len(set(ids)) == len(ids),
        "traces": len({run["trace_id"] for run in runs}),
        "raizes": sum(run["parent_run_id"] is None for run in runs),
        "com_erro": sum(bool(run["error"]) for run in runs),
        "filhos_sem_pai_no_arquivo": sum(
            run["parent_run_id"] is not None and run["parent_run_id"] not in set(ids) for run in runs),
        "feedback": len(feedback),
        "feedback_sem_run_no_arquivo": sum(fb["run_id"] not in set(ids) for fb in feedback),
        "primeiro_start_time": inicios[0].isoformat() if inicios else None,
        "ultimo_start_time": inicios[-1].isoformat() if inicios else None,
        "sha256": {p.name: digest(p) for p in sorted(destino.glob("*.jsonl"))},
    }


def feedback_local(ids: list[str]) -> list[dict]:
    alvo = set(ids)
    return [fb for fb in ler_jsonl(COURSE / "dados" / "feedback.jsonl") if fb["run_id"] in alvo]


def consultar_remoto(client, projeto: str, desde: datetime, ate: datetime, maximo: int) -> Iterable[dict]:
    """Pede maximo+1 para detectar excesso. list_runs está deprecado no SDK 0.11.1: ver capítulo 22."""
    for run in client.list_runs(project_name=projeto, filter=filtro_janela(desde, ate), limit=maximo + 1):
        yield normalizar_remoto(run)


def feedback_remoto(client) -> Callable[[list[str]], list[dict]]:
    def buscar(ids: list[str]) -> list[dict]:
        linhas = []
        for i in range(0, len(ids), LOTE_FEEDBACK):
            lote = client.list_feedback(run_ids=ids[i:i + LOTE_FEEDBACK])
            linhas += [normalizar_feedback(fb) for fb in lote]
        return linhas
    return buscar


def main():
    p = parser(__doc__)
    p.add_argument("--desde", help="Início da janela (ISO 8601, inclusivo).")
    p.add_argument("--ate", help="Fim da janela (ISO 8601, exclusivo).")
    p.add_argument("--dias", type=int, default=1, help="Com --send e sem --desde/--ate: janela até agora.")
    p.add_argument("--destino", help="Padrão: artefatos/17-export/<origem>-<janela>[-conteudo].")
    p.add_argument("--conteudo", action="store_true",
                   help="Inclui inputs/outputs, mensagens de erro completas e comment/value do feedback. "
                        "Sem esta opção saem só metadados e a classe do erro.")
    p.add_argument("--sem-feedback", action="store_true")
    p.add_argument("--max", type=int, default=5000, help="Teto de runs na janela; acima dele nada é gravado.")
    args = p.parse_args()
    if args.max < 1:
        raise SystemExit("--max precisa ser pelo menos 1.")
    with session(args, lab="17-exportar") as client:
        if client:
            ate = instante(args.ate) if args.ate else datetime.now(UTC).replace(second=0, microsecond=0)
            desde = instante(args.desde) if args.desde else ate - timedelta(days=args.dias)
            origem = f"langsmith-{args.project}"
        else:
            desde = instante(args.desde or JANELA_LOCAL[0])
            ate = instante(args.ate or JANELA_LOCAL[1])
            origem = "local-sintetico"
        if desde >= ate:
            raise SystemExit("A janela precisa ter --desde anterior a --ate.")
        ident = identidade(origem=origem, desde=desde, ate=ate, conteudo=args.conteudo,
                           feedback=not args.sem_feedback)
        destino = Path(args.destino) if args.destino else ARTIFACTS / "17-export" / slug(ident)
        anterior = conferir_destino(destino, ident)
        if client:
            fonte = consultar_remoto(client, args.project, desde, ate, args.max)
            feedback = None if args.sem_feedback else feedback_remoto(client)
        else:
            fonte = (normalizar_local(row) for row in ler_jsonl(COURSE / "dados" / "runs.jsonl"))
            feedback = None if args.sem_feedback else feedback_local
        execucao = {"gerado_em": datetime.now(UTC).isoformat(),
                    **exportar(fonte, desde=desde, ate=ate, destino=destino, maximo=args.max,
                               conteudo=args.conteudo, feedback=feedback)}
    if execucao["truncado"]:
        raise SystemExit(f"Mais de {args.max} runs na janela; nada foi gravado. Reduza a janela ou "
                         "aumente --max. Um arquivo parcial nunca é apresentado como completo.")
    reconciliacao = reconciliar(destino)
    if not reconciliacao["ids_unicos"]:
        raise SystemExit("Há ids duplicados no arquivo exportado; investigue antes de usar.")
    manifesto = {
        "identidade": ident,
        "janela": {"desde": desde.isoformat(), "ate": ate.isoformat(), "fechada_a_direita": True,
                   "filtro_no_servidor": filtro_janela(desde, ate) if client else None},
        "conteudo_incluido": args.conteudo,
        "texto_livre_incluido": args.conteudo,
        "feedback_incluido": not args.sem_feedback,
        "execucoes": [*(anterior or {}).get("execucoes", []), execucao],
        "reconciliacao": reconciliacao, "manifest": manifest(),
    }
    (destino / "manifesto.json").write_text(
        json.dumps(manifesto, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({"identidade": ident, "execucao": execucao, "reconciliacao": reconciliacao},
                     indent=2, ensure_ascii=False))
    print(f"Arquivos: {destino.relative_to(ROOT) if destino.is_relative_to(ROOT) else destino}/"
          "{runs.jsonl, feedback.jsonl, manifesto.json}")
    print("Isto é uma exportação pequena por SDK, não o bulk export nativo (Parquet para bucket S3).")


if __name__ == "__main__":
    main()
