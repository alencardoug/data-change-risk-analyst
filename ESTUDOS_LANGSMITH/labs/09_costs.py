"""Contabilidade didática; preços FICTÍCIOS, sem chamada de modelo."""

from dataclasses import dataclass
from decimal import Decimal

from _common import parser, session, traced_call, write_json


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
    print(result)
    with session(args, lab="09-custo-sintetico") as client:
        if client:
            from langsmith import traceable

            fn = traceable(synthetic_generation, run_type="llm", name="modelo-de-papel",
                           metadata={"ls_provider": "curso-ficticio", "ls_model_name": "modelo-de-papel"})

            def outer(inputs):
                return fn(inputs)

            traced_call(client, args.project, "custo-ficticio", outer, {"question": "Quanto custaria?"},
                        metadata={"synthetic_cost": True})
    write_json("09-custos.json", result)


if __name__ == "__main__":
    main()
