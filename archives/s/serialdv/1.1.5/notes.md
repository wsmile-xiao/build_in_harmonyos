# serialdv 1.1.5 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，`project(serialdv)`）
- 编译日期: 2026-09-19
- 编译器: OHOS SDK clang/clang++ 15.0.4（aarch64-linux-ohos，profile `ohos-aarch64-device`）
- Conan: 2.29.1（OHOS 适配版），`serialdv/1.1.5@ohpcd/stable`
- 状态: built（配方零补丁；消费者测试 59/59；设备侧 UDP 协议 E2E 11/11）

## 编译步骤

1. `conan create` 按 conanfile.py 流程执行：`source()` 拉取官方源包
   `https://github.com/f4exb/serialDV/archive/refs/tags/v1.1.5.tar.gz`
   （sha256 `9ff90d85…ab5d2` 校验通过）；CMakeToolchain 生成工具链后
   configure/build/install。
2. 上游 CMakeLists 关键行为：
   - `add_library(serialdv SHARED ...)` 固定动态库（`VERSION 1.1.5`、
     `SOVERSION 1`——OHOS 平台不生成版本化文件名/SONAME，见下）；
   - `option(BUILD_TOOL "Build dvtest tool" ON)`：默认构建并安装 `bin/dvtest`；
   - GNUInstallDirs 安装 `lib/libserialdv.so`、`include/serialdv/*.h`。
3. 配方 `generate()`：
   - `BUILD_TOOL` 选项透传（默认 ON，与上游一致）；
   - 注入 `CMAKE_SHARED_LINKER_FLAGS=-Wl,-soname,libserialdv.so` 修复
     OHOS CMake 缺 SONAME（CI L5a）问题。
4. `conan-verify`（G0–G4 全 PASS）→ 本地 CI 门禁
   （G0/KC/JC/L0/L1/L4/L5 全 PASS）→ `finish` W3 复核。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 动态库缺 DT_SONAME（CI L5a 门禁） | OHOS 的 `Platform/OHOS.cmake` 仅 include Platform/Linux，未定义 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`，上游 `VERSION/SOVERSION` 属性不生效（仓库内 apache-arrow/boost 同类记录） | 配方 `generate()` 注入 `-Wl,-soname,libserialdv.so`（与安装文件名一致，零补丁） |
| 2 | CI L2 `dvtest --version` 加载失败（非阻塞） | OHOS CMake 不写 RPATH，工具依赖同包 `libserialdv.so`，需 `LD_LIBRARY_PATH` | 记录为平台特性；L2 为非阻塞项；库消费者由 Conan 生成器接管链接参数 |
| 3 | 无 AMBE3000 硬件无法跑 `dvtest` 全流程 | 设备无 ThumbDV 串口硬件 | 设备侧对 Amax 主机上的模拟 AMBE3000 UDP 服务端完成 PRODID/速率/编码/解码全链路验证（11/11 ×2 次） |

## 源码修改

无补丁（patches/ 目录不存在，`conandata.yml` 中 `patches: []`）。

## 依赖版本

无第三方依赖（仅 POSIX termios / BSD socket + libc++）。

## 验证结果

```text
# W3 / CI 同源 conan create（设备 profile）
test_serialdv: 59/59 assertions passed          # conan-verify G2、本地 CI 门禁、finish W3 各一次
readelf -d libserialdv.so: SONAME [libserialdv.so]
dvtest -h: 正常输出用法（LD_LIBRARY_PATH=<prefix>/lib）
# 设备侧协议端到端（模拟 AMBE3000，Amax 主机 UDP）
serialdv_udp_e2e: 11/11 checks passed           # 复跑 2 次均通过
   open PRODID 握手 / encode 3600x2400(9B)+7200x4400(18B) / decode 192 样本逐字节一致
# 本地 CI 门禁
G0_RESULT=pass KC_RESULT=pass JC_RESULT=pass L0_RESULT=pass
L1_RESULT=pass (test_package executed) L4_RESULT=pass (no patches)
L5_RESULT=pass (bin/ has content) L2_RESULT=skip (非阻塞，见问题 2)
```

## 注意事项

- 实际编解码功能需要 AMBE3000 硬件（串口 ThumbDV）或 AMBE-over-UDP 服务端；
  无硬件时库可正常加载、`dvtest -h` 可用。
- 上游 `getNbMbeBytes/getNbMbeBits` 未覆盖 `DVRate7100x4400` 与 `DVRate2400`
  两个枚举（返回 0），`test_package` 以行为断言如实记录该现状。
- 上游 `MBE_AUDIO_BLOCK_SIZE_INTERNAL=192`（内部块）与公开
  `MBE_AUDIO_BLOCK_SIZE=160` 并存，`dvtest` 使用公开 160/320 字节 I/O 循环；
  模拟服务端按内部 192 样本格式应答（`0x0182`）以匹配本版本库的解析逻辑。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libserialdv.so` | 动态库（SONAME `libserialdv.so`，含全部公开符号） |
| `include/serialdv/*.h` | 6 个公开头文件（dvcontroller/datacontroller/serial/udp/dummy/export） |
| `bin/dvtest` | 编解码测试工具（需 DV 硬件或 AMBE-over-UDP 服务端） |
| `licenses/LICENSE` | GPL-3.0 许可证 |
| `packaging/serialdv-1.1.5-ohos-aarch64.tar.gz` | Conan 包产物发布归档 |

**编译结束**: 2026-09-19 —— W3/CI 本地门禁全过（消费者测试 59/59，设备协议 E2E 11/11）。
