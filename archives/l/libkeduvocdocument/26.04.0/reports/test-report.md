# libkeduvocdocument 26.04.0 verification report

## Environment

- OpenHarmony / HarmonyOS PC aarch64 real device (os.version 6.0)
- Clang 15.0.4 (OHOS SDK 26.0.0.18), libc++, cppstd=17
- Conan 2.29.1 (OHOS adapted), remote `ohpcd`, profile `ci/conan/profiles/ohos-aarch64`
- QPA platform: offscreen（sandboxed HOME/TMPDIR/XDG）

## Verification

| 命令 | 退出码 | 结果 |
|---|---|---|
| `conan create archives/l/libkeduvocdocument/26.04.0 -pr:h/-pr:b=ohos-aarch64 -r=ohpcd --build="libkeduvocdocument/*"` | 0 | 补丁应用 → configure → build → 上游测试 → 打包 → test_package 全通过 |
| `ohc-run.py conan-verify libkeduvocdocument 26.04.0` | 0 | G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS（L2/L4/L5 因工具未定位包 ID 跳过） |
| `JUNK_PR_DIFF=<pr.diff> zsh ci/conan/build_and_test.sh` | 0 | JC pass / L0 pass / L1 pass / L2 skip(no bin) / L4 warn / L5 pass；Pass rate 100% |
| `ohc-run.py finish libkeduvocdocument 26.04.0 published` | 1（非阻塞项） | Step5 W3 本地 CI 模拟 **PASS**；G0 clean-verify 因工具按 autotools 调 `./configure` 而误报失败（见下） |

CI 日志：`reports/w3-local-ci.log`、`reports/conan-create.log`、`reports/conan-verify-report.md`。

## 上游测试（真实执行，逐项）

测试命令：`ctest --test-dir <build> --output-on-failure --no-tests=error`

| # | 用例 | 注册来源 | 结果 | 耗时 |
|---|---|---|---|---|
| 1 | `keduvocdocumenttest.cpp` | `autotests/CMakeLists.txt:43`（`ecm_add_test`，非 GUI） | Passed | 0.07s |
| 2 | `emptydocumenttest.cpp` | 同上 | Passed | 0.06s |
| 3 | `keduvoctexttest.cpp` | 同上 | Passed | 0.07s |
| 4 | `readerkvtml2test.cpp` | `autotests/CMakeLists.txt:61`（`ecm_add_test` GUI，static） | Passed | 0.09s |
| 5 | `readerwordquiztest.cpp` | 同上 | Passed | 0.08s |
| 6 | `readerpaukertest.cpp` | 同上 | Passed | 0.07s |
| 7 | `readervokabelntest.cpp` | 同上 | Passed | 0.08s |
| 8 | `readerxdxftest.cpp` | 同上 | Passed | 0.07s |

**ctest：总数 8 / 通过 8 / 失败 0 / 跳过 0**

**用例级口径**：8 个 QTest 程序内部共 **23 个用例**（`<binary> -functions` 实测：keduvocdocumenttest 2、emptydocumenttest 1、keduvoctexttest 2、readerkvtml2test 10、readerwordquiztest 2、readerpaukertest 2、readervokabelntest 2、readerxdxftest 2），全部通过，0 跳过。

上游另有两个测试程序（`keduvocdocument/tests/`），上游只用 `ecm_mark_as_test()`
（ECM 实现仅设 `EXCLUDE_FROM_ALL`，不 `add_test`）故未被 ctest 注册，配方在 `build()` 中显式运行：

| # | 程序 | 调用 | 结果 |
|---|---|---|---|
| 9 | `sharedkvtmlfilestest` | `<build>/bin/sharedkvtmlfilestest` | exit 0 |
| 10 | `converter` | `<build>/bin/converter <src>/keduvocdocument/kvtml_empty_sample.kvtml <out>.kvtml` | exit 0；输出 1488 字节 KVTML2，断言 `<kvtml version="2.0">` 与 `<identifier` 存在 |

**上游合计：总数 10 / 通过 10 / 失败 0 / 跳过 0**（测试程序口径：8 个 ctest 注册程序 + 2 个未注册程序；用例级口径为 23 个 QTest 用例 + 2 个程序，全部通过）

> 说明：`converter` 的 `-f/--format` 在上游被误定义为无值 flag，按 `converter <in> <out>` 调用；
> `docs/basic_vocabulary_en2de.kvtml` 为过期样例（reader 报 `missing identifier elements`），
> round-trip 使用 `kvtml_empty_sample.kvtml`。

## test_package

链接安装后的 `libKEduVocDocument.so.5` 与 `libkeduvocdocument` 头文件，构造含 2 个 identifier、
1 条 entry（2 个 translation）的文档，`saveAs(Kvtml)` → `open()` 回读比对，并做产物结构检查。

- 断言数：18
- 通过：18
- 失败：0
- 跳过：0

包含的 HarmonyOS 专项用例（≥1）：

| 用例 | 检查 | 结果 |
|---|---|---|
| `dt_soname_stamped` | `llvm-readelf -d <pkg>/lib/libKEduVocDocument.so.5.1.0` → `DT_SONAME == libKEduVocDocument.so.5` | PASS |
| `no_absolute_needed_leak` | 同一产物 9 条 DT_NEEDED 全部为 basename，无 Conan 缓存绝对路径（E537） | PASS |

## 已知非阻塞项

1. **G0 clean-verify 误报**：该步骤对 CMake 工程仍执行 `./configure`，日志
   `bash: ./configure: No such file or directory`（exit 127）；同时伴随 OHOS 已知的
   `getcwd: cannot access parent directories`。属工具链限制，非本包缺陷；`conan create`
   与 W3 已独立完成干净构建验证。
2. **L4 warn**：`ci/conan/build_and_test.sh` 的补丁危险函数正则为
   `(strcpy|sprintf|gets|strcat)\b`，命中了补丁文本中单词 "Tar**gets**" 的子串（误报）。
   补丁不含任何危险函数调用。
3. **W3 full 模式 JC 失败（外部因素）**：`origin/main` 中已跟踪 3 个未登记的隐藏文件
   （`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
   `archives/k/kics/2.1.20/.staging-verified`，另一批任务的产物），使全仓扫描模式 JC 失败。
   按 PR diff 范围检查（与 CI 真实口径一致）本包 **0 junk、1 个软件包**，通过。
4. **finish Step6/7/8 警告**：均为仓级既有状态（知识图谱 E219/E253/E305 字段空缺、
   1331 个历史草稿待审、`gen_summary` 内部错误），与本包无关。

## 结果

在 OpenHarmony aarch64 真机完成真实构建与测试：上游 10/10、test_package 18/18、
conan-verify 全门禁 PASS、W3 本地 CI 模拟 PASS。包可标记 `published`（制品仓上传由合并后的
release 流水线执行，本阶段停在 PR 前）。
