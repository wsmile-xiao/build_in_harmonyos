# libdisasm

`libdisasm` is a library for decoding and formatting x86 (IA-32) machine
instructions, developed as part of the "bastard" disassembler project. It
decodes a byte buffer into instruction structures (mnemonic, type,
operands) and formats them to Intel, AT&T, XML, raw, or native syntax.
The same source tree builds `x86dis`, a command-line disassembler that
wraps the library.

## OpenHarmony adaptation

- 0.23 source: https://sourceforge.net/projects/bastard/ (official project
  files, `libdisasm/0.23/libdisasm-0.23.tar.gz`)
- Build system: autotools (2003-era, libtool 1.5.24)
- Dependencies: none (pure C)
- Patches:
  - `0001-config-sub-aarch64.patch`: the bundled `config.sub` predates
    aarch64; accept `aarch64-*-linux*` / `aarch64-*-ohos*` triples
  - `0002-configure-umask-022.patch`: create the `config.status` tmp dir
    with umask 022 (setgid hmdfs makes umask 077 dirs unwritable)
- The recipe builds both the static/shared `libdisasm` library and the
  `x86dis` CLI; `commands.json` is declared at the software level

## Testing

The upstream suite (`test/run-test.sh`) round-trips every instruction in
`test/ia32_test_insn.S` through GNU `as --32` + `objdump` + `perl` and
compares against libdisasm output. Those host-only x86 binutils tools do
not exist on the OHOS target, so the check target is not run there. The
Conan consumer test decodes hand-verified IA-32 encodings through the
packaged library (sizes, instruction types, operands, formatted text) and
is architecture-independent, since the library decodes buffers without
executing them.
