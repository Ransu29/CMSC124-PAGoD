# LOLCODE dynamic type representation, casting rules, and comparison helpers

from dataclasses import dataclass
import re
from typing import Any

from errors import LolRuntimeError

VALID_TYPES = {"NOOB", "NUMBR", "NUMBAR", "YARN", "TROOF"}

# numeric string formats accepted when casting YARN to NUMBR or NUMBAR
INT_STRING_PATTERN = re.compile(r"^-?[0-9]+$")
FLOAT_STRING_PATTERN = re.compile(r"^-?[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class LolValue:
    # explicit type tag prevents Python bool/int overlap (e.g. isinstance(True, int))
    type_name: str
    value: Any


NOOB_VAL = LolValue("NOOB", None)


def _format_numbar(num: float) -> str:
    # normalize -0.0 to 0.0 and truncate decimals beyond 2 places per LOLCODE spec
    if num == 0.0:
        return "0.0"

    raw = str(num)
    if "e" in raw or "E" in raw:
        raw = format(num, ".2f")

    if "." not in raw:
        return f"{raw}.0"

    whole, frac = raw.split(".", 1)
    return f"{whole}.{frac[:2]}"


def to_troof(val: LolValue) -> LolValue:
    # NOOB, numeric zero, and empty string map to FAIL; everything else maps to WIN
    if val.type_name == "NOOB":
        return LolValue("TROOF", False)
    if val.type_name == "TROOF":
        return val
    if val.type_name == "NUMBR":
        return LolValue("TROOF", val.value != 0)
    if val.type_name == "NUMBAR":
        return LolValue("TROOF", val.value != 0.0)
    if val.type_name == "YARN":
        return LolValue("TROOF", val.value != "")
    return LolValue("TROOF", bool(val.value))


def to_numbr(val: LolValue, explicit: bool = False, line: int = 0) -> LolValue:
    if val.type_name == "NUMBR":
        return val
    if val.type_name == "NOOB":
        if not explicit:
            raise LolRuntimeError("Cannot implicitly cast NOOB to NUMBR", line)
        return LolValue("NUMBR", 0)
    if val.type_name == "TROOF":
        return LolValue("NUMBR", 1 if val.value else 0)
    if val.type_name == "NUMBAR":
        return LolValue("NUMBR", int(val.value))
    if val.type_name == "YARN":
        if INT_STRING_PATTERN.match(val.value):
            return LolValue("NUMBR", int(val.value))
        if FLOAT_STRING_PATTERN.match(val.value):
            return LolValue("NUMBR", int(float(val.value)))
        raise LolRuntimeError(f"Cannot cast YARN '{val.value}' to NUMBR", line)
    raise LolRuntimeError(f"Cannot cast {val.type_name} to NUMBR", line)


def to_numbar(val: LolValue, explicit: bool = False, line: int = 0) -> LolValue:
    if val.type_name == "NUMBAR":
        return val
    if val.type_name == "NOOB":
        if not explicit:
            raise LolRuntimeError("Cannot implicitly cast NOOB to NUMBAR", line)
        return LolValue("NUMBAR", 0.0)
    if val.type_name == "TROOF":
        return LolValue("NUMBAR", 1.0 if val.value else 0.0)
    if val.type_name == "NUMBR":
        return LolValue("NUMBAR", float(val.value))
    if val.type_name == "YARN":
        if INT_STRING_PATTERN.match(val.value) or FLOAT_STRING_PATTERN.match(val.value):
            return LolValue("NUMBAR", float(val.value))
        raise LolRuntimeError(f"Cannot cast YARN '{val.value}' to NUMBAR", line)
    raise LolRuntimeError(f"Cannot cast {val.type_name} to NUMBAR", line)


def to_yarn(val: LolValue, explicit: bool = False, line: int = 0) -> LolValue:
    if val.type_name == "YARN":
        return val
    if val.type_name == "NOOB":
        if not explicit:
            raise LolRuntimeError("Cannot implicitly cast NOOB to YARN", line)
        return LolValue("YARN", "")
    if val.type_name == "TROOF":
        return LolValue("YARN", "WIN" if val.value else "FAIL")
    if val.type_name == "NUMBR":
        return LolValue("YARN", str(val.value))
    if val.type_name == "NUMBAR":
        return LolValue("YARN", _format_numbar(val.value))
    raise LolRuntimeError(f"Cannot cast {val.type_name} to YARN", line)


def cast_value(val: LolValue, target_type: str, explicit: bool = False, line: int = 0) -> LolValue:
    if target_type not in VALID_TYPES:
        raise LolRuntimeError(f"Unknown type '{target_type}'", line)
    if target_type == "NOOB":
        if not explicit:
            raise LolRuntimeError("Cannot implicitly cast value to NOOB", line)
        return NOOB_VAL
    if target_type == "TROOF":
        return to_troof(val)
    if target_type == "NUMBR":
        return to_numbr(val, explicit=explicit, line=line)
    if target_type == "NUMBAR":
        return to_numbar(val, explicit=explicit, line=line)
    return to_yarn(val, explicit=explicit, line=line)


def coerce_numeric(val: LolValue, line: int = 0) -> LolValue:
    # arithmetic operations implicitly convert YARN with '.' to NUMBAR and without '.' to NUMBR
    if val.type_name in ("NUMBR", "NUMBAR"):
        return val
    if val.type_name == "TROOF":
        return LolValue("NUMBR", 1 if val.value else 0)
    if val.type_name == "YARN":
        if INT_STRING_PATTERN.match(val.value):
            return LolValue("NUMBR", int(val.value))
        if FLOAT_STRING_PATTERN.match(val.value):
            return LolValue("NUMBAR", float(val.value))
        raise LolRuntimeError(f"Cannot implicitly cast YARN '{val.value}' to a number", line)
    raise LolRuntimeError("Cannot implicitly cast NOOB to a number", line)


def values_equal(left: LolValue, right: LolValue) -> bool:
    # comparisons use numeric equality across NUMBR/NUMBAR and forbid other implicit casts
    if left.type_name == "NOOB" and right.type_name == "NOOB":
        return True
    if left.type_name == right.type_name:
        return left.value == right.value
    if left.type_name in ("NUMBR", "NUMBAR") and right.type_name in ("NUMBR", "NUMBAR"):
        return float(left.value) == float(right.value)
    return False
