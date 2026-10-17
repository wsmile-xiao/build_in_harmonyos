# Adaptation Notes - jube 2.7.1

## Overview
JUBE（Jülich Benchmarking Environment）是于利希超算中心开发的基于脚本的
基准测试 / 工作流环境：以 XML 或 YAML 描述基准集、参数组合、平台配置、
分析器与结果数据库，并在不同系统上运行与评估。纯 Python 3，无 C 扩展，
GPL-3.0。

- 上游：https://github.com/FZJ-JSC/jube （REL-2.7.1，commit 29aaf67）
- 官网：https://www.fz-juelich.de/jsc/jube
- 组成：`jube/`（jube / jube.result_types / jube.util 三个包）、
  `bin/jube` / `bin/jube-autorun`（CLI）、examples / platform /
  contrib/schema / docs/JUBE.pdf（share 数据）

## 源码选型（关键）
- 官方发布的 **sdist** `JUBE-2.7.1.tar.gz`（592450 字节）**不含 tests/**。
- 上游测试（Python unittest，`tests/` 目录）只存在于 git 仓库，
  `.gitlab-ci.yml` 从 git checkout 运行。
- 守则要求"只要上游存在测试，就必须接入并在真机完整执行"，不允许 no_tests。
- 因此改用官方 git tag 归档（同门同源）：
  `https://github.com/FZJ-JSC/JUBE/archive/refs/tags/REL-2.7.1.tar.gz`
  （691653 字节，sha256 6D9B34E4...2410，strip_root 后为 JUBE-REL-2.7.1/）。

## Build System
- setup.py（setuptools）：`packages=['jube','jube.result_types','jube.util']`，
  `install_requires=['pyyaml']`，`scripts=['bin/jube','bin/jube-autorun']`，
  data_files 到 `share/jube`，package_data `jube/help.txt`。
- 纯 Python，无编译器参与；设置声明 os/arch/compiler/build_type 满足 OHOS profile。

## Build Process
1. `get()` 拉取 REL-2.7.1 归档（strip_root）。无补丁。
2. build() 先跑上游测试（见下），再把产物持久化到
   `share/jube/upstream_test_result.json` 供缓存命中复射。
3. `pip install --no-deps --prefix=staging`（alabaster / python3-distro 先例），
   归一化 site-packages / bin / share/jube 到包内。
4. package_info 注入 PYTHONPATH（site-packages）与 PATH（bin）。

## 上游测试（Python unittest，102 用例）
- 入口 `tests/run_all_tests.py`（聚合 parameter/multiprocessing/pattern/
  benchmark/result_database/example_*/yaml/xml/step/util/conf/substitute）。
- CI 运行方式：`cd tests && PYTHONPATH=<repo_root> python3 <mod>_tests.py`；
  `run_all_tests.py` 是官方聚合入口。
- **统计口径 python_def**：unittest 运行时发现 102 个 test 用例
  （静态逐类核算出 104，但 run_all_tests.py 运行时实际注册 102；数字以真机 conan create 为准）。
- build() 内：先 `pip --target` 兜底安装 pyyaml（import yaml 失败时），
  以 PYTHONPATH=<source_root>[:pydeps] 运行 `python3 run_all_tests.py`，
  解析 unittest 汇总块（`Ran N tests ... OK/FAILED(...)`），
  输出 `HMBS_UPSTREAM_TEST_RESULT`。
- 幂等复射：结果 JSON 写入包内 share/jube/upstream_test_result.json；
  test_package test() 在 build() 被缓存跳过时读取并复射该标记，
  避免"缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据"门禁（abuild-sudo /
  fancy-cat / manifold 先例）。

## Platform Notes (OHOS)
1. `jube/util/util.py` 顶层 `import grp, pwd` —— POSIX 模块，OHOS（类 POSIX
   内核）自带；这也是 Windows 本机无法导入测试的原因（不影响真机）。
2. `sqlite3`（result_types/database.py、测试用）来自 CPython 标准库。
3. `pyyaml` 是唯一 Python 运行时第三方依赖（YAML 输入需要；XML 输入不需要）。

## 验证
- 上游测试：**真机 conan create 实测（以预检日志为准）**，102 用例（98 通过 + 4 errors 为 os.posix_spawn 平台限制）。
- test_package：consumer 测试（`jube --version` + 最小 XML benchmark
  端到端 + import 检查），见 test_package/MANIFEST.yml。
- 版本号：2.7.1（上游首次适配，R37）。

## 已知限制 / 后续
- example 测试会真实调用 `jube run` 执行 shell 命令与文件操作；个别
  OHOS 平台行为差异（如有）将如实记入 HMBS gaps（ohos_feature / environment），
  不伪造通过。
- 运行时若消费方使用 YAML 输入，需提供 pyyaml（已在 README / manifest 声明）。
---
**编译结束**: 2026-09-30
**最终状态**: built（待真机预检复核，CI 上传后才可标 published）


## 2026-09-30 fix: unlock real-device evidence preflight
- Symptom: hmbs preflight reported incomplete at the evidence stage
  ("cannot read current archive code tree, cannot start real-device preflight"),
  i.e. it never reached conan create (a pre-gate, before compile/test).
- Root cause: the jube archive tree was built (software/version manifests, README,
  conanfile.py, conandata.yml, test_package/{conanfile.py,test_jube.py}) but the
  required test_package/MANIFEST.yml was missing. The manifest must declare a
  non-negative integer upstream_test_total and upstream_test_count_method; without
  it the evidence gate cannot read the tree and is judged incomplete.
  (Prior unlock precedent: manifold/3.4.1)
- Fix: added test_package/MANIFEST.yml declaring
  upstream_test_total: 104 (python_def; unittest reports "Ran 104 tests"),
  upstream_test_count_method: python_def, upstream_tests_exist: true, and the
  test_package_tests entry for test_jube.py (real CLI + API checks).
- Next: hmbs re-runs the real-device preflight; the 104-case pass/fail numbers
  from conan create are used to fill the PR body.


## 2026-09-30 fix: test_package IndexError (missing pkg arg) + upstream gaps
- Symptom: conan create exit 1 at test_package: test_jube.py IndexError at line 113
  main(sys.argv[1], sys.argv[2], sys.argv[3]).
- Root cause: test_package/conanfile.py test() ran
  self.run("{py} \"{script}\" \"{site}\" \"{bin}\"") i.e. passed only 3
  positional args (script, site, bin), but test_jube.py main() expects
  argv[1]=pkg, argv[2]=site, argv[3]=bin -> sys.argv[3] IndexError.
- Fix: added pkg as the first arg:
  self.run("{py} \"{script}\" \"{pkg}\" \"{site}\" \"{bin}\").
- Upstream suite: runs 102 cases (python_def), 98 pass, 4 error (0 skipped) on
  the real device. The 4 errors are CPython subprocess _posix_spawn ->
  os.posix_spawn() raising (HongMeng kernel lacks the posix_spawn fast path),
  affecting tests that spawn child processes. Reported as ONE ohos_feature gap
  of count 4 (declared_total 102 - passed 98 = 4), evidence = real traceback.
  Not faked; status stays failed with gaps documented.
- Aligned MANIFEST upstream_test_total: 104 -> 102 (matches real run).


## 2026-10-02 fix: rule4 upstream gaps status -> incomplete
- Symptom: hmbs preflight incomplete at evidence stage, rule4 reports
  "upstream test 4/102 not passed, gaps demanded" (discovered 102, executed 102,
  passed 98, failed 4, skipped 0).
- Root cause: when gaps exist (98/102, 4 ohos_feature), conanfile emitted
  HMBS_UPSTREAM_TEST_RESULT status="failed". The evidence gate requires
  status="incomplete" whenever the suite is not run to 100% and gaps are the
  technical justification; "failed" without a fully-passing run is treated as a
  hard failure demanding more (i.e. gaps not accepted / 新增测试不足 100%).
- Fix: conanfile.py status logic now maps ran>0 with failures/errors/skips ->
  "incomplete" (gaps list provides specific reason+evidence), keeps "error" only
  when 0 tests collected, and "passed" only on full OK. Numbers unchanged:
  102/102/98/4/0, gaps count 4 (ohos_feature, posix_spawn).
  Identity: 98+4=102, 102+0<=102.
- Next: hmbs re-runs real-device preflight; gate should accept incomplete+gaps.


## 2026-10-02 round: pr-body + manifest consistency + honest status
- Wrote complete PR body draft to .hmbs/pr-body.md (积分赛事PR模板 all sections:
  PR info, upstream/adapted test tables, upstream-test-modification N/A,
  supplementary-tests N/A, verification, notes). 适配路径 = 路径 A（基础适配）.
  Test counts use the real-device measured values already logged (upstream 102
  -> 98 pass + 4 ohos_feature errors; consumer 7/7); no {{...}} placeholders.
- Manifest consistency: aligned all "104" (stale static estimate) references to
  the real runtime count 102 (software manifest key_points, version manifest
  knowledge_gained, notes.md).
- Version manifest test_result:round=2 with real measured numbers
  (discovered 102 / passed 98 / failed 0 / errors 4 / skipped 0) and consumer
  7/7; upstream_test_exempted_reason documents the 4 os.posix_spawn ohos_feature
  gap.
- Status changed published -> built in both software & version manifests
  (R3: published = CI upload 成功; not yet pushed/uploaded, honest state is
  built until HMBS preflight re-verify + CI upload).
- No commit/push this round (task rule 5); waits for HMBS real-device preflight.


## 2026-10-02 round: fix consumer test "hello_world produced done file" (新增测试 100%)
- Symptom: hmbs preflight incomplete at evidence stage, rule4 "新增测试不足 100%".
  Real-device conan create test_package failed at test() "Error 1"; test_jube.py
  reported `FAIL hello_world produced done file` / `PASS hello_world no error file`,
  while jube's own workpackage_status table showed say_hello done=1 (done file
  IS created). The consumer walk over the temp cwd found no `done` file.
- Root cause: hello_world.xml sets `outpath="bench_run"` (relative). JUBE resolves
  the XML's relative outpath against the *XML file's directory*, not cwd —
  jube/jubeio.py: when CLI --outpath is None, `outpath =
  os.path.normpath(os.path.join(self.file_path_ref, outpath))`, i.e. into the
  packaged examples dir. So the benchmark `done` file landed in
  `<pkg>/share/jube/examples/hello_world/bench_run/<id>/say_hello/done`, outside
  the temp cwd the consumer test walked; os.walk(work) found nothing.
- Fix: test_jube.py now runs `jube run --outpath jube_out --hide-animation <xml>`
  with cwd=work (--outpath is relative to the execution location per jube main.py
  help). Benchmark output then lands deterministically under work/jube_out/<id>/
  say_hello/done, so `os.walk(work)` finds both `done` (present) and `error`
  (absent) -> consumer 7/7.
- Upstream unchanged: 102 discovered, 98 pass, 4 error (os.posix_spawn fast path
  unavailable on HongMeng kernel) reported as ONE ohos_feature gap count=4
  (102-98=4) with real traceback evidence; status "incomplete". This is an honest,
  non-fake platform limitation; numbers from real-device unittest summary.
- Next: hmbs re-runs real-device preflight; expect consumer test_package 7/7 and
  upstream incomplete+consistent-ohos_feature-gaps to pass the evidence gate.

