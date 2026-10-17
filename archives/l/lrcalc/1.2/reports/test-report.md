# lrcalc 1.2 测试报告（HarmonyOS PC / OHOS aarch64）

- 日期: 2026-09-18
- 软件: lrcalc 1.2（Littlewood-Richardson calculator）
- 构建系统: autotools
- 工具链: OHOS SDK 26.0.0.18 clang 15.0.4 / armv8 / Release
- 验证入口: `conan create archives/l/lrcalc/1.2 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device`
- 证据日志: `reports/conan-create.log`、`reports/conan-verify-report.md`

## 1. 上游测试用例对比（R51）

| 项 | 上游（原版源码） | 适配后（OHOS aarch64） |
| --- | --- | --- |
| 测试入口 | `make check`（`Makefile.am`: `TESTS = testsuite`） | 同一入口，build() 内原样执行 |
| 注册测试数 | 1（`testsuite`） | 1（未增删） |
| 内部检查数 | 8 | 8 |
| 通过数 | —（Linux 基线） | **8/8** |
| 上游用例修改 | — | **无** |

`testsuite` 的 8 项检查（逐字节比对 CLI 输出）：
1. `lrcalc lrcoef 3 2 1 - 2 1 - 2 1` → `2`
2. `lrcalc skew 3 2 1 / 2 1` → 3 行
3. `lrcalc skew -r 2 3 2 1 / 2 1` → 2 行
4. `lrcalc mult 2 1 - 2 1` → 7 行
5. `lrcalc mult -f 3,2 3 2 1 - 3 2 1` → 2 行
6. `lrcalc mult -q 3,2 3 2 1 - 3 2 1` → 2 行
7. `lrcalc coprod 3 2 1` → 13 行
8. `schubmult 1 3 2 - 1 3 2` → 2 行

conan create 实测：`PASS: testsuite`（1 test passed，内部 8/8 全部 ok）。

## 2. 补全测试用例（test_package，消费者视角）

上游无 `test_package`，按仓库规范补全（CI 自动执行）：

| 用例 | 内容 | 结果 |
| --- | --- | --- |
| `test.c`（C 消费者） | CMakeDeps `find_package(lrcalc)` + 链接 `lrcalc::lrcalc`；用导出 API `v_new_init`/`lrcoef` 断言 3 个 Littlewood-Richardson 系数（`c^{321}_{21,21}=2`、`c^{321}_{3,21}=1`、`c^{4321}_{32,21}=0`） | **3/3 通过**（ctest `lrcalc_api` Passed） |
| `test_lrcalc.sh`（CLI 消费者） | 运行打包的 `lrcalc`/`schubmult`，比对 4 个上游 README 示例输出（coef/skew/mult -q/schubmult） | **4/4 通过** |

两类用例都实质依赖被适配包（库链接 + 二进制执行），可被 CI L1e 破坏性反向验证（移除 bin/lib/include 后测试必失败）。

在 OHOS 设备上曾验证发布包二进制（staged 前缀）可直接运行：

```
$ lrcalc coef 3 2 1 - 2 1 - 2 1
2
$ schubmult 1 3 2 - 1 3 2
1  (1, 4, 2, 3)
1  (2, 3, 1)
```

## 3. 配方门禁结果（conan-verify G0–G4）

| 门禁 | 内容 | 结果 |
| --- | --- | --- |
| G0 | 预构建风险评估（知识图谱） | PASS |
| G1 | 配方完整性 | PASS |
| G2 | 干净 `conan create`（含 build + 上游测试 + test_package） | **PASS** |
| G3 | 系统同名库隔离（R26） | PASS（非系统同名库，shared 常规） |
| G4 | 产物完整性（bin/lib/include） | PASS |
| L2 | 平台功能矩阵 smoke（--version/--help） | skip（lrcalc/schubmult 不提供 --version/--help，参数错误时打印 usage 并退出 1；非阻塞） |
| L4 | 静态安全检查（补丁文本扫描） | warn（正则含 `gets`，误命中 config.guess 中的单词 "targets"；已知非阻塞误报，补丁本身仅含 printf/echo 模板） |
| L5 | 产物基线对比 | PASS（bin/ 有内容） |

本地 CI 门禁（`ci/conan/build_and_test.sh`，与平台 CI 同一脚本）实测：
`L0 pass / L1 pass（上游测试 + test_package 均被验证执行）/ L1e 破坏性反向验证通过 / L5 pass`；
`L2 skip、L4 warn` 均为上述非阻塞项。

结论：**配方验证通过（Verdict: PASS）**。

## 4. 适配补丁与平台差异

| 补丁 | 目的 | 类别 |
| --- | --- | --- |
| 0001-config.guess.patch | 识别 `uname -s=HarmonyOS` → `aarch64-unknown-linux-ohos`（native 构建的 build type 推断） | portability |
| 0002-config.sub.patch | 接受 `linux-ohos*` OS token（POSIX 修复，无平台宏） | portability |
| 0003-configure.patch | configure 临时目录 `umask 077`→`022`（HMDFS setgid 目录不可写，E011/E129） | portability |

另在 `conanfile.py` 内处理：HMDFS 下 harmonybrew bash 作为 SHELL 会损坏 libtool/config.status（E386 同族）→ configure 显式 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`；`make -j1` 规避 HMDFS jobserver FIFO 限制。

## 5. 结论

- 编译状态: **成功**（conan create 全流程通过）
- 上游测试: **8/8 通过，未修改用例**
- 补全测试: **7 项断言全部通过**
- 适配后二进制与上游语义一致（README 示例逐字节比对）
