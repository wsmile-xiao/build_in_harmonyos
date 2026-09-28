# trompeloeil-cpp 49 测试报告

- 日期：2026-09-27　主机：B 机（HarmonyOS PC aarch64）　编译器：OHOS clang 15 / libc++
- 配方：`archives/t/trompeloeil-cpp/49`（header-only，无补丁，无库产物）
- 一手来源件：`reports/w3-local-ci.log`（finish W3 本地 CI，实算 435 行，
  sha256 `ce7cc4156299de7f7a36885c98da7e63022bb590eafd0bcb4f505c58d2f16569`，与 `.ci-result.json.log_sha256` 互证）、
  `reports/conan-create.log`（conan-verify G2 干净构建，实算 152 行，
  sha256 `8d764881ddffd0a614d2e47879698c01ef89428936b830666b8afea7fc93a731`）；逐条行号见 notes.md 的读数表

## 一、摘要（五维）

| 维度 | 数值 |
|:--:|:--|
| 静态总数 | 上游 0 个 ctest 注册；3 个自测可执行目标 + 68 个 expect-to-fail 编译单元；测试源码 14,736 行 |
| 可执行数 | self_test×2 标准（运行时用例 604 + 615 = 1219）+ 独立程序 2 + 负向用例 50（C++14）/68（C++20）+ 消费者 4 用例 |
| 实测通过 | 1361 断言/604 用例（C++14）、1394 断言/615 用例（C++20）、2/2、50/50、68/68、消费者 5 断言/4 用例 |
| 跳过 | 18（上游 `// exception:` 规则在 C++14 轮排除，非本包裁剪） |
| 失败 | 0 |

## 二、结论

**PASS**（本地）——上游官方测试套件在 OHOS aarch64 上**零补丁、零用例修改**全部通过，
含 C++20 协程 mock；68 个负向编译用例诊断文本零漂移；消费者测试真编译真运行
（`MAKE_MOCK0/1` + `REQUIRE_CALL` + `RETURN`/`TIMES`/`LR_SIDE_EFFECT`/`gt()` +
`expectation_violation` 断言）。

## 三、限制与披露

1. 上游 `test/CMakeLists.txt` 找不到 Catch2 会构建期 `file(DOWNLOAD)` 抓 `catch.hpp`；
   配方以 `tool_requires catch2/3.8.1` + `CMAKE_PREFIX_PATH` 预置消除联网。
2. 上游 `check_errors.sh` 依赖 GNU `parallel`（OHOS 无），配方用线程池驱动同一个
   `verify_compilation_error.sh`，判定语义与上游 `FAILURES=... | grep FAIL | wc -l` 等价。
3. `verify_compilation_error.sh` 的 `mktemp` 需 `TMPDIR` 指向可写目录（OHOS `/tmp` 只读）。
4. CMake 提示 `System is unknown to cmake, create: Platform/HarmonyOS`、HMDFS jobserver
   `mkfifo` 受限告警均为良性，不影响构建与运行。
5. **`conandata.yml` 声明的 `github.com` 主机名在 B 机不可直连**（2026-09-27 复测：
   `-I` 20s 超时、`-L -m 65` 得 `http=000`、`git clone` 连不上 443；逐字读数与
   行号见 notes.md「源码与哈希」节引用的 `~/tmp/uc2/z74-trompeloeil/probe-output.txt`）；
   `codeload/raw/api` 三条子域本轮实测可达，本轮 W3 源码仍经 harness 临时镜像取得 ⇒
   CI 侧可达性未由本窗证明，本地绿不代表 CI 绿。
6. 上游 `compilation_errors` 的 C++14 轮排除 18 例由上游规则决定（本窗未增删用例）。

## 四、W3 门禁与证据锚点（W4-01 改名后重跑，值由脚本从盘上重算）

- 本包 CMake 导出名已让给已合入的 `trompeloeil/49`：`cmake_file_name =
  trompeloeil-cpp`、`cmake_target_name = trompeloeil-cpp::trompeloeil-cpp`，
  未用 `cmake_target_aliases` 复原上游名（理由与实物佐证见 notes.md 同名节）。
- `.ci-result.json`：`exit_code=0`、`step=W3_local_ci`、
  `integrity_hash=186d57017ea6c08c`、`log_sha256=ce7cc4156299de7f7a36885c98da7e63022bb590eafd0bcb4f505c58d2f16569`、`timestamp=2026-09-27T03:20:48.937404`；
  失败步骤：无。
- `sha256sum reports/w3-local-ci.log` = `ce7cc4156299de7f7a36885c98da7e63022bb590eafd0bcb4f505c58d2f16569`（与上面的 `log_sha256` 逐字相等）；
  `sha256sum reports/conan-create.log` = `8d764881ddffd0a614d2e47879698c01ef89428936b830666b8afea7fc93a731`（152 行）。
- 探针输出件：`~/tmp/uc2/z74-trompeloeil/probe-output.txt`（网络复测 + 两棵树真 diff）、
  `probe-s8-output.txt`（tag 形态 / 404 / 三次取档同 sha）、
  `lsremote-mirror.txt`（50 条 tag ref，无裸 `49`）、`lsremote-direct.txt`（0 字节）。
