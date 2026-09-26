# Homework 2: DCE and LVN for Bril

## Overview

In this assignment, you will implement a local Dead Code Elimination (DCE) pass for the Bril intermediate representation (IR). The objective is to remove redundant instructions within basic blocks and then integrate DCE with Local Value Numbering (LVN) to further reduce dynamic instruction count. You will assess the impact of these transformations using the brili interpreter, comparing dynamic instruction counts before and after the passes are applied.

LVN is supplied by the TAs in `src/lvn.py`. You implement only the DCE pass.

## Prerequisites

- Docker
- The homework image, which already contains Python 3, Deno and the Bril toolchain

## Getting Started

1. Clone the repository recursively, so that you get the Bril submodule:
   ```bash
   git clone --recursive https://github.com/NTU-Advanced-Compiler/ntu-2026fall-advanced-compiler-hw2.git
   cd ntu-2026fall-advanced-compiler-hw2
   ```

2. Pull the homework image and start a container with the repository mounted:
   ```bash
   docker pull ghcr.io/ntu-advanced-compiler/acd-hw2:2026
   docker run -it --rm -v "$PWD":/home/student/hw ghcr.io/ntu-advanced-compiler/acd-hw2:2026
   ```

   The repository appears inside the container at `/home/student/hw`. Unlike Homework 1, `bril2json`, `bril2txt` and `brili` are already installed, so you do not need `install_bril.sh`.

## Project Structure
```
homework-directory/
├── src/
│   ├── form_blocks.py
│   ├── local_dce.py
│   ├── lvn.py
│   └── util.py
├── tests/
│   ├── local_dce/
│   ├── lvn+local_dce/
│   ├── safety/
│   ├── additional/
│   └── manifest.json
├── tools/
├── bril/
├── run_testcase.sh
├── verify_hw2.sh
└── README.md
```

`lvn.py`, `form_blocks.py` and `util.py` are supplied. You may add your own helper files in `src/`.

## Implementation Tasks

1. Remove instructions that are never served as arguments of other instructions (`trivial_dce_pass` in `local_dce.py`). Repeat until nothing changes, since removing one instruction can make an earlier one dead.
2. Delete instructions that are unused before the next assignment (`drop_killed_local` in `local_dce.py`). This one considers a single basic block.

Your pass must preserve the behavior of the input program. For every test we compare the output and exit status of your optimized program against the original, and a case where they differ scores zero however few instructions it executes. In particular:

- A value defined in one block and used in a later block must survive. Task 1 collects uses across the whole function; only task 2 is block-local.
- `print`, `call`, `br`, `jmp`, `ret` and the memory operations have effects and must be kept. A `dest` field alone does not make an instruction removable.
- A definition that is overwritten later is still needed if something reads it in between.

`python3 src/local_dce.py` must read one Bril JSON program from stdin and write exactly one Bril JSON program to stdout, then exit 0. Debugging output belongs on stderr.

## Running and Testing

1. To check your work the way it is graded:
```bash
bash verify_hw2.sh <student-id> test
```
All graded test cases are in this repository, so this reports the score you will receive. `tests/manifest.json` lists each case, its category and how much reduction it requires.

2. To generate the form after transformations:
```bash
# DCE only
bril2json < [path_to_testcase] | python3 ./src/local_dce.py | bril2txt > output.bril

# Combine DCE with LVN
bril2json < [path_to_testcase] | python3 ./src/lvn.py | python3 ./src/local_dce.py | bril2txt > output.bril
```
3. To check the dynamic instruction count:
```bash
#  Original program
bril2json < [path_to_testcase] | brili -p

# DCE only
bril2json < [path_to_testcase] | python3 ./src/local_dce.py | brili -p

# Combine DCE with LVN
bril2json < [path_to_testcase] | python3 ./src/lvn.py | python3 ./src/local_dce.py | brili -p
```
4. To check if the dynamic instruction count pass the threshold
```bash
# DCE only
bash run_testcase.sh [path_to_testcase] [path_to_corresponding_threshold_file] local_dce

# Combine DCE with LVN
bash run_testcase.sh [path_to_testcase] [path_to_corresponding_threshold_file] lvn+local_dce
```

For test cases in `tests/local_dce`, dynamic instruction count can be reduced to threshold with only DCE enabled. For those in `tests/lvn+local_dce`, it can be lowered with a combination of LVN and DCE. The cases in `tests/safety` ask you to preserve behavior, and for some of them the correct outcome is to change nothing.

## Submission Instructions

1. Implement all required functionalities in the `src/` directory.
2. Test your implementation thoroughly.
3. Put `src/` in a directory named after your student ID, with the first character in lower case, and compress it into a zip archive with the same name:
   ```
   r14922000.zip
   └── r14922000/
       └── src/
           └── local_dce.py
   ```
4. Upload the archive to NTU COOL. Do not include `bril/`, screenshots or test output.

## Do and Don't

- You are allowed to modify any part of the starter code within the src/ directory to suit your approach. While the current structure serves as a guideline, ensuring the driver script functions properly is key for grading.
- Make sure you have a solid understanding of the algorithm before starting your implementation.
- DO NOT rely on modifications to `src/lvn.py`; it is replaced with a pristine copy during grading.
- DO NOT special-case a particular test case. The test cases are given to you to develop against, not to hard-code.

## Additional Resources

- Engineering a Compiler
- [Bril Language Reference](https://capra.cs.cornell.edu/bril/lang/index.html)
- Course lecture notes on DCE and LVN
