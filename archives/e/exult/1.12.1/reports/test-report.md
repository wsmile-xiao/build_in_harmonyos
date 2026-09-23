# Exult 1.12.1 Test Report

> **项目**: exult
> **测试日期**: 2026-09-09
> **测试环境**: HarmonyOS PC aarch64 Conan OHOS profile
> **测试类型**: 官方递归检查 + Conan 消费者测试

## 一、测试摘要

| 指标 | 数值 | 结果 |
|:----:|:----:|:------:|
| 上游注册测试用例 | 0 | 无上游 TESTS/check_PROGRAMS |
| 上游递归检查目标 | 1 | 通过（非测试用例） |
| 真实消费者断言 | 3 | 100% |
| 失败 | 0 | 0% |
| 跳过 | 0 | 0% |

**真实消费者功能通过率**: ✅ **100%**

## 二、测试结论

### 2.1 总体评价

✅ **Exult 1.12.1 在 HarmonyOS PC aarch64 上完成构建、安装和消费者验证。**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游未声明独立 TESTS/check_PROGRAMS | 上游测试统计 | 🟡 |
| `--help` 对部分工具返回非零状态 | L2 非阻断 smoke | 🟡 |

### 2.3 可用功能清单

```text
✅ exult: 版本查询通过
✅ expack: 用法输出通过
✅ ipack: 用法输出通过
✅ Conan 消费者环境: 三个可执行文件均可调用
```

### 2.4 已知限制

1. 本次适配禁用 MT32Emu、FluidSynth 和 Android APK 构建分支；Exult 的 `expack` 和 `ipack` 工具保持构建并由消费者测试覆盖。
2. 上游 `make check` 是递归检查目标，未声明独立单元测试清单。

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `make check` | 上游递归检查目标 | ✅ PASS |
| `exult --version` | 主程序版本查询 | ✅ PASS |
| `expack --help` | 数据打包工具消费者调用 | ✅ PASS |
| `ipack --help` | 图像打包工具消费者调用 | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | 无 | 本次记录的四项断言全部通过 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | 未跳过上游测试或消费者测试 |

## 四、验证命令

```text
make check
conan create archives/e/exult/1.12.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
sh test.sh
```

结果：上游检查通过，Conan create 通过，消费者测试通过。

## 五、测试环境

```text
Package: exult/1.12.1
Build system: Autotools
Target: aarch64-linux-ohos
Compiler: clang/clang++
Dependencies: sdl2/2.30.10, libpng/1.6.58, zlib/1.3.1.1,
              libvorbis/1.3.7, libogg/1.3.6
```

*报告生成时间: 2026-09-09*
