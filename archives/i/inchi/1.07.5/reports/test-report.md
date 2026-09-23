# InChI 1.07.5 HarmonyOS PC test report

## Summary

| Test set | Executed | Passed | Failed | Skipped | Result |
|----------|---------:|-------:|-------:|--------:|--------|
| Upstream GoogleTest programs | 7 | 7 | 0 | 0 | 100% |
| Conan consumer program | 1 | 1 | 0 | 0 | 100% |

The seven upstream programs reported 59 runtime GoogleTest cases. The consumer
performed six API assertions covering valid and invalid InChI classification,
InChIKey generation, exact expected key equality, and key validation.

## Upstream inventory

- `test_ichimain`
- `test_inchi_dll_b`
- `test_inpdef`
- `test_mol_fmt`
- `test_permutation_util`
- `test_strutil`
- `test_util`

`reports/upstream-inventory.txt` binds `INVENTORY_COUNT=7`. No upstream test
source was modified. `reports/upstream-test.log` contains the exact r4 target
stdout/stderr and ends with `UPSTREAM_PROGRAMS=7/7 PASS` and
`RUNTIME_TEST_CASES=59/59 PASS`.

## Consumer coverage

The consumer links the packaged `inchi::inchi` target and executes against the
packaged shared library. It validates:

1. a standard water InChI layout;
2. rejection of an invalid prefix;
3. successful InChIKey generation;
4. exact water InChIKey equality;
5. validation of the generated key;
6. rejection of an invalid key length.

## Target result

- Endpoint: `10.62.150.125:8022`
- Run: `inchi-1.07.5-w3-r4`
- Candidate code tree: `c52b9bed9896471f7d7e923963a4ebba62ef4783`
- Launch count: `1`
- Receipt phases: `12/12`
- Signed artifact state: `10/10`
- Release/postrelease: `PASS/PASS`
- Transaction result SHA-256:
  `01809a9efb0dd322b2ea0f6a87ed21c0659fba8b84e67da58f0df9641681199e`

The predecessor r1 consumer failure and stale r2/r3 recipe identities are not
included in the passing numerator; no transaction was relaunched.
