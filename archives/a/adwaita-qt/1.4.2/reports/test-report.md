# adwaita-qt 1.4.2 Test Report

## Test Inventory

- Upstream automated tests: 0/0. The 1.4.2 release has no `tests` directory,
  no `enable_testing()`, no `add_test()`, and no documented automated test
  command. `BUILD_EXAMPLE` builds an interactive demo only.
- Added consumer tests: 1/1. The Conan `test_package` builds and runs
  `test_adwaita_qt`, links `AdwaitaQt6::adwaitaqt6`, starts Qt with the
  offscreen QPA backend, discovers the packaged style plugin via
  `QT_PLUGIN_PATH`, creates the Adwaita style, and checks non-visual
  palette/metric behavior with 8 internal assertions.

## W3 Result

- Device: `10.62.215.229:2222`.
- Run root: `/storage/Users/currentUser/codex-tasks/adwaita-qt-1.4.2-task837-807f-20260810-234006`.
- Runner PID: 24479.
- Started UTC: `2026-08-10T15:45:24Z`.
- Finished UTC: `2026-08-10T15:48:34Z`.
- Result: PASS, exit 0.
- Execution base: `807fa2c350480cb15271d1891f23b2b991916fd5`.
- Frozen W3 input tree: `65f48cc47db8e3cb49a78aa2d555abf3a8349460`.
- Candidate input SHA-256: `e7aa22e1846170274dc08688679eed5864f63be11d5468bf8163c70821017850`.
- Launch bundle SHA-256: `fc4bc1ca24216cbc6209934fdb5b9cc7fa0022ccb9686168355f067c1460e9fb`.
- Source archive SHA-256: `cd5fd71c46271d70c08ad44562e57c34e787d6a8650071db115910999a335ba8`.
- Evidence bundle SHA-256: `6a909a5fa8457d0fcf95cec44ab9b6eb8b18055f101b07ce2e2b196cdb02de2c`.

The W3 runner verified the frozen archive and source cache, structure gate,
OHOS macro gate, published `qtbase/6.11.1` dependency, `conan create`, artifact
discovery, installed ELF SONAME/DT_NEEDED metadata, and the consumer test.

## Frozen Input And Post-run Results

The W3 evidence is bound to the frozen input tree above. The recipe inputs
(`conanfile.py`, `conandata.yml`, `patches/`, and `test_package/`) remain
byte-identical after the run. Completion totals and device evidence are recorded
only in post-run result surfaces (`manifest.yaml`, `notes.md`, and `reports/`),
as required by the frozen-candidate input contract. These result files are not
execution inputs and are not used to splice evidence from another run or device.

## Release Readback

- Root-bound process count: 0.
- Task lock: absent.
- Task lease: absent.
- Device release: confirmed.
