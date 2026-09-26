#!/usr/bin/env bash
# Usage: ./run_testcase.sh <testcase.bril> [threshold_file] [local_dce|lvn+local_dce]
#
# Kept for compatibility with the interface used in previous years. This is
# now a thin wrapper around tools/evaluate.py, which checks that your
# optimized program still behaves like the original before it looks at the
# instruction count. Nothing is written into the repository.

set -u

TESTCASE="${1:-}"
THRESHOLD_FILE="${2:-}"
MODE="${3:-}"

if [[ -z "$TESTCASE" || -z "$THRESHOLD_FILE" || -z "$MODE" ]]; then
  echo "Usage: $0 <testcase.bril> <threshold_file> <local_dce|lvn+local_dce>" >&2
  exit 2
fi

if [[ ! -f "$TESTCASE" ]]; then
  echo "Error: test case '$TESTCASE' not found." >&2
  exit 2
fi

if [[ ! -f "$THRESHOLD_FILE" ]]; then
  echo "Error: threshold file '$THRESHOLD_FILE' not found." >&2
  exit 2
fi

THRESHOLD="$(awk '
  /^[[:space:]]*#/ {next}
  /^[[:space:]]*$/ {next}
  {gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0); print; exit}
' "$THRESHOLD_FILE")"

if ! [[ "$THRESHOLD" =~ ^[0-9]+$ ]]; then
  echo "Error: threshold must be an integer; got: '$THRESHOLD' (from $THRESHOLD_FILE)" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$REPO_ROOT/tools/run_case.py" \
  --file "$TESTCASE" --mode "$MODE" --max-dyn-inst "$THRESHOLD"
