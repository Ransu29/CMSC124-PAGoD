from dataclasses import dataclass, field
from typing import Any
# ast node definitions

# expressions
@dataclass
class Literal:
    value: Any
    type_name: str
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class VariableRef:
    name: str
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class BinaryOp:
    op: str
    left: Any
    right: Any
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class UnaryOp:
    op: str
    operand: Any
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class InfiniteBoolExpr:
    op: str
    operands: list[Any] = field(default_factory=list)
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class SmooshExpr:
    operands: list[Any] = field(default_factory=list)
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

SmoothExpr = SmooshExpr  # alias for spec naming compatibility

@dataclass
class TypecastExpr:
    expr: Any
    target_type: str
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class FuncCall:
    name: str
    args: list[Any] = field(default_factory=list)
    line: int = field(default=0, compare=False, repr=False, kw_only=True)


# statements
@dataclass
class VarDecl:
    name: str
    value_expr: Any = None
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class Assignment:
    var_name: str
    expr: Any = None
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class RecastStmt:
    var_name: str
    target_type: str
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class PrintStmt:
    operands: list[Any] = field(default_factory=list)
    suppress_newline: bool = False
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class InputStmt:
    var_name: str
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class ExprStmt:
    expr: Any
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class IfStmt:
    cond_expr: Any = None
    then_body: list[Any] = field(default_factory=list)
    mebbe_clauses: list[tuple[Any, list[Any]]] = field(default_factory=list)
    else_body: list[Any] = field(default_factory=list)
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class CaseClause:
    literal: Literal
    body: list[Any] = field(default_factory=list)
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class SwitchStmt:
    cases: list[CaseClause] = field(default_factory=list)
    default_case: list[Any] | None = None
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class LoopStmt:
    label: str
    operation: str
    var_name: str
    condition_type: str | None = None
    condition_expr: Any = None
    body: list[Any] = field(default_factory=list)
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class FuncDef:
    name: str
    params: list[str] = field(default_factory=list)
    body: list[Any] = field(default_factory=list)
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class ReturnStmt:
    expr: Any = None
    line: int = field(default=0, compare=False, repr=False, kw_only=True)

@dataclass
class BreakStmt:
    line: int = field(default=0, compare=False, repr=False, kw_only=True)
