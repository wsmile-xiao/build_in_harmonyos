# Test Report — robodoc 4.99.44

## Build Information
- Software: robodoc 4.99.44
- Build system: autotools
- Compiler: clang 15.0.4 (target aarch64-unknown-linux-ohos)
- Platform: HarmonyOS (HongMeng Kernel 1.12.0) aarch64
- Date: 2026-09-27

## Build Result

- ✅ configure: PASS
- ✅ make: PASS（2 个非阻塞告警：analyser.c 多余括号相等判断、troff_generator.c 非字面量格式串）
- ✅ make install: PASS（bin/robodoc、bin/robohdrs、share/man/man1/{robodoc,robohdrs}.1、share/doc/robodoc/*）
- ✅ conan create（含 test_package）：PASS

## Upstream Test Suite

上游**没有可执行的自动化测试套件**。清点与实跑证据见 `../notes.md`
「上游测试入口清点」与 `../test_package/MANIFEST.yml`。

```
$ make check
Making check in Source
make[1]: Nothing to be done for 'check'.
Making check in Docs
make[1]: Nothing to be done for 'check'.
...
rc=0（无任何用例运行：Makefile.am 无 TESTS/check_PROGRAMS/check-local）
```

真实测试入口核验：上游 git tag 的 `Test/` 目录仅含非自动化脚本
（`test_build.sh` 硬编码 4.99.43 tarball 不可运行；`generate_testcase.py` 只生成数据；
`Test/*/makefile` 为空；`Source/unittest.c` 不被 makefile 引用且含语法错误），
且 `Test/` 未随官方发布包分发。

## test_package Results（消费者视角 + 鸿蒙特有）

执行方式：`conan create ... `（test_package/test() 调用两个脚本）。
日志：`conan-create.log`。

### test.sh（消费者冒烟，3 断言）

| 用例 | 说明 | 结果 |
|------|------|------|
| robodoc --version | 输出 `4.99.44` | ✅ PASS |
| robodoc --help | 版本横幅 `ROBODoc Version 4.99.44` | ✅ PASS |
| robohdrs | 输出 `robodoc header insertor` 横幅 | ✅ PASS |

### ohos_specific_test.sh（鸿蒙特有，7 断言）

| # | 用例 | 说明 | 结果 |
|---|------|------|------|
| 1a | AArch64 ELF | `readelf -h` 显示 Machine: AArch64 | ✅ PASS |
| 1b | OHOS loader | `file` 显示 `ld-musl-aarch64.so.1`（OHOS musl 动态加载器） | ✅ PASS |
| 2a | robodoc --config | 退出码 0 | ✅ PASS |
| 2b | 平台三元组 | `Compiled for aarch64-unknown-linux-ohos`（config.guess/sub 适配生效） | ✅ PASS |
| 3a | HTML 抽取 | `--multidoc --html` 退出码 0 | ✅ PASS |
| 3b | HTML 内容 | 生成 HTML 含被抽取条目名 `ohos_probe/robodoc_ohos_probe` | ✅ PASS |
| 3c | HTML 源码体 | 生成 HTML 含源码体 `return 42;` | ✅ PASS |
| 4a | ASCII 抽取 | `--singledoc --ascii` 退出码 0 | ✅ PASS |
| 4b | ASCII 内容 | 输出含文档文本 `robodoc_ohos_probe -- HarmonyOS adaptation probe` | ✅ PASS |
| 5 | robohdrs | 伴随工具可运行并输出横幅 | ✅ PASS |

## Summary

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| test_package 总计 | 10 | 100% |
| 通过 (PASS) | 10 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

## Conan Verification (G0–G4 + L2/L4/L5)

- G0 预构建风险评估: PASS
- G1 配方完整性: PASS
- G2 conan create（干净源码构建 + test_package）: PASS
- G3 系统同名库隔离 (R26): PASS
- G4 产物完整性: PASS
- L2/L4/L5 smoke 可执行 / 静态安全 / 产物基线: 见 `conan-verify-report.md`

## Known Limitations

1. `robohdrs` 的 `--version`/`-h` 选项不被支持（无参或 `-x` 等选项会打印用法到 stderr 并以非 0 退出）；
   本测试仅校验其可运行与横幅输出。
2. 上游文档生成器中的若干生成器（RTF/LaTeX/troff/DocBook XML）本次未纳入自动断言，
   仅 HTML 与 ASCII 做了内容级校验。
