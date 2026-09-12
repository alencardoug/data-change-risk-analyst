"""Contabilidade didática; preços FICTÍCIOS, sem chamada de modelo."""

from dataclasses import dataclass
from decimal import Decimal

from _common import parser, session, show_trace, write_json


def token_cost(input_tokens: int, output_tokens: int, cache_read: int = 0) -> Decimal:
    if min(input_tokens, output_tokens, cache_read) < 0 or cache_read > input_tokens:
        raise ValueError("Contagens inválidas; cache_read é subconjunto do input.")
    # Unidades: USD por um milhão de tokens. Tabela inventada para fazer a conta à mão.
    return (Decimal(input_tokens - cache_read) * 2 + Decimal(cache_read) * Decimal("0.5")
            + Decimal(output_tokens) * 8) / 1_000_000


@dataclass
class Budget:
    limit: Decimal
    reserved: Decimal = Decimal(0)

    def reserve(self, upper_bound: Decimal) -> bool:
        if upper_bound < 0:
            raise ValueError("Reserva precisa ser não negativa.")
        if self.reserved + upper_bound > self.limit:
            return False
        self.reserved += upper_bound
        return True


@dataclass
class TarifaPlataforma:
    """Tarifa FICTÍCIA com a estrutura da fatura documentada: um medidor de ingestão e outro de upgrades."""
    franquia_traces: int = 5_000  # traces ingeridos incluídos no mês
    preco_trace_ingerido: Decimal = Decimal("0.0025")  # cobrado de todo trace ingerido, de qualquer faixa
    preco_upgrade: Decimal = Decimal("0.005")  # promoção à retenção estendida: evento à parte, quando ocorre
    assentos: int = 1
    preco_assento: Decimal = Decimal("39")


def estimativa_mensal(*, traces_ingeridos: int, upgrades_no_mes: int, tarifa: TarifaPlataforma,
                      modelo_aplicacao: Decimal, juiz: Decimal, armazenamento_externo: Decimal) -> dict:
    """Dois medidores separados: ingestão do mês e upgrades do mês, que podem ser de traces de outro mês."""
    if traces_ingeridos < 0 or upgrades_no_mes < 0:
        raise ValueError("Contagens não negativas.")
    ingeridos_cobraveis = max(0, traces_ingeridos - tarifa.franquia_traces)
    plataforma = {
        "ingestao": ingeridos_cobraveis * tarifa.preco_trace_ingerido,
        "upgrades": upgrades_no_mes * tarifa.preco_upgrade,
        "assentos": tarifa.assentos * tarifa.preco_assento,
    }
    parcelas = {**plataforma, "modelo_aplicacao": modelo_aplicacao, "juiz": juiz,
                "armazenamento_externo": armazenamento_externo}
    # Erro A: supor que o trace promovido sai do medidor de ingestão (subestima).
    promovidos_do_mes = min(upgrades_no_mes, traces_ingeridos)
    ingeridos_sem_promovidos = max(0, traces_ingeridos - promovidos_do_mes - tarifa.franquia_traces)
    erro_a = (ingeridos_sem_promovidos * tarifa.preco_trace_ingerido
              + plataforma["upgrades"] + plataforma["assentos"])
    # Erro B: cobrar a ingestão de novo no mês do upgrade (superestima).
    erro_b = (plataforma["ingestao"] + upgrades_no_mes * (tarifa.preco_trace_ingerido + tarifa.preco_upgrade)
              + plataforma["assentos"])
    return {
        "precos": "FICTICIOS", "traces_ingeridos": traces_ingeridos,
        "ingeridos_cobraveis": ingeridos_cobraveis, "upgrades_no_mes": upgrades_no_mes,
        "parcelas_usd": {k: str(v) for k, v in parcelas.items()},
        "plataforma_usd": str(sum(plataforma.values(), Decimal(0))),
        "erro_a_promovido_sai_da_ingestao_usd": str(erro_a),
        "erro_b_ingestao_cobrada_de_novo_usd": str(erro_b),
        "total_usd": str(sum(parcelas.values(), Decimal(0))),
    }


def synthetic_generation(inputs: dict) -> dict:
    from langsmith import get_current_run_tree

    run = get_current_run_tree()
    usage = {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200,
             "input_token_details": {"cache_read": 200},
             "input_cost": 0.0017, "output_cost": 0.0016, "total_cost": 0.0033}
    if run:
        run.set(usage_metadata=usage)
    return {"answer": "Resposta pré-escrita. Tokens e preços SINTÉTICOS.", "usage_metadata": usage}


def main():
    p = parser(__doc__)
    p.set_defaults(project="dcra-estudos-custos-sinteticos")
    args = p.parse_args()
    simple = token_cost(1000, 200, 200)
    leaves = [simple, token_cost(2500, 450, 500), token_cost(3000, 600)]
    total = sum(leaves, Decimal(0))
    double_counted = total + sum(leaves, Decimal(0)) + leaves[-1]  # raiz + folhas + wrapper do agente
    budget = Budget(Decimal("0.010"))
    accepted = [budget.reserve(simple) for _ in range(4)]
    result = {"prices": "FICTICIOS", "single_call_usd": str(simple), "leaves_usd": str(total),
              "wrong_sum_parents_and_children_usd": str(double_counted),
              "reservations_accepted": accepted, "reserved_usd": str(budget.reserved),
              "eval_target_calls": 16 * 2 * 3, "eval_judge_calls_if_one_per_target": 16 * 2 * 3}
    # Mês típico: 20 mil traces ingeridos e 2 mil upgrades (feedback via API/avaliador com retenção ligada).
    result["plataforma_mensal"] = estimativa_mensal(
        traces_ingeridos=20_000, upgrades_no_mes=2_000, tarifa=TarifaPlataforma(),
        modelo_aplicacao=Decimal("12"), juiz=Decimal("3"), armazenamento_externo=Decimal("1"))
    # Mês sem ingestão: só upgrades de traces antigos. A fatura não é zero.
    result["plataforma_mes_sem_ingestao"] = estimativa_mensal(
        traces_ingeridos=0, upgrades_no_mes=500, tarifa=TarifaPlataforma(),
        modelo_aplicacao=Decimal(0), juiz=Decimal(0), armazenamento_externo=Decimal(0))
    print(result)
    with session(args, lab="09-custo-sintetico") as client:
        if client:
            from langsmith import trace, traceable

            fn = traceable(synthetic_generation, run_type="llm", name="modelo-de-papel",
                           metadata={"ls_provider": "curso-ficticio", "ls_model_name": "modelo-de-papel"})
            question = {"question": "Quanto custaria?"}
            with trace("custo-ficticio", inputs=question, metadata={"synthetic_cost": True}) as run:
                run.end(outputs=fn(question))
            show_trace(client, args.project, str(run.id), start_time=run.start_time)
    write_json("09-custos.json", result)


if __name__ == "__main__":
    main()
