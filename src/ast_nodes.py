from dataclasses import dataclass, field
from typing import Any
# ast node definitions

# expressions
@dataclass
class Literal:
    value: Any
    type_name: str

@dataclass
class VariableRef:
    name: str

@dataclass
class BinaryOp:
    op: str
    left: Any
    right: Any

@dataclass
class UnaryOp:
    op: str
    operand: Any

@dataclass
class InfiniteBoolExpr:
    op: str
    operands: list[Any] = field(default_factory=list)

@dataclass
class SmooshExpr:
    operands: list[Any] = field(default_factory=list)

SmoothExpr = SmooshExpr  # alias for spec naming compatibility

@dataclass
class TypecastExpr:
    expr: Any
    target_type: str

@dataclass
class FuncCall:
    name: str
    args: list[Any] = field(default_factory=list)


# statements
@dataclass
class VarDecl:
    name: str
    value_expr: Any = None

@dataclass
class Assignment:
    var_name: str
    expr: Any = None

@dataclass
class RecastStmt:
    var_name: str
    target_type: str

@dataclass
class PrintStmt:
    operands: list[Any] = field(default_factory=list)
    suppress_newline: bool = False

@dataclass
class InputStmt:
    var_name: str

@dataclass
class ExprStmt:
    expr: Any

@dataclass
class IfStmt:
    cond_expr: Any = None
    then_body: list[Any] = field(default_factory=list)
    mebbe_clauses: list[tuple[Any, list[Any]]] = field(default_factory=list)
    else_body: list[Any] = field(default_factory=list)

@dataclass
class CaseClause:
    literal: Literal
    body: list[Any] = field(default_factory=list)

@dataclass
class SwitchStmt:
    cases: list[CaseClause] = field(default_factory=list)
    default_case: list[Any] | None = None

@dataclass
class LoopStmt:
    label: str
    operation: str
    var_name: str
    condition_type: str | None = None
    condition_expr: Any = None
    body: list[Any] = field(default_factory=list)

@dataclass
class FuncDef:
    name: str
    params: list[str] = field(default_factory=list)
    body: list[Any] = field(default_factory=list)

@dataclass
class ReturnStmt:
    expr: Any = None

@dataclass
class BreakStmt:
    pass
