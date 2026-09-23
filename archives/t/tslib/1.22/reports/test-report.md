# tslib 1.22 测试报告

> **项目**: tslib
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（OHOS SDK native clang）
> **测试类型**: 手动功能测试 + test_package 消费者测试（上游无官方测试套件）

---

## 一、测试摘要

| 指标 | 数值 | 说明 |
|:----:|:----:|:------:|
| 上游自动化测试入口 | 0 | 上游无任何自动化测试（清点证据见下） |
| test_package 消费者测试 | 1 | PASS（5 项断言） |
| 工具冒烟探针（L2） | 11 | 10 通过 + 1 非阻塞（ts_finddev 无长选项） |

**消费者测试通过率**: 1/1（100%）

**上游测试通过率**: 0/0（不适用——上游 0 个可运行测试入口）

---

## 二、上游测试清点证据（R51 三步法）

1. **清点**：对 tslib 1.22 原始包（sha256 `aaf0aed410a268d7b51385d07fe4d9d64312038e87c447ec8a24c8db0a15617a`）全部 Makefile.am（根、etc、src、plugins、tests、tools）执行 `grep -rn "TESTS\|check_PROGRAMS" --include="Makefile.am"`，零命中；automake 的 `make check` 目标为结构性空跑。
2. **运行**：无可运行自动化入口。tests/ 目录下 10 个程序（ts_calibrate、ts_conf、ts_finddev、ts_harvest、ts_print、ts_print_mt、ts_print_raw、ts_test、ts_test_mt、ts_verify）为交互式硬件工具，需真实触摸屏与 framebuffer 设备，无法在无头环境执行，全部按上游既定形态编译构建（非测试跳过）。
3. **申报**：上游 0 个可运行测试入口，通过率 0/0；不据此省略消费者测试。

## 三、test_package 消费者测试（鸿蒙特有）

| 测试项 | 断言内容 | 结果 |
|--------|----------|------|
| test_tslib_consumer | `ts_libversion()` 非 NULL | ✅ PASS |
| test_tslib_consumer | `package_version == "1.22"` | ✅ PASS |
| test_tslib_consumer | `TSLIB_VERSION_VERSION` 特性位置位 | ✅ PASS |
| test_tslib_consumer | `tslib_version()` 前缀为 "tslib 1.22" | ✅ PASS |
| test_tslib_consumer | `ts_open()` 对不存在设备返回 NULL | ✅ PASS |

执行日志（W3 conan create，`reports/w3-local-ci.log`）：

```
tslib/1.22 (test package): RUN: ... test_tslib_consumer.c ... -lts -o test_tslib_consumer
tslib/1.22 (test package): RUN: ... test_tslib_consumer
tslib consumer test OK: version API and error path verified
```

破坏性反向验证（L1e/R34）：移除包内 bin/lib/include 后消费者测试确认失败，证明测试真实依赖被测包。

## 四、构建产物冒烟（L2 工具探针）

| 工具 | 探针 | 结果 |
|------|------|------|
| ts_calibrate | --version | ✅ |
| ts_conf | --version | ✅ |
| ts_finddev | --version/--help | ⚠️ 均不支持（非阻塞，工具按上游设计仅接受位置参数） |
| ts_harvest | --version | ✅ |
| ts_print | --version | ✅ |
| ts_print_mt | --version | ✅ |
| ts_print_raw | --version | ✅ |
| ts_test | --version | ✅ |
| ts_test_mt | --help | ✅ |
| ts_uinput | --help | ✅ |
| ts_verify | --version | ✅ |

真机功能冒烟：`ts_print_raw`/`ts_conf` 在设备上原生执行，加载 libts.so 并 dlopen input 插件后到达设备访问点（`/dev/input` 受 SELinux 限制返回 Permission denied，属预期错误路径），证明库与插件加载链路完整。

## 五、测试结论

### 5.1 总体评价

✅ **通过**——消费者测试与产物冒烟全部符合预期，上游无自动化测试入口为上游既定事实。

### 5.2 已知限制

1. 触摸屏读取/校准等功能需真实硬件，无头环境仅验证构建、链接、插件加载与错误路径。
2. ts_finddev 不支持长选项探针（上游设计如此，非适配缺陷）。
