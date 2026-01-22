from os import stat
from typing import Optional, Tuple
from lark import Lark, Transformer, UnexpectedInput, Token
from src.exceptions import DslError, ErrorCode


# =====================================================
#                    GRAMMAR
# =====================================================

grammar = r"""
?expression: term
           | expression OR term      -> or_op

?term: factor
     | term AND factor               -> and_op

?factor: NOT factor                  -> not_op
       | comparison
       | "(" expression ")"

comparison: FIELD OP value

FIELD: "amount"
     | "currency"
     | "merchantId"
     | "ipAddress"
     | "deviceId"
     | "user.age"
     | "user.region"

AND: /(?i:and)/
OR:  /(?i:or)/
NOT: /(?i:not)/

OP: ">" | ">=" | "<" | "<=" | "=" | "!="

value: NUMBER -> number
     | STRING -> string

STRING: "'" /[^']*/ "'"

%import common.NUMBER
%import common.WS
%ignore WS
"""

parser = Lark(grammar, start="expression", parser="lalr", propagate_positions=True)


# =====================================================
#                    AST CLASSES
# =====================================================


class Node:
    def eval(self, ctx):
        raise NotImplementedError


class Or(Node):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def eval(self, ctx):
        return self.a.eval(ctx) or self.b.eval(ctx)


class And(Node):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def eval(self, ctx):
        print(self.b)
        return self.a.eval(ctx) and self.b.eval(ctx)


class Not(Node):
    def __init__(self, a):
        self.a = a

    def eval(self, ctx):
        return not self.a.eval(ctx)


class Comparison(Node):
    def __init__(self, field, op, value, pos):
        self.field = field
        self.op = op
        self.value = value
        self.pos = pos  # (line, col)

    def eval(self, ctx):
        parts = self.field.split(".")
        cur = ctx
        for p in parts:
            cur = cur[p]

        left = cur
        right = self.value

        match self.op:
            case "=":
                return left == right
            case "!=":
                return left != right
            case ">":
                return left > right
            case ">=":
                return left >= right
            case "<":
                return left < right
            case "<=":
                return left <= right

        raise ValueError(f"Unknown op: {self.op}")


# =====================================================
#                    AST BUILDER
# =====================================================



class ASTBuilder(Transformer):
    def or_op(self, args):
        return Or(args[0], args[2])

    def and_op(self, args):
        print(args)
        return And(args[0], args[2])

    def not_op(self, args):
        return Not(args[0])

    def comparison(self, args):
        field_tok, op_tok, val = args
        pos = (field_tok.line, field_tok.column)
        return Comparison(field_tok.value, op_tok.value, val, pos)

    def number(self, tok):
        s = tok[0]
        return float(s) if "." in s else int(s)

    def string(self, tok):
        return tok[0][1:-1]

    def expression(self, items):
        return items[0]

    def term(self, items):
        return items[0]

    def factor(self, items):
        return items[0]


# =====================================================
#                    SEMANTIC VALIDATION
# =====================================================

FIELD_TYPES = {
    "amount": "number",
    "currency": "string",
    "merchantId": "string",
    "ipAddress": "string",
    "deviceId": "string",
    "user.age": "number",
    "user.region": "string",
}

NUMERIC_OPS = {">", ">=", "<", "<="}
EQUALITY_OPS = {"=", "!="}


def validate_ast(node, rule_text, errors):
    """Рекурсивная проверка семантики; при ошибке -> DslError"""

    if isinstance(node, (Or, And)):
        validate_ast(node.a, rule_text, errors)
        validate_ast(node.b, rule_text, errors)
        return

    if isinstance(node, Not):
        validate_ast(node.a, rule_text, errors)
        return

    if isinstance(node, Comparison):
        line, col = node.pos
        pos_str = f"{line}:{col}"

        # Неизвестное поле
        if node.field not in FIELD_TYPES:
            errors.append(
                DslError(
                    status_code=422,
                    err_code=ErrorCode.dsl_invalid_field,
                    message=f"Неизвестное поле '{node.field}'",
                    position=pos_str,
                    near=get_context(rule_text, line, col),
                )
            )

        expected = FIELD_TYPES[node.field]

        # Неверный оператор
        if node.op not in NUMERIC_OPS | EQUALITY_OPS:
            errors.append(
                DslError(
                    status_code=400,
                    err_code=ErrorCode.dsl_invalid_operator,
                    message=f"Недопустимый оператор '{node.op}'",
                    position=pos_str,
                    near=get_context(rule_text, line, col),
                )
            )

        # Типы
        if expected == "number" and isinstance(node.value, str):
            errors.append(
                DslError(
                    status_code=422,
                    err_code=ErrorCode.dsl_invalid_field,
                    message=f"Поле '{node.field}' числовое, но сравнивается со строкой '{node.value}'",
                    position=pos_str,
                    near=get_context(rule_text, line, col),
                )
            )

        if expected == "string" and node.op in NUMERIC_OPS:
            errors.append(
                DslError(
                    status_code=422,
                    err_code=ErrorCode.dsl_invalid_field,
                    message=f"Строковое поле '{node.field}' нельзя сравнивать оператором '{node.op}'",
                    position=pos_str,
                    near=get_context(rule_text, line, col),
                )
            )

        return


# =====================================================
#               EXTRACT CONTEXT FOR ERROR
# =====================================================


def get_context(text, line, col):
    lines = text.split("\n")
    if 1 <= line <= len(lines):
        l = lines[line - 1]
        pointer = " " * col + "^"
        return l + "\n" + pointer
    return None


# =====================================================
#                    VALIDATE RULE
# =====================================================


def validate_rule(rule: str) -> Tuple[bool, list, Optional[Node]]:
    """
    Если правило плохое — бросает DslError.
    Если хорошее — возвращает AST.
    """

    # --- СИНТАКСИС -----------------------------------
    errors = []
    try:
        tree = parser.parse(rule)
    except UnexpectedInput as e:
        errors.append(
            DslError(
                status_code=422,
                err_code=ErrorCode.dsl_parse_error,
                message="Синтаксическая ошибка",
                position=f"{e.line}:{e.column}",
                near=e.get_context(rule),
            )
        )
        return False, errors, None

    # --- AST -----------------------------------------
    ast = ASTBuilder().transform(tree)

    # --- СЕМАНТИКА -----------------------------------
    validate_ast(ast, rule, errors)
    if errors:
        return False, errors, None

    return True, errors, ast  # валидно


class NormalizeTransformer(Transformer):
    def FIELD(self, token: Token):
        return token.value

    def OP(self, token: Token):
        return token.value

    def number(self, items):
        return items[0].value

    def string(self, items):
        return f"'{items[0].value[1:-1]}'"

    def comparison(self, items):
        field, op, value = items
        return f"{field} {op} {value}"

    # AND aggregator
    def and_op(self, items):
        parts = []
        for item in items:
            if isinstance(item, str):
                # skip operator tokens accidentally passed
                if item.upper() == "AND":
                    continue
            parts.append(item)
        # join them
        return " AND ".join(parts)

    # OR aggregator
    def or_op(self, items):
        parts = []
        for item in items:
            if isinstance(item, str):
                if item.upper() == "OR":
                    continue
            parts.append(item)
        return " OR ".join(parts)

    def not_op(self, items):
        expr = items[0]
        return f"NOT {expr}"

    # Needed to unwrap parentheses properly
    def factor(self, items):
        return items[0]

    def term(self, items):
        return items[0]

    def expression(self, items):
        return items[0]


def normalize_rule(rule: str) -> str:
    tree = parser.parse(rule)
    return NormalizeTransformer().transform(tree)


# =====================================================
#                       DEMO
# =====================================================

if __name__ == "__main__":
    rule = "amount > 'USD' AND user.age < 18"

    try:
        ast = validate_rule(rule)
        print("VALID:", ast)
    except DslError as e:
        print("!!! DSL ERROR:")
