# ParaFly

ParaFly runs a command list in parallel using OpenMP.

Upstream: https://github.com/ParaFly/ParaFly (tag `v0.1.0`)

Example:

```sh
ParaFly -c commands.txt -CPU 4
```

Each line in `commands.txt` is run as a command. ParaFly records completed lines alongside the command file and records failed commands separately.
