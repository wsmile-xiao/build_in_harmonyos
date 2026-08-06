# libICE 1.1.2 validation report

Upstream tests: **0/0**. Upstream registers no test cases; the mandatory
`make -j1 check` target completed successfully for both shared and static builds.

Adapted consumers: **2/2**. Both independent installed-package consumers passed;
their repeated execution against shared and static variants is counted once.

## Consumer results

| Consumer | Result | Contract |
| --- | --- | --- |
| Authority file round-trip | PASS | Writes and reads a complete `IceAuthFileEntry`, verifies every field and EOF, then removes the file. |
| Public API contract | PASS | Verifies `ICEAUTHORITY`, nonzero cookie generation, error-handler registration, and NULL-safe cleanup. |

## Package results

- Shared package: AArch64 `libICE.so.6.3.0`, SONAME `libICE.so.6`, six public headers, relocatable `ice.pc`, and required public symbols.
- Static package: `libICE.a` with 19 unique members, six public headers, relocatable `ice.pc`, and no shared-library payload.
- Both packages omit the non-relocatable `libICE.la` file.
- W0 resolved the exact xorgproto and xtrans recipe and package revisions from the `ohpcd` remote without building dependencies.

## Evidence

- Run: `libice-1.1.2-fresh-w3-r11`
- Independent validator: `LIBICE_R11_RESULT_VALID=1 files=31 upstream=0/0 adapted=2/2`
- Result archive SHA-256: `77de0cd4a25ba460f7f327a5e157fdd92195821f6a36eba84c20c9a8b99504fa`
