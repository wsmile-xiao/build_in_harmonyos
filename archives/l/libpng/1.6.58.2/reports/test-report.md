# libpng 1.6.58.2 target validation report

## Snapshot

- Root objective: GitCode Issue #1093, `dosbox-staging/0.82.2-r1`.
- Dependency task: contrib task 3319, GitCode Issue #2003.
- Base HEAD/tree/base: `9b94a603c1f031845a9aab68e360fd43443c62e6` / `f19f3423e3ad26f2cf58ca8b5e33224a0cb2043e` / `807fa2c350480cb15271d1891f23b2b991916fd5`.
- Frozen candidate tree: `7db177bc6b170867625d4d202703b87bc6d23869`.
- Device run: `libpng-1.6.58.2-task3319-transfer-only-r20-148108-finish-r1` on `10.62.148.108:2222`.

## Results

| Scope | Passed | Total | Result |
|---|---:|---:|---|
| Upstream unique inventory | 36 | 36 | PASS |
| Conan consumer flow | 1 | 1 | PASS |
| Consumer assertions within the flow | 4 | 4 | PASS |

The raw upstream log is `upstream-test.log` (SHA256 `4dea0fffa95c215904334f6cd2cae09f0e9457c86c6699d999c1f1fbfbcb1121`). It records every named Automake test followed by `TOTAL: 36`, `PASS: 36`, `SKIP: 0`, `FAIL: 0`, and `ERROR: 0`.

The durable terminal is `FORMAL_FINISH_PASS_CLEANED`, with `launch_count=1`, terminal archive SHA256 `73e44314a508f2093185a2c857900f7189093360470b6c8d37c840ecf919edb8`, and no second launch or artifact upload. Cleanup recorded four zero process counts and two clean scans.

The host wrapper emitted a post-terminal PowerShell return-type error after writing the durable PASS. No retry was made; `w3-final-result.json`, `w3-terminal-readback.txt`, the validated terminal archive, and `w3-cleanup-readback.txt` independently establish the terminal state.
