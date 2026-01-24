from sqlalchemy.sql import expression
from src.fraud_rules.models import FraudRule
from src.transaction_result.schemes import RuleResult 
from src.fraud_rules.service import normalize_rule, validate_rule


def check_transaction(transaction: dict, rule: FraudRule
) -> RuleResult:
    try:
        valid, _, ast = validate_rule(rule.dsl_expression)
    except Exception as e:
        return RuleResult(
            ruleId=rule.id,
            ruleName=rule.name,
            priority=rule.priority,
            matched=False,
            description="not valid dsl",
        )
    if not valid:
        return RuleResult(
            ruleId=rule.id,
            ruleName=rule.name,
            priority=rule.priority,
            matched=False,
            description="not valid dsl",
        )
    if ast is None:
        return RuleResult(
            ruleId=rule.id,
            ruleName=rule.name,
            priority=rule.priority,
            matched=False,
            description="not valid dsl",
        )

    try: 
        result = ast.eval(transaction)
    except Exception as e:
        return RuleResult(
            ruleId=rule.id,
            ruleName=rule.name,
            priority=rule.priority,
            matched=False,
            description=f"cannot eval this rule due to this: {e}",
        )
    

    desc = f"{rule.dsl_expression} cannot be passed"
    if not result:
        desc = f"{rule.dsl_expression} passed" 
    return RuleResult(
        ruleId=rule.id,
        ruleName=rule.name,
        priority=rule.priority,
        matched=result,
        description=desc,
    )
