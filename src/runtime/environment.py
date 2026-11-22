# scope manager and flow control signals for runtime

from core.debug import log
from core.errors import LolRuntimeError
from semantics.lol_types import NOOB_VAL, LolValue

# control flow signal for gtfo break statment
class _BreakSignal(Exception):
    pass

# return signal carrying evaluated value
class _ReturnSignal(Exception):
    # initalize return signal with evaluated value
    def __init__(self, value: LolValue):
        self.value = value

# runtime environment scope tracking variable bindings
class Environment:
    # initalize scope with optional parent, set implicit accumulator to noob
    def __init__(self, parent: "Environment | None" = None):
        self.parent = parent
        self.bindings: dict[str, LolValue] = {"IT": NOOB_VAL}  # symbol bindings dictionary

    # declare new variable in current scope
    def declare(self, name: str, value: LolValue = NOOB_VAL, line: int = 0) -> None:
        # prevent delcaration of reserved accumulator symbol
        if name == "IT":
            raise LolRuntimeError("Cannot declare reserved implicit variable 'IT'", line)
        # check duplicate delcaration in current scope
        if name in self.bindings:
            raise LolRuntimeError(f"Variable '{name}' is already declared", line)
        log('ENV', f'declare {name} = ({value.type_name}) {value.value!r}')
        self.bindings[name] = value  # store value in bindings dictionary

    # reassign existing variable walking up parent chain
    def assign(self, name: str, value: LolValue, line: int = 0) -> None:
        env: Environment | None = self
        # traverse parent chain to find existing symbol and reassign
        while env is not None:
            if name in env.bindings:
                log('ENV', f'assign {name} = ({value.type_name}) {value.value!r}')
                env.bindings[name] = value
                return
            env = env.parent
        raise LolRuntimeError(f"Variable '{name}' is not declared", line)

    # lookup variable value walking up parent chain
    def lookup(self, name: str, line: int = 0) -> LolValue:
        env: Environment | None = self
        # traverse parent chain to find existing symbol and retrieve value
        while env is not None:
            if name in env.bindings:
                return env.bindings[name]
            env = env.parent
        raise LolRuntimeError(f"Variable '{name}' is not declared", line)

    # retrieve implicit accumulator value from current scope
    def get_it(self) -> LolValue:
        return self.bindings["IT"]

    # update implicit accumulator value in current scope
    def set_it(self, value: LolValue) -> None:
        log('ENV', f'IT <- ({value.type_name}) {value.value!r}')
        self.bindings["IT"] = value

    # return shallow copy of scope bindings dictionary for inspection
    def snapshot(self) -> dict[str, LolValue]:
        return dict(self.bindings)