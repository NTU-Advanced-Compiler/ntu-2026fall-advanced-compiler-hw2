"""Strict evaluator for the HW2 optimization pipeline.

This module is the single authority for whether a test case passes. It is
used by the student self-check (`verify_hw2.sh`) and by the TA batch
grader, so both agree on every decision.

The rule that matters: a case awards optimization points only after the
transformed program has been shown to behave exactly like the original.
An instruction-count improvement from an incorrect program is worth zero.

Each stage of the pipeline runs as its own subprocess, and every stage is
checked independently for exit status, timeout, output size, and complete
parseable JSON. Nothing is written to the repository; each case runs in
its own temporary directory.
"""
import json
import os
import shutil
import subprocess
import tempfile

# Modules that belong to the TAs. The LVN stage always runs against
# pristine copies of these, so a student's edits can never change the
# behavior of the supplied pass.
TA_MODULES = ('lvn.py', 'form_blocks.py', 'util.py')

# The student implements this file.
STUDENT_ENTRY = 'local_dce.py'

DEFAULT_TIMEOUT = 10          # seconds per stage
MAX_OUTPUT_BYTES = 8 << 20    # 8 MiB per stage


class StageError(Exception):
    """A pipeline stage failed. The message is shown to the student."""

    def __init__(self, stage, detail):
        super(StageError, self).__init__('{}: {}'.format(stage, detail))
        self.stage = stage
        self.detail = detail


def _run(cmd, stdin_bytes, timeout=DEFAULT_TIMEOUT, cwd=None, stage='stage'):
    """Run one stage. Returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        raise StageError(stage, 'exceeded the {}s time limit'.format(timeout))
    except FileNotFoundError:
        raise StageError(stage, 'command not found: {}'.format(cmd[0]))
    if len(proc.stdout) > MAX_OUTPUT_BYTES:
        raise StageError(stage, 'produced more than {} bytes of output'
                         .format(MAX_OUTPUT_BYTES))
    return proc.returncode, proc.stdout, proc.stderr


def _decode(data):
    return data.decode('utf-8', errors='replace')


def bril2json(bril_path, timeout=DEFAULT_TIMEOUT):
    """Convert a Bril text program to canonical JSON bytes."""
    with open(bril_path, 'rb') as fh:
        source = fh.read()
    rc, out, err = _run(['bril2json'], source, timeout, stage='bril2json')
    if rc != 0:
        raise StageError('bril2json', 'exit status {}: {}'
                         .format(rc, _decode(err).strip()))
    return out


def run_pass(script, module_dir, json_bytes, stage, timeout=DEFAULT_TIMEOUT):
    """Run one optimization pass and return its output JSON bytes.

    The pass must read exactly one Bril JSON object from stdin and write
    exactly one Bril JSON object to stdout. Anything it writes to stderr
    is ignored, so debugging output there is harmless.
    """
    rc, out, err = _run(['python3', script], json_bytes, timeout,
                        cwd=module_dir, stage=stage)
    if rc != 0:
        raise StageError(stage, 'exit status {} (stderr: {})'
                         .format(rc, _decode(err).strip()[:400] or 'empty'))
    if not out.strip():
        raise StageError(stage, 'wrote nothing to stdout')
    try:
        parsed = json.loads(out.decode('utf-8'))
    except UnicodeDecodeError:
        raise StageError(stage, 'stdout was not valid UTF-8')
    except json.JSONDecodeError as exc:
        raise StageError(stage, 'stdout was not one complete JSON object ({})'
                         .format(exc))
    if not isinstance(parsed, dict) or 'functions' not in parsed:
        raise StageError(stage, 'stdout was not a Bril program '
                                '(no "functions" key)')
    return out


def interpret(json_bytes, args, timeout=DEFAULT_TIMEOUT):
    """Run a Bril program under the profiling interpreter.

    Returns a dict with the program's stdout, its exit status, and its
    dynamic instruction count. A program that exits nonzero is a valid
    observation, not an evaluator error: the original and the optimized
    program simply have to agree.
    """
    cmd = ['brili', '-p'] + [str(a) for a in args]
    rc, out, err = _run(cmd, json_bytes, timeout, stage='brili')
    dyn = None
    for line in _decode(err).splitlines():
        if line.startswith('total_dyn_inst:'):
            try:
                dyn = int(line.split(':', 1)[1].strip())
            except ValueError:
                dyn = None
            break
    return {
        'stdout': _decode(out),
        'status': rc,
        'dyn_inst': dyn,
        'stderr': _decode(err),
    }


def build_exec_dirs(student_src, ta_src, workdir):
    """Create the two directories the pipeline stages run in.

    `ta_exec` holds pristine TA modules and is where the supplied LVN
    runs, so LVN behaves identically for every submission.

    `student_exec` holds the student's files, including any helper
    modules they added. `lvn.py` there is replaced with the pristine copy
    so that a modified LVN cannot be reached through an import.
    """
    if not os.path.isdir(student_src):
        raise StageError('submission layout',
                         'source directory not found: {}'.format(student_src))
    if not os.path.isfile(os.path.join(student_src, STUDENT_ENTRY)):
        raise StageError('submission layout',
                         '{} not found in {}'.format(STUDENT_ENTRY,
                                                     student_src))
    ta_exec = os.path.join(workdir, 'ta_exec')
    student_exec = os.path.join(workdir, 'student_exec')
    os.makedirs(ta_exec, exist_ok=True)
    os.makedirs(student_exec, exist_ok=True)

    for name in TA_MODULES:
        shutil.copy2(os.path.join(ta_src, name), os.path.join(ta_exec, name))

    # Start the student's directory from the supplied modules, so a
    # submission that contains only local_dce.py still imports
    # form_blocks and util. A student's own copy of a helper overwrites
    # these in the loop below.
    for name in TA_MODULES:
        shutil.copy2(os.path.join(ta_src, name),
                     os.path.join(student_exec, name))

    for entry in sorted(os.listdir(student_src)):
        src = os.path.join(student_src, entry)
        if os.path.isfile(src) and entry.endswith('.py'):
            shutil.copy2(src, os.path.join(student_exec, entry))
    # The supplied LVN is TA-owned even inside the student's directory.
    shutil.copy2(os.path.join(ta_src, 'lvn.py'),
                 os.path.join(student_exec, 'lvn.py'))
    return ta_exec, student_exec


def optimize(json_bytes, mode, ta_exec, student_exec, timeout):
    """Apply the requested pipeline, one checked subprocess per stage."""
    data = json_bytes
    if mode == 'lvn+local_dce':
        data = run_pass('lvn.py', ta_exec, data, 'supplied lvn.py', timeout)
    elif mode != 'local_dce':
        raise StageError('pipeline', 'unknown mode {!r}'.format(mode))
    return run_pass(STUDENT_ENTRY, student_exec, data,
                    'your local_dce.py', timeout)


def check_criterion(criterion, baseline, optimized):
    """Decide whether the optimization requirement is met.

    Returns (ok, explanation). `preserve_only` is used for safety
    fixtures, where the correct answer may be to change nothing.
    """
    kind = criterion.get('type', 'preserve_only')
    base = baseline['dyn_inst']
    opt = optimized['dyn_inst']

    if kind == 'preserve_only':
        return True, 'behavior preserved (no reduction required)'

    if base is None or opt is None:
        return False, 'could not read total_dyn_inst from the interpreter'

    if kind == 'max_dyn_inst':
        limit = criterion['value']
        if opt < base and opt <= limit:
            return True, ('{} -> {} dynamic instructions (limit {})'
                          .format(base, opt, limit))
        return False, ('{} -> {} dynamic instructions; needs fewer than {} '
                       'and at most {}'.format(base, opt, base, limit))

    if kind == 'reduce_at_least':
        need = criterion['value']
        if base - opt >= need:
            return True, ('{} -> {} dynamic instructions (removed {})'
                          .format(base, opt, base - opt))
        return False, ('{} -> {} dynamic instructions; needs at least {} '
                       'fewer'.format(base, opt, need))

    if kind == 'no_increase':
        if opt <= base:
            return True, ('{} -> {} dynamic instructions (no increase)'
                          .format(base, opt))
        return False, ('{} -> {} dynamic instructions; must not increase'
                       .format(base, opt))

    return False, 'unknown criterion {!r}'.format(kind)


def evaluate_case(case, repo_root, student_src, ta_src, timeout=DEFAULT_TIMEOUT):
    """Evaluate one case and return a result dict.

    The order here is the whole point: behavior first, optimization
    second. `points` is awarded only if both hold.
    """
    result = {
        'id': case['id'],
        'category': case.get('category', 'uncategorized'),
        'mode': case['mode'],
        'max_points': case['points'],
        'points': 0,
        'passed': False,
        'messages': [],
        'runs': [],
    }
    bril_path = os.path.join(repo_root, case['file'])
    arg_sets = case.get('arg_sets') or [[]]

    workdir = tempfile.mkdtemp(prefix='hw2case.')
    try:
        try:
            ta_exec, student_exec = build_exec_dirs(student_src, ta_src,
                                                    workdir)
            original = bril2json(bril_path, timeout)
            optimized_json = optimize(original, case['mode'], ta_exec,
                                      student_exec, timeout)
        except StageError as exc:
            result['messages'].append('FAILED in {}'.format(exc))
            return result

        # Behavior must match on every argument set before anything else.
        all_match = True
        for args in arg_sets:
            try:
                base = interpret(original, args, timeout)
                opt = interpret(optimized_json, args, timeout)
            except StageError as exc:
                result['messages'].append('FAILED in {}'.format(exc))
                return result

            run = {
                'args': args,
                'baseline_stdout': base['stdout'],
                'optimized_stdout': opt['stdout'],
                'baseline_status': base['status'],
                'optimized_status': opt['status'],
                'baseline_dyn_inst': base['dyn_inst'],
                'optimized_dyn_inst': opt['dyn_inst'],
            }
            result['runs'].append(run)

            label = 'args {}'.format(args) if args else 'no arguments'
            if base['stdout'] != opt['stdout']:
                all_match = False
                result['messages'].append(
                    'WRONG OUTPUT with {}: original printed {!r}, '
                    'your optimized program printed {!r}'.format(
                        label, base['stdout'], opt['stdout']))
            elif base['status'] != opt['status']:
                all_match = False
                result['messages'].append(
                    'WRONG COMPLETION STATUS with {}: original exited {}, '
                    'your optimized program exited {}'.format(
                        label, base['status'], opt['status']))

        if not all_match:
            result['messages'].append(
                'No optimization credit is given for a program whose '
                'behavior differs from the original.')
            return result

        # Behavior is preserved; now check the optimization requirement
        # on the argument set the fixture was designed around.
        primary = result['runs'][0]
        ok, why = check_criterion(
            case.get('criterion', {'type': 'preserve_only'}),
            {'dyn_inst': primary['baseline_dyn_inst']},
            {'dyn_inst': primary['optimized_dyn_inst']},
        )
        result['messages'].append(('OK: ' if ok else 'NOT MET: ') + why)
        if ok:
            result['passed'] = True
            result['points'] = case['points']
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def load_manifest(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)['cases']


def load_manifest_full(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def evaluate_all(cases, repo_root, student_src, ta_src,
                 timeout=DEFAULT_TIMEOUT):
    results = [evaluate_case(c, repo_root, student_src, ta_src, timeout)
               for c in cases]
    return {
        'results': results,
        'score': sum(r['points'] for r in results),
        'max_score': sum(r['max_points'] for r in results),
    }
