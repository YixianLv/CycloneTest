from pycdr import cdr
# from pycdr.types import int16

# @cdr(keylist="user_id")
# class Helloworld:
#     user_id: int
#     message: str


@cdr
class Integer:
    seq: int
    keyval: int


@cdr
class String:
    seq: int
    keyval: str
