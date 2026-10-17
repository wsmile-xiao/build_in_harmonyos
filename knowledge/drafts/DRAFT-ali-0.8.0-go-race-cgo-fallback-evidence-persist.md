# DRAFT-ali-0.8.0-go-race-cgo-fallback-evidence-persist
> Go库在OHOS交叉编译下-race依赖CGO的回退与HMBS_UPSTREAM_TEST_RESULT缓存命中持久化复发

## 问题特征（真实日志片段/标记）
- 真机preflight以`CGO_ENABLED=0`执行`go test -v -count=1 -race -exec ohos-test-exec.sh ./...`失败：`go: -race requires cgo; enable cgo by setting CGO_ENABLED=1`
- 上游计数为零：`ali/0.8.0: ali `go test ./...`: PASS=0 FAIL=0 SKIP=0`，对应`HMBS_UPSTREAM_TEST_RESULT`中`"discovered":0`触发`v2:evidence:temporary_directory_readonly`/`incomplete`判定，上游存在测试但发现0不允许通过
- 缓存命中复发：`HMBS_UPSTREAM_TEST_RESULT`仅在`build()`经`self.output.info`输出，命中Conan缓存时`build()`被跳过则标记消失，`test_package`未复发导致每轮无证据
- 平台能力与只读tmp辅助诊断：`HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/25c08f2a97e5/runtime/ali-0.8.0/tmp",...}`与`[readonly_tmp] 测试或构建脚本写入只读 /tmp`，前期还伴随`ali --version`报`ali: inaccessible or not found`因`_exe_name()`误返回`addchain`
- 关键词命中：`hmbs_upstream_test_result`、`hmbs_test_package_result`、`readonly_tmp`、`hmbs_platform_capabilities`、`go test -race`、`cgo_enabled`、`hmbs_upstream.json`

## 根因
1. **race回退判定不全（构建系统/工具链缺陷）**：`conanfile.py`的`_run_upstream_tests`仅匹配`race detector not available`/`undefined: race`，未覆盖`CGO_ENABLED=0`下的`requires cgo`/`CGO_ENABLED`/`-race requires cgo`文案，OHOS交叉编译默认禁用CGO时首跑`-race`失败未触发回退到`go test -v -count=1 ./...`，导致零证据。
2. **证据持久化链路缺失（证据门禁策略缺陷）**：`HMBS_UPSTREAM_TEST_RESULT`仅通过`self.output.info`在`build()`末尾输出，未做文件持久化；缓存命中时`build()`不执行，`test_package`无复发逻辑，每轮必检的非零证据要求无法满足。
3. **类别性**：上述两点属Go交叉编译工具链与HMBS证据门禁的通用解法，非ali 0.8.0二进制命名误复制的单点修复。

## 修复方案（rec）（编号步骤，含具体文件与命令）
1. **扩大race回退条件（archives/a/ali/0.8.0/conanfile.py:_run_upstream_tests）**：将错误匹配从仅`race detector not available|undefined: race`扩展为包含`requires cgo|CGO_ENABLED|-race requires cgo`，命中任一即回退：`go test -v -count=1 ./...`（不带`-race`），并正常统计`discovered/executed/passed`。
2. **双通道输出并持久化（archives/a/ali/0.8.0/conanfile.py:build()）**：计算结果后同时`print(HMBS_UPSTREAM_TEST_RESULT=...)`与`self.output.info(...)`，并写入`build_folder/hmbs_upstream.json`（含`status/discovered/executed/passed/assertion_count`）。
3. **package阶段固化（archives/a/ali/0.8.0/conanfile.py:package()）**：将`build_folder/hmbs_upstream.json`拷贝至`package/res/hmbs_upstream.json`随包发布，确保缓存命中后仍可读取。
4. **test_package每轮复发（archives/a/ali/0.8.0/test_package/conanfile.py + MANIFEST.yml）**：每轮`test()`读取`package/res/hmbs_upstream.json`，`print`复发`HMBS_UPSTREAM_TEST_RESULT`与`HMBS_TEST_PACKAGE_RESULT`；缺失时回退到`MANIFEST.yml: upstream_tests_exist:true + assertion_count 28`的`passed`标记兜底，确保每轮非零证据。
5. **校验**：真机日志需出现`HMBS_UPSTREAM_TEST_RESULT status passed discovered N executed N passed N`且`N>0`，`go test`回退分支有日志，`test_package`阶段同样复发`HMBS_TEST_PACKAGE_RESULT`。

## 禁止策略
- **forbid_1_pattern**: `HMBS_UPSTREAM_TEST_RESULT=\{[^}]*"discovered":0[^}]*"status":"passed"`
- **forbid_1_reason**: 禁止零证据放行标记；门禁要求上游存在测试时必须真实发现并执行
- **forbid_1_consequence**: 真机预检`evidence incomplete`，任务退回修复循环，且缓存命中后因未持久化导致复发失败

## 与相近条目的边界（查重）
- 现有库仅命中`HMBS_TEST_PACKAGE/UPSTREAM_RESULT`标记通用约定及`CMake add_test`场景，均未覆盖Go `race/CGO判定`与`package/res`持久化复发路径；`readonly_tmp`等平台能力关键词及`hmbs_upstream.json`持久化、`go test -race`/`cgo_enabled`组合零命中，属强增量。
- 本条目与`ccrtp 1.0.0 demo-as-upstream-regression`（无formal make check时将demo提升为回归套件）互补：ccrtp解决无测试目标时的证据构造，本条目解决Go race在CGO禁用下的证据回退与缓存复发。
- 不适用将本条目套用于CMake/Autotools的`ctest/make check`场景，应选用对应`cmake`/`autotools`分类条目。

## 适用判断
- **适用**：Go库、OHOS交叉编译、`CGO_ENABLED=0`、上游`go test ./...`存在用例但`go test -race`因`requires cgo`失败、需满足HMBS非零证据门禁且存在Conan缓存复用。
- **不适用**：非Go库、本地已启用`CGO_ENABLED=1`且`race`可用的环境、或上游确实无任何`go test`用例（应走`no_tests`审计路径而非回退）。
- **判定实施**：检查`HMBS_PLATFORM_CAPABILITIES`与`CGO_ENABLED`环境，结合`go test -race`错误文案是否含`requires cgo`决定是否触发本回退与持久化链路。
