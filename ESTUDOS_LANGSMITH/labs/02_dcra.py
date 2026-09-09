"""Grafo real, catálogo fixture, checkpointer em memória; opcionalmente LLM real."""

from uuid import uuid4

from _common import parser, require_real, session, show_trace, write_json

SCENARIOS = {
    "low": "add index on orders(customer_id)",
    "medium": "drop column orders.customer_legacy_id",
    "high": "drop column orders.id",
    "unknown": "drop column orders.legacy_region",
    "gap": "drop column orders.customer_legacy_id",
}


def main():
    p = parser(__doc__)
    p.add_argument("--case", choices=SCENARIOS, default="medium")
    p.add_argument("--review", choices=["none", "approve", "reject", "return", "return-evidence"],
                   default="none")
    p.add_argument("--real", action="store_true", help="Usa LLM real e gera cobrança no provedor.")
    args = p.parse_args()
    with session(args, lab="02-dcra") as client:
        from _dcra import make_deps, review, summarize
        from langsmith import tracing_context

        from dcra.domain.models import ChangeRequest
        from dcra.graph.build import build_graph, pending_interrupt, run

        if args.real:
            require_real(args)
        graph = build_graph(make_deps(["usage"] if args.case == "gap" else [], real=args.real))
        cr = ChangeRequest(raw_text=SCENARIOS[args.case], submitted_by="aluno-sintetico")
        phases = []
        metadata = {"thread_id": cr.id, "scenario": args.case,
                    "model_mode": "real" if args.real else "fixture"}
        with tracing_context(metadata=metadata):
            root_id = str(uuid4())
            configured = graph.with_config(run_name="dcra-iniciar", run_id=root_id, metadata=metadata)
            state = run(configured, cr)
            phases.append(summarize(state, cr.id) | {"run_id": root_id})
            if client:
                show_trace(client, args.project, root_id)
            actions = {"none": [], "approve": ["APPROVE"], "reject": ["REJECT"],
                       "return": ["RETURN", "APPROVE"], "return-evidence": ["RETURN", "APPROVE"]}
            for decision in actions[args.review]:
                if pending_interrupt(state) is None:
                    print("Não há pausa para revisar: confira se o caso é LOW ou ocorreu um erro.")
                    break
                root_id = str(uuid4())
                configured = graph.with_config(run_name=f"dcra-retomar-{decision.lower()}",
                                               run_id=root_id, metadata=metadata)
                state = review(configured, cr.id, decision,
                               evidence_missing=args.review == "return-evidence" and decision == "RETURN")
                phases.append(summarize(state, cr.id) | {"run_id": root_id})
                if client:
                    show_trace(client, args.project, root_id)
        print(f"thread_id: {cr.id}")
        for n, phase in enumerate(phases, 1):
            print(f"Fase {n}: risco={phase['risk']} pausa={phase['awaiting_review']} "
                  f"resultado={phase['outcome']} versões={phase['recommendation_versions']}")
        print("\n".join(phases[-1]["step_log"]))
        write_json(f"02-{args.case}-{args.review}.json", {"mode": metadata["model_mode"], "phases": phases})


if __name__ == "__main__":
    main()
