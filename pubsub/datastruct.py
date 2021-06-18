from pycdr import cdr
from pycdr.types import array, sequence


@cdr
class Integer:
    seq: int
    keyval: int


@cdr
class String:
    seq: int
    keyval: str


@cdr
class Array:
    seq: int
    keyval: array[int, 3]


@cdr
class Sequence:
    seq: int
    keyval: sequence[int]
