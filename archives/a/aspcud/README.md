# aspcud

ASP-based solver for package dependency problems in CUDF format.

## Description

Aspcud is a solver for package dependency problems using Answer Set Programming (ASP). It provides:
- `cudf2lp`: A converter/preprocessor to translate CUDF specifications into ASP facts
- `aspcud`: A solver that orchestrates the translation and solving process

The solver uses ASP grounder (gringo) and solver (clasp) to find solutions to package dependency problems.

## Homepage

https://potassco.org/aspcud/

## Dependencies

### Build Dependencies
- Boost >= 1.43
- CMake >= 2.6
- re2c >= 0.13
- C++14 compiler (gcc >= 4.9 or clang)

### Runtime Dependencies
- clasp >= 3.0.0
- gringo >= 4.2.1 (part of clingo)

## Usage

```bash
aspcud problem.cudf solution.cudf <criteria>
```

## License

MIT License

## Available Versions

- 1.9.6 (building)