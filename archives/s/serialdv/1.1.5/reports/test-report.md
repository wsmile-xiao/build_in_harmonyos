# serialdv 1.1.5 测试报告

> **项目**: serialdv（AMBE3000 数字语音编解码串口/UDP 接口库）
> **测试日期**: 2026-09-19
> **测试环境**: HarmonyOS 6.1.0.117（HongMeng Kernel 1.12.0，aarch64 HAD-W32），OHOS SDK clang 15.0.4，Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64-device`
> **测试类型**: 消费者 API 回归测试（test_package）+ 设备侧协议端到端测试（模拟 AMBE3000 服务端）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游自动化用例总数 | 0 | —（上游无测试套件，R51 证据见下） |
| 适配后消费者测试断言（test_package） | 59 | 100% |
| 通过 (PASS) | 59 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 设备侧协议端到端断言（UDP E2E） | 11 | 100% |
| 通过 (PASS) | 11 | 100% |

**核心功能通过率**: ✅ **100%（59/59 + 11/11）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。正式 `conan create`（W3/CI 同源）在真实鸿蒙 PC 设备上编译、打包、安装并通过全部消费者断言；设备侧以模拟 AMBE3000 UDP 服务端完成 PRODID 握手、速率切换、编码（9/18 字节 AMBE 帧）与解码（192 样本）全链路协议验证。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OHOS CMake 平台无 SONAME 支持 | 动态库缺 DT_SONAME，CI L5a 门禁不过 | 🟡 已修复（配方注入 `-Wl,-soname,libserialdv.so`） |
| OHOS CMake 不生成 RPATH | `dvtest` 需 LD_LIBRARY_PATH 才能直接运行（CI L2 非阻塞 skip） | 🟢 平台特性，不影响库使用 |
| 上游速率表未覆盖 DVRate7100x4400/DVRate2400 | 返回 0（上游行为，非本适配引入） | 🟢 已断言记录 |

### 2.3 可用功能清单

```
✅ 动态库加载与 API 链接: libserialdv.so（SONAME libserialdv.so），6 个头文件
✅ DVController 生命周期: open/close/isOpen、关闭态拒绝 encode/decode
✅ DV3000 协议常量与 MBE 帧长表: getNbMbeBytes/getNbMbeBits 全速率矩阵
✅ UDP 传输后端: PRODID 握手、RATEP/GAIN/AMBE/AUDIO 包收发（真实 socket）
✅ 串口后端错误路径: 非 TTY 设备安全拒绝（不崩溃）
✅ 代码库/工具: dvtest -h 正常（需 LD_LIBRARY_PATH 指向包 lib 目录）
⚠️ 实际编解码: 需要 AMBE3000 硬件（ThumbDV）或 AMBE-over-UDP 服务端（已在模拟服务端上验证协议链路）
```

### 2.4 已知限制

1. 上游无自动化测试套件（无 `tests/`、无 `enable_testing()/add_test()`），`dvtest` 为需真实 DV 硬件的工具；CI 环境无硬件，端到端验证采用协议兼容的模拟服务端。
2. `dvtest` 为动态链接工具，OHOS CMake 不写 RPATH，直接执行需 `LD_LIBRARY_PATH=<prefix>/lib`（CI L2 为非阻塞项）。
3. 上游 `getNbMbeBytes/getNbMbeBits` 未覆盖 `DVRate7100x4400`、`DVRate2400`（返回 0），属上游现状。

---

## 三、测试详情

### 3.1 上游测试用例清点（R51）

| 检查项 | 结果 |
|--------|------|
| 源包内 `tests/`、`test/`、`unittests/` 目录 | 无 |
| `CMakeLists.txt` 中 `enable_testing()` / `include(CTest)` / `add_test()` | 无 |
| 唯一测试性产物 | `dvtest.cpp`（安装为 `bin/dvtest` 的工具，运行需 AMBE3000 设备或 AMBE-over-UDP 服务端） |
| `samples/*.raw` | 仅 8 kS/s S16LE 输入样本，非断言型用例 |
| **上游自动化用例数** | **0**（清点证据同步记录于 `test_package/MANIFEST.yml`） |

### 3.2 适配后测试（补全）

**A. 消费者 API 回归测试** `test_package/test_serialdv.cpp`（59 断言，`conan create` 自动执行）：

| 分组 | 断言数 | 结果 |
|------|:---:|------|
| 协议常量（块大小/头长/类型码/控制码） | 16 | ✅ PASS |
| `getNbMbeBytes` 全速率矩阵（含 2 项上游空缺记录） | 14 | ✅ PASS |
| `getNbMbeBits` 全速率矩阵（含 2 项上游空缺记录） | 14 | ✅ PASS |
| 控制器生命周期（关闭态拒绝 encode/decode） | 3 | ✅ PASS |
| 串口错误路径（/dev/null 非 TTY、不存在设备） | 3 | ✅ PASS |
| UDP 错误路径（非本地对端无服务、非法入参） | 4 | ✅ PASS |
| DummyDataController 契约 | 5 | ✅ PASS |
| **合计** | **59** | **✅ 59/59（100%）** |

**B. 设备侧协议端到端测试**（`serialdv_udp_e2e`，链接包内 `libserialdv.so`，对端为 Amax 主机上的模拟 AMBE3000 服务端）：

| 测试项 | 验证内容 | 结果 |
|--------|----------|------|
| `open()` | PRODID 请求/应答握手（`DV3000 chip identified as: DV3000`） | ✅ PASS |
| `encode()` 3600x2400 | AUDIO→AMBE 应答，9 字节帧内容与模拟端确定性数据逐字节一致 | ✅ PASS |
| `decode()` 3600x2400 | AMBE→AUDIO 应答，192 样本与模拟端确定性数据逐样本一致 | ✅ PASS |
| `encode()` 7200x4400 | 速率切换后 18 字节帧内容一致 | ✅ PASS |
| `decode()` 7200x4400 | 192 样本逐样本一致 | ✅ PASS |
| `close()` | isOpen() 转为 false | ✅ PASS |
| **合计** | —— | **✅ 11/11（100%，复跑 2 次均通过）** |

**C. 工具冒烟**：`dvtest -h` 输出完整用法（退出码 0）✅。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| `dvtest` 真实编解码回放 | 需要物理 AMBE3000 设备（ThumbDV 串口）或真实 AMBE 服务端；设备端无该硬件，协议链路已由 B 组模拟服务端覆盖 |
| `make check`/`ctest` | 上游未提供任何测试目标（见 3.1） |

---

## 四、关键问题分析

### 问题1: 动态库缺失 DT_SONAME（CI L5a 门禁）

**现象**：`readelf -d libserialdv.so` 无 SONAME 条目；上游 `VERSION/SOVERSION` 属性在 OHOS 不生效。
**根因**：OHOS 的 CMake 平台模块 `Platform/OHOS.cmake` 仅 `include(Platform/Linux)`，未定义 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 等，CMake 不生成版本化 SONAME 与符号链接（仓库内 apache-arrow/boost 适配补丁有同类记录）。
**解决方案**：配方 `generate()` 注入 `CMAKE_SHARED_LINKER_FLAGS="-Wl,-soname,libserialdv.so"`（与安装文件名一致，零补丁）。修复后 `readelf`：`SONAME [libserialdv.so]`，`dvtest` 的 `DT_NEEDED=libserialdv.so`，CI L5a 通过。

### 问题2: CI L2 dvtest --version 失败（非阻塞）

**现象**：CI 直接执行 `bin/dvtest --version` 报加载失败。
**根因**：OHOS CMake 构建不写 RPATH（与当前仓库 `§7 RPATH 解析` 已知平台差异一致），工具依赖 `libserialdv.so` 需 `LD_LIBRARY_PATH`。
**处置**：CI L2 本身为**非阻塞**项（结果 skip）；库消费者通过 Conan 生成器获得正确链接参数，`test_package`（带 conanrun 环境）59/59 通过。

---

## 五、测试环境

```
设备: HarmonyOS PC 6.1.0.117 / HongMeng Kernel 1.12.0 aarch64 (HAD-W32)
工具链: OHOS SDK 26.0.0.18 native clang/clang++ 15.0.4 (aarch64-linux-ohos)
Conan: 2.29.1 (OHOS 适配版), profile ohos-aarch64-device
构建: CMake 4.4.3 + Unix Makefiles, Release
包: serialdv/1.1.5@ohpcd/stable
产物: lib/libserialdv.so（SONAME libserialdv.so）、include/serialdv/*.h、bin/dvtest、licenses/LICENSE
源码: https://github.com/f4exb/serialDV/archive/refs/tags/v1.1.5.tar.gz
      sha256 9ff90d85ff613e81659a2d661515e01d3c1f3ad1cade58908838b97fdd7ab5d2
```

---

*报告生成时间: 2026-09-19*
