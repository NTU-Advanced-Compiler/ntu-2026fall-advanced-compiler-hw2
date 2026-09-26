"""Dead code elimination for Bril. This is the file you implement.

Command-line contract (the graders rely on it exactly):

    python3 src/local_dce.py

reads one Bril JSON program from stdin and writes one Bril JSON program
to stdout. Write nothing else to stdout; debugging output goes to stderr.
Exit with status 0 on success.

You implement the two functions marked TODO. You may add helper functions
or extra .py files in src/. Do not rename `trivial_dce_pass`,
`drop_killed_local`, or the stdin/stdout behavior above.

Note that `form_blocks` yields a leading label as part of a block, and a
label has no 'op' key. An instruction is removable only if it has a
'dest' and no side effect; `print`, `call`, `br`, `jmp`, `ret` and the
memory operations must be preserved even when their result is unused.
"""
import sys
import json
from form_blocks import form_blocks
from util import flatten


def trivial_dce_pass(func):
    """
    TODO:
    1. Remove instructions from func that are never used as arguments to any other instruction.
    2. Return a bool indicating whether anything changed.
    """
    return False



def drop_killed_local(block):
    """
    TODO:
    1. Delete instructions in a single block whose result is unused before the next assignment. 
    2. Return a bool indicating whether anything changed.
    """
    return False


def drop_killed_pass(func):
    """Drop killed functions from *all* blocks. Return a bool indicating
    whether anything changed.
    """
    blocks = list(form_blocks(func['instrs']))
    changed = False
    for block in blocks:
        changed |= drop_killed_local(block)
    func['instrs'] = flatten(blocks)
    return changed


def trivial_dce_plus(func):
    while trivial_dce_pass(func) or drop_killed_pass(func):
        pass




def localopt():
    modify_func = trivial_dce_plus
    # Apply the change to all the functions in the input program.
    bril = json.load(sys.stdin)
    for func in bril['functions']:
        modify_func(func)
    json.dump(bril, sys.stdout, indent=2, sort_keys=True)


if __name__ == '__main__':
    localopt()
