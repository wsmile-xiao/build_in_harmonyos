# gumbo 0.10.1 — native target verification

Source SHA-256: 28463053d44a5dfbc4b77bcf49c8cee119338ffa636cc17fc3378421d714efad.
Runtime candidate tree: 8170816507cbe3b83b342f9f1e111acd1d7a2e3d.

| Independent denominator | Actual result | Evidence |
| --- | --- | --- |
| Upstream registered GoogleTest cases | 172/172, no failures or skipped cases | upstream-test-inventory.txt, upstream-test-result.xml, upstream-test.log |
| Complete consumer | 1/1, seven assertions | consumer-test.log |
| Native HarmonyOS PC/HMDFS consumer | 1/1 | harmony-test-inventory.txt, harmony-test.log |
| Windows Release/NDEBUG directed controls | 5/5, host only | external gumbo-null-controls-r002/result.json |

Reports are exact bytes derived from frozen w3-gumbo-r003 snapshot-009.json;
derivation did not execute tests. The independent validator replayed the full
receipt/WAL chain, requiring one launch, no owned live processes and completed
release/postrelease. Failed r001/r002 remain immutable and are not combined
with r003. Windows static Conan create RC0 is separate from native W3.

This report does not certify formal native finish, platform CI, latest AI Review
or submission. Those gates must use the final pushed HEAD.
