from os import stat
from typing import Optional
from lark import Lark, Transformer, UnexpectedInput
from src.exceptions import DslError, ErrorCode


# =====================================================
#                    GRAMMAR
# =====================================================

grammar = r"""
?expression: term
           | expression "OR" term   -> or_op

?term: factor
     | term "AND" factor            -> and_op

?factor: "NOT" factor               -> not_op
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
            case "=": return left == right
            case "!=": return left != right
            case ">": return left > right
            case ">=": return left >= right
            case "<": return left < right
            case "<=": return left <= right

        raise ValueError(f"Unknown op: {self.op}")


# =====================================================
#                    AST BUILDER
# =====================================================

class ASTBuilder(Transformer):

    def or_op(self, args): return Or(args[0], args[1])
    def and_op(self, args): return And(args[0], args[1])
    def not_op(self, args): return Not(args[0])

    def comparison(self, args):
        field_tok, op_tok, val = args
        pos = (field_tok.line, field_tok.column)
        return Comparison(field_tok.value, op_tok.value, val, pos)

    def number(self, tok):
        s = tok[0]
        return float(s) if "." in s else int(s)

    def string(self, tok):
        return tok[0][1:-1]


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


def validate_ast(node, rule_text):
    """Рекурсивная проверка семантики; при ошибке -> DslError"""

    if isinstance(node, (Or, And)):
        validate_ast(node.a, rule_text)
        validate_ast(node.b, rule_text)
        return

    if isinstance(node, Not):
        validate_ast(node.a, rule_text)
        return

    if isinstance(node, Comparison):
        line, col = node.pos
        pos_str = f"{line}:{col}"

        # Неизвестное поле
        if node.field not in FIELD_TYPES:
            raise DslError(
                status_code=422,
                err_code=ErrorCode.dsl_invalid_field,
                message=f"Неизвестное поле '{node.field}'",
                position=pos_str,
                near=get_context(rule_text, line, col),
            )

        expected = FIELD_TYPES[node.field]

        # Неверный оператор
        if node.op not in NUMERIC_OPS | EQUALITY_OPS:
            raise DslError(
                status_code=400,
                err_code=ErrorCode.dsl_invalid_operator,
                message=f"Недопустимый оператор '{node.op}'",
                position=pos_str,
                near=get_context(rule_text, line, col),
            )

        # Типы
        if expected == "number" and isinstance(node.value, str):
            raise DslError(
                status_code=422,
                err_code=ErrorCode.dsl_invalid_field,
                message=f"Поле '{node.field}' числовое, но сравнивается со строкой '{node.value}'",
                position=pos_str,
                near=get_context(rule_text, line, col),
            )

        if expected == "string" and node.op in NUMERIC_OPS:
            raise DslError(
                status_code=422,
                err_code=ErrorCode.dsl_invalid_field,
                message=f"Строковое поле '{node.field}' нельзя сравнивать оператором '{node.op}'",
                position=pos_str,
                near=get_context(rule_text, line, col),
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

def validate_rule(rule: str):
    """
    Если правило плохое — бросает DslError.
    Если хорошее — возвращает AST.
    """

    # --- СИНТАКСИС -----------------------------------
    try:
        tree = parser.parse(rule)
    except UnexpectedInput as e:
        raise DslError(
            status_code=422,
            err_code=ErrorCode.dsl_parse_error,
            message="Синтаксическая ошибка",
            position=f"{e.line}:{e.column}",
            near=e.get_context(rule)
        )

    # --- AST -----------------------------------------
    ast = ASTBuilder().transform(tree)

    # --- СЕМАНТИКА -----------------------------------
    validate_ast(ast, rule)

    return ast  # валидно


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

