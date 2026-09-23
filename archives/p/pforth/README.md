# pForth

Portable ANS-like Forth interpreter written in ANSI C.

## Description

pForth is a portable Forth written in C for most 32 and 64-bit platforms.
It only needs character input and output functions to operate and therefore
does not require an operating system, which makes it handy for bringing up
and testing embedded systems. It also works on desktops including Windows,
Mac and Linux.

pForth is based on ANSI-Forth but is not 100% compatible.

## Build

pForth uses a two-stage bootstrap build:

1. Compile the C-based Forth kernel (`pforth`).
2. Run `pforth -i system.fth` to build the dictionary (`pforth.dic`).
3. Generate `pfdicdat.h` and compile `pforth_standalone` (dictionary embedded).

```sh
cd platforms/unix
make all        # builds pforth, pforth.dic and pforth_standalone
make test       # runs the upstream Forth test suite
```

## Run

```sh
./pforth_standalone      # all-in-one, no external dictionary needed
3 4 + .                  # prints 7
bye
```

## Source

https://github.com/philburk/pforth

## License

BSD Zero Clause License (0BSD).
