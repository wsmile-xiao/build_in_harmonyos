# libffi 3.5.2 adaptation notes

## Current status

The SDK12 AArch64 static package builds and installs successfully. Fresh target
run r10 validates every registered upstream configuration and the installed-
package consumer. The upstream test pass rate is **363/363 (100%)**. Each
upstream configuration is executed at `-O0` and `-O2`; all 726 execution
records are PASS. The optimization variants are repeated configurations, not
additional independent tests. The single consumer flow is 1/1 PASS.

Publication is not claimed. The target result is a local evidence closure and
does not imply any CI state.

## Source and patches

- Official release archive SHA256:
  `f3a3082a23b37c293a4fcd1053147b371f2ff91fa7ea1b2a52e335676bac82dc`
- Offline validation may set `user.libffi:source_archive` to that exact archive.
  The recipe rejects missing files and digest mismatches before extraction;
  normal builds continue to use the official release URL.
- `0001-config-guess-sub-ohos.patch`: recognizes HarmonyOS and `linux-ohos`.
- `0002-configure-hmdfs-umask.patch`: selects a usable temporary-directory mask
  only for the target host.
- `0003-tramp-hmdfs-path.patch`: after the ordinary file open fails, resolves an
  HMDFS mount path and accepts only a regular file whose mapped bytes match.
- `0004-tramp-posix-capability.patch`: compile-probes the POSIX mmap, file and
  pthread interfaces used by the static-trampoline implementation.

The package is static-only and PIC-enabled. It configures with
`--disable-shared --enable-static --disable-multi-os-directory` and disables
Automake dependency tracking. The recipe prevents regeneration of the release
Autotools files and verifies that source content is unchanged by generated-path
normalization.

## AArch64 call-frame information repair

Target run r7 discovered 363 independent configurations and executed their O0
and O2 variants. It produced 722 PASS and 4 FAIL. The only failing independent
entries were `libffi.closures/unwindtest.cc` and
`libffi.closures/unwindtest_ffi_call.cc`, both at O0 and O2. All other entries
and the ordinary C++ exception baseline passed.

The release `configure` call-frame-information probe runs inline assembly in a
C function. Without an unwind-table request, the target compiler did not place
the state directives inside an active frame interval, so the probe reported
`no`. Consequently `HAVE_AS_CFI_PSEUDO_OP` was absent and AArch64 `sysv.o` did
not carry the frame information needed when exceptions cross libffi assembly
frames.

For OHOS only, the recipe appends `-funwind-tables` through
`AutotoolsToolchain`. It then requires exactly one
`#define HAVE_AS_CFI_PSEUDO_OP 1` in the generated `fficonfig.h`. This retains
the upstream probe as the source of truth: the recipe does not seed a cache
answer and does not edit generated configuration output.

In r10 the probe reports `yes`; `sysv.o` contains `.eh_frame` and
`.rela.eh_frame`; the two former failure entries pass in both optimization
configurations; and the full suite closes at 726/726 PASS.

## Upstream test accounting

Dynamic discovery from the verified official archive finds 363 independent
DejaGNU configurations:

- 161 `libffi.bhaible`;
- 72 `libffi.call`;
- 99 `libffi.closures`;
- 28 `libffi.complex`;
- 2 `libffi.go`;
- 1 `libffi.threads`.

There are 362 run actions and one compile-only action. Exactly 104 independent
configurations use output oracles. O0 and O2 produce 726 unique execution
records, all PASS, while the independent total remains 363.

The consumer is one process flow. It checks ordinary `ffi_call`, aggregate ABI
return and a real `ffi_closure` callback. Those internal checks are assertions,
not separate tests.

## Target r10 evidence

- Upstream test pass rate: `363/363 (100%)`.
- O0 executions: `363/363 PASS`.
- O2 executions: `363/363 PASS`.
- Total execution records: `726/726 PASS`.
- Installed-package consumer: `1/1 PASS`.
- Evidence archive SHA256:
  `a8b2a328ccb5f59d7fcc547ab59a811cbf86ffe5ff138fe73d2fd29ad383873c`.
- Runner SHA256:
  `55bc54c0c83daa4abb5f84a52a00a0045950f584e2e4b75667d336ec61298265`.
- Frozen recipe SHA256:
  `cdf87c04cb6bf4be5feb2e82715b08bc474053a3c77bc3c2cb8d344db533d668`.
- Summary SHA256:
  `b7d9cf4c4fcaa83203d717d13fc1b7ce6aaa8a08372fce6d11ff655565d5f8c9`.
- Execution manifest SHA256:
  `2d0d1b3bd7c9ce735363d90ec97870e073164e31ae6d469acdd8ca30f4b203fc`.
- Source manifest SHA256:
  `d775c2f867e93855e49efcf4017ebbcbece546eb1b5fe94ada54634687351f5c`.
- Evidence file list SHA256:
  `27e9d00a422566b87dbc5d2033f0662e40c9733cdcd55492d99ae2d8ac9f5b76`.
- Evidence hash manifest SHA256:
  `c21ecfa45d7731e1468e7846c2400da5fc5023e9a919f90977d5b66940d452f5`.
- Built `libffi.a` SHA256:
  `3264e2c8f1bb609506d174cfdf7f028697be191f5e806d293c50e7be9a5ec7f5`.
- AArch64 `sysv.o` SHA256:
  `66933bc0598c87a3a34f7d617ae5adac924f442e1a7c22359988a61ae7056525`.

The independent validator binds eight frozen inputs, re-derives discovery from
the official archive, verifies 726 unique terminals and their raw compile,
sign and run logs, checks the consumer output, and validates 3661 evidence
files against 3662 SHA256 records. It also rejects 13 negative mutations.

## Historical and execution boundaries

- r7 remains failure evidence (`722 PASS / 4 FAIL`) and is not counted as a
  successful run.
- Host results remain useful diagnostics but are not used to inflate the
  target count.
- The recipe's cross-build branch correctly reports target execution as
  `NOT_RUN` when Conan cannot execute target binaries. That per-invocation
  message does not conflict with the separately completed target r10 evidence.
- No CI result or publication state is inferred from r10.
