# 测试报告 — tinyxxd 1.3.16

> **项目**: tinyxxd 1.3.16（命令行工具）
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64, OHOS clang
> **测试类型**: 上游自包含用例复现 + 消费者功能测试

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游复现用例 | 16 | 100% |
| 通过 (PASS) | 16 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 消费者断言 | 18 | 100% |
| 消费者检查通过 | 18 | 100% |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 上游自包含用例（16/16）

| 来源 | 用例 | 结果 |
|------|------|------|
| `make test` | `-h` 输出到 stdout | ✅ |
| `make test` | 非法参数输出到 stderr | ✅ |
| `testfiles/test13.sh` | `-i -b` 二进制 C include | ✅ |
| `testfiles/test14.sh` | `-e -c6` / `-e -c9` | ✅ |
| `testfiles/test15.sh` | `-i` 从 stdin | ✅ |
| `testfiles/test_c0.sh` | `-c 0` 的 7 种行为 | ✅ |
| `make test` | little-endian padding | ✅ |
| `make test` | CRLF 十六进制转储还原 | ✅ |
| `make test` | 转储 + 还原往返 | ✅ |

> 说明：上游 `make test` 另有约 27 组用例依赖联网下载的 ViM `xxd` 作对照，且会构建
> ASan 版本，不适合干净 CI；本包复现其中不依赖外部对照的用例。

### 2.3 消费者测试（18/18）

`test_package/test_tinyxxd.py` 针对**安装后的** `bin/tinyxxd` 运行：16 组上游用例，
外加 `-v` 版本号与 256 字节 dump/revert 往返。

### 2.4 已知限制

1. 依赖 ViM `xxd` 作对照的用例未纳入（外部依赖，非本包能力）。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang (Conan profile ohos-aarch64)
Package: tinyxxd/1.3.16 (bin/tinyxxd + man page)
```

---

*报告生成时间: 2026-09-15*
