from sqlalchemy.sql import expression
from sqlalchemy.sql.coercions import expect
from src.fraud_rules.models import FraudRule
from src.transactions.schemes import RuleResult, TransactionScheme
from src.fraud_rules.service import normalize_rule, validate_rule
from src.users.models import User


def check_transaction(
    user: User, transaction: dict, rule: FraudRule
) -> RuleResult:
    valid, _, ast = validate_rule(rule.dsl_expression)
    print("exp", normalize_rule(rule.dsl_expression))
    print("ast", ast)
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
