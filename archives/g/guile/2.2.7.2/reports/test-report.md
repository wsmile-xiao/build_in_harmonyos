# Guile 2.2.7.2 真机测试报告

- 日期：2026-09-26
- 环境：HarmonyOS PC aarch64，OHOS 6.0 Conan profile，Clang 15，Conan 2.29.1（OHOS 适配版）
- 命令：`conan create archives/g/guile/2.2.7.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 '--build=guile/*'`，退出码 0
- 仓库门禁：`python3 scripts/ohc-run.py conan-verify guile 2.2.7.2`，G0–G4、L2、L4、L5 全部通过；PC 本地报告为 `reports/conan-verify-report.md`

## 上游 Automake 测试

| 测试组 | 通过 | 失败 |
| --- | ---: | ---: |
| standalone 稳定子集 | 36 | 0 |
| VM | 20 | 0 |
| LALR | 19 | 0 |
| 合计 | 75 | 0 |

`conan-verify` 的 `reports/conan-create.log` 分别记录了 `All 36 tests passed`、`All 20 tests passed` 和 `All 19 tests passed`。

## 上游 Scheme 测试

`test-suite/tests/` 的 174 个 `.test` 文件全部进入四段测试。下表按 Guile 测试驱动报告的断言结果计数：

| 分段 | 文件数 | PASS | FAIL | XFAIL | UNRESOLVED | UNTESTED | UNSUPPORTED | ERROR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 48 | 2,711 | 0 | 4 | 61 | 0 | 33 | 0 |
| 2 | 48 | 31,214 | 0 | 3 | 6 | 0 | 11 | 0 |
| 3 | 62 | 7,111 | 0 | 2 | 518 | 1 | 21 | 0 |
| 4 | 16 | 756 | 0 | 1 | 9 | 0 | 0 | 0 |
| 合计 | 174 | 41,792 | 0 | 10 | 594 | 1 | 65 | 0 |

| 汇总项 | 数量 |
| --- | ---: |
| 总测试数（Scheme 断言） | 42462 |
| 通过 PASS | 41792 |
| 预期偏差 XFAIL | 10 |
| 未解决 UNRESOLVED | 594 |
| 未测试 UNTESTED | 1 |
| 不支持 UNSUPPORTED | 65 |
| 失败 FAIL | 0 |
| 错误 ERROR | 0 |

这 594 个 UNRESOLVED 保持原分类，**未计入 PASS**。四段汇总与上一适配版 `.1` 的记录相同；已有 OHOS 测试适配涉及文件系统权限、AF_UNIX、locale/iconv、FFI 回调和信号相关边界。报告只确认本次配方构建的测试结果，不把这些边界视为已修复。

## 消费者测试

`test_package` 完成编译与链接，并实际运行七项检查：`guile --version`、Scheme 算式求值、`guild --version`、`guile-config --version`、`guile-config compile`、`guile-config link`、C API `./test_probe`。七项均退出码 0；探针输出 `guile test: (+ 1 2) = 3` 和 `guile test: PASS`。新配方让任一消费者命令失败向 Conan 传播，修复上一版吞掉运行异常的假阳性。

## 已知限制与后续门禁

- 稳定 standalone 子集未纳入旧版已确认在 OHOS 上崩溃或触发 GC OOM 的 `test-ffi`、`test-loose-ends`、`test-out-of-memory`；上表 75 项不包括这三项。
- 沿用 `.1` 的 `GUILE_TEST_OHOS` 测试补丁会将已确认的平台边界条件记为 `UNSUPPORTED` 或 `UNRESOLVED`，涉及只读 `/tmp`、AF_UNIX 权限、locale/iconv、FFI callback、interval timer 和 profiler。`0 FAIL` 不表示这些断言已通过；本版只修正 `sandbox.test` 的补丁上下文，不改变这些既有分类。
- 主配方沿用 `.1` 的 `make -k` 容错与默认 `shared=True` 构建；本报告不声称所有非核心目标或 `shared=False` 配置已验证。
- 运行时打印 Boehm GC 的 `PT_GNU_RELRO` warning；本轮命令与探针仍通过。打包过程对 `.pc` 文件的 `exec_prefix=/` 替换未匹配，Conan 给出 warning；需据包内文件判断是否要调整。
- 打包进 `lib/guile/2.2/ccache` 的 `.go`（Scheme 字节码）取自上游源码 tarball 的 `prebuilt/64-bit-little-endian/` 目录，并非本机编译：真机上 `guild compile` 生成 `.go` 时触发 SIGTRAP（Signal 5，与既有 GC/平台边界相关），配方 `build()` 以 `make -k` 容错（`.so` 与二进制先于 `.go` 目标编译成功），`package()` 复制上游预生成字节码（conanfile.py 已在 docstring 声明）。该产物与上游官方发布物同源；`guile` 运行时加载正常（消费者测试与上表 41,792 项 PASS 即在其上运行）。SIGTRAP 根因待后续版本跟进，不视为已修复。
- `finish ... built` 内的 W3 本地 CI 已在鸿蒙 PC 真机通过，`setup.sh` 与 `build_and_test.sh` 均成功，目标包被强制重新构建并测试。W3 完整输出留在本机 `reports/w3-local-ci.log`；正式 PR CI 仍须在提交流程中运行。

本报告数据来自鸿蒙 PC 上的 `conan create` 和 `archives/g/guile/2.2.7.2/reports/conan-create.log`；日志留在真机工作区，不把运行缓存或大体积日志加入源码 PR。
