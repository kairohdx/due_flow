from dataclasses import dataclass

from policyflow import FirstMatch, PolicyEngine, RuleResult, rule


@dataclass(frozen=True)
class ChargeContext:
    status: str
    days_until_due: int


@rule(id="skip-paid")
def skip_paid(context: ChargeContext):
    if context.status != "paid":
        return RuleResult.pass_(reason="charge_is_not_paid")
    return RuleResult.consume({"action": "skip"}, reason="charge_is_paid")


@rule(id="due-today")
def due_today(context: ChargeContext):
    if context.days_until_due != 0:
        return RuleResult.pass_(reason="charge_is_not_due_today")
    return RuleResult.consume(
        {"action": "send", "template": "due_today"},
        reason="charge_is_due_today",
    )


def build_engine() -> PolicyEngine[ChargeContext, dict]:
    engine = PolicyEngine[ChargeContext, dict](name="dueflow.contract")
    engine.add_scope(
        "charge.notification",
        rules=[skip_paid, due_today],
        strategy=FirstMatch(),
    )
    return engine


def evaluated_rules(execution) -> list[str]:
    return [
        event.attributes["rule_id"]
        for event in execution.trace.events
        if event.name == "rule.evaluated"
    ]


def test_first_match_continues_after_pass() -> None:
    execution = build_engine().run(
        ChargeContext(status="pending", days_until_due=0),
        scopes=["charge.notification"],
    )

    assert execution.decision is not None
    assert execution.decision.rule_id == "due-today"
    assert execution.decision.effect == {
        "action": "send",
        "template": "due_today",
    }
    assert evaluated_rules(execution) == ["skip-paid", "due-today"]


def test_first_match_stops_after_first_terminal_result() -> None:
    execution = build_engine().run(
        ChargeContext(status="paid", days_until_due=0),
        scopes=["charge.notification"],
    )

    assert execution.decision is not None
    assert execution.decision.rule_id == "skip-paid"
    assert execution.decision.reason == "charge_is_paid"
    assert evaluated_rules(execution) == ["skip-paid"]

