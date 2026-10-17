# libforensic1394 0.2 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-17
- 编译器: clang 15 (OHOS SDK 26.0.0.18) / CMake 4.1.2 / Conan 2.29.1
- 目标: HarmonyOS (OHOS) 6.0, aarch64 (armv8)
- 状态: built

## 上游信息

- 版本: 0.2（上游最后一次发布，2010-10-05 打标；master 分支 2018 年后无提交）
- 官方站点: https://freddie.witherden.org/tools/libforensic1394/
- 源码仓库: https://github.com/FreddieWitherden/libforensic1394
- 源码包: `libforensic1394-0.2.tar.gz`
  - URL: https://freddie.witherden.org/tools/libforensic1394/releases/libforensic1394-0.2.tar.gz
  - SHA256: `50a82fe2899aa901104055da2ac00b4c438cf1d0d991f5ec1215d4658414652e`（59223 字节）
- 许可证: LGPL-3.0-or-later

## 上游测试清单（R51 第一步：清点，附证据）

**结论：0.2 无上游测试套件，N = 0。**

| 清点项 | 结果 | 证据 |
|--------|------|------|
| 发布 tarball 文件清单 | 17 个文件，无 tests/ 目录、无测试源文件 | `tar tzf libforensic1394-0.2.tar.gz` 全量清单（见下） |
| CMakeLists.txt 测试注册 | 无 `enable_testing()` / `add_test()` / `include(CTest)` | 上游 CMakeLists.txt 全文 146 行，仅构建静态/共享库 + 安装 + Doxygen + CPack |
| Makefile 测试目标 | 无顶层 Makefile（CMake 生成），无 `check` 目标定义 | 源码树无 Makefile.am/Makefile.in |
| 上游 master 分支 | 同样无 tests/ 目录（仅多出 src/csr.c、src/csr.h、BUGS） | GitHub API `git/trees/master?recursive=1` 全量路径清单 |
| harness 目录/脚本 | 无 | 同上 |

发布 tarball 全量文件清单（`tar tzf`，17 项）：

```
libforensic1394-0.2/AUTHORS
libforensic1394-0.2/CMakeLists.txt
libforensic1394-0.2/COPYING
libforensic1394-0.2/COPYING.LESSER
libforensic1394-0.2/README
libforensic1394-0.2/docs/Doxyfile
libforensic1394-0.2/python/setup.py
libforensic1394-0.2/python/forensic1394/__init__.py
libforensic1394-0.2/python/forensic1394/bus.py
libforensic1394-0.2/python/forensic1394/device.py
libforensic1394-0.2/python/forensic1394/errors.py
libforensic1394-0.2/python/forensic1394/functions.py
libforensic1394-0.2/src/common.c
libforensic1394-0.2/src/common.h
libforensic1394-0.2/src/forensic1394.h
libforensic1394-0.2/src/linux/juju.c
libforensic1394-0.2/src/macosx/iokit.c
```

上游无测试入口 → 上游分母 0/0；功能验证由 test_package 消费者程序承担
（2 个程序 / 46 条断言，见 `test_package/MANIFEST.yml`）。python/ 目录的
ctypes 绑定不参与本包构建（Conan 包只交付 C 库），其自测入口同样不存在。

## R47 语言预检（设备实跑，含反证）

设备 `ohc-run.py lang-preflight libforensic1394 0.2 --src <源码>` 的判定为
`detected_language=python`（依据 `python/setup.py`，`build_system=setuptools`），
并写出 `env_unsupported` 终态回执。**该判定与源码事实不符**：

- 工程主构建系统是根目录 CMake（`CMakeLists.txt`，产出 `libforensic1394.a/.so`），根目录无任何 python 打包文件；
- 被判定的 `python/setup.py` 位于子目录，是可选 **ctypes 绑定**的打包脚本（`setup(name='Forensic1394', ...)`，无 ext_modules），自述为 "Python interface to libforensic1394"；
- Conan 包只构建 C 库，`python/` 完全不参与构建；剔除绑定目录后 `.c` 实源占比 100%。

根因：`scripts/ohc/lang_detect.py::_manifest_scan` 的 manifest 名集合取自全树（`names`）
而非顶层（`tops`），子目录 `setup.py` 先于根目录 `CMakeLists.txt` 命中；与协议附录 D.4-2
"绑定类包按被绑定库判语言" 的文档规则不一致。按本地技术索引"保存反证后按真实 CLI 路径处理，
不伪造语言结果"的口径继续（`../../task-data/libforensic1394-0.2/lang-preflight-override.md`，
工具反馈见 `feedback/pending/2026-09-17-libforensic1394-lang-preflight.md`）。
本包语言属 `c` ⊂ `cpp` 兼容族，走 conan C 流程。

## 编译步骤

```bash
# 1. 下载并解压官方源码（sha256 见上）
# 2. 应用补丁
patch -p1 < patches/0001-cmake-harmonyos-platform.patch
# 3. 配置（Conan CMakeToolchain 注入工具链；CMake 4 需额外命令行定义）
cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DFORENSIC1394_BUILD_STATIC=ON -DFORENSIC1394_BUILD_SHARED=OFF
# 4. 构建并安装
cmake --build build
cmake --install build
```

Conan 入口：`conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台分支不生效，`ADD_LIBRARY` 收到空源列表（"No SOURCES given to target"） | OHOS 上 CMake 报告 `CMAKE_SYSTEM_NAME=HarmonyOS`，`CMAKE_SYSTEM` 展开为 `HarmonyOS-HongMeng Kernel 1.12.0`，不匹配上游的 `MATCHES "Linux"`；上游 `MESSAGE(FATAL ...)` 不是合法的 message 模式，不会终止配置，错误延后到 add_library 才暴露 | `patches/0001` 把条件扩为 `MATCHES "Linux" OR MATCHES "HarmonyOS"`，与仓库 R32（`os in ("Linux","OHOS")`）口径一致 |
| 2 | 配置阶段 CMake 4.1.2 拒绝 `CMAKE_MINIMUM_REQUIRED(VERSION 2.8)`（首轮 W3 实测失败） | CMake 4 移除了对 <3.5 的兼容策略；且**顶层 CMakeLists 第 1 行**的 `CMAKE_MINIMUM_REQUIRED` 在 toolchain 文件加载之前执行，`tc.variables` / `tc.cache_variables` 写入的 toolchain 缓存条目都来不及生效 | 配方在 `build()` 用 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` 以 `-D` 形式在配置命令行注入（设备探针实测：失败轮与通过轮命令对照见 `logs/…-conan-create-probe/output.txt`）；不重写上游构建文件 |
| 3 | 消费者断言 `forensic1394_get_bus_user_data(bus) == NULL` 在 OHOS 上失败 | 上游 `forensic1394_alloc()` 用 `malloc`（非 calloc）且**从不初始化** `bus->user_data`；macOS 首次堆页为零时才“碰巧”为 NULL | 断言改为只验证文档化的 set/get 往返；该未初始化行为记入本笔记与消费者测试注释（见下“上游行为观察”） |
| 4 | 本地 macOS 预验证中 `forensic1394_enable_sbp2` 崩溃 | 上游 macOS/IOKit 后端在无本地 FireWire 节点时的缺陷（`IOServiceGetMatchingServices`/plug-in 路径） | 与 OHOS 无关：OHOS 走 `src/linux/juju.c`，该函数在无 `/dev/fw*` 时安全返回 `IO_ERROR`（设备实测） |

## 上游行为观察（消费者测试必须注意）

- `forensic1394_alloc()` 返回的 `forensic1394_bus` 中 `user_data` 字段**未初始化**
  （上游用 `malloc` 且未赋值），首次调用 `forensic1394_get_bus_user_data()` 前必须先
  `set`。设备实测：OHOS 上该字段为脏值（macOS 上为 0 属堆页巧合）。
  消费者测试按文档化的 set/get 往返断言，不依赖该隐含值。
- 无 FireWire 控制器时 `forensic1394_get_devices()` 返回**非 NULL 的空列表**
  （首元素即 NULL），`*ndev` 为 0；`forensic1394_enable_sbp2()` 返回
  `FORENSIC1394_RESULT_IO_ERROR`（-5）。均属上游文档行为。
- **未覆盖路径（如实披露）**：本设备与 CI 均无 FireWire 控制器，对真实对端的
  设备枚举、`forensic1394_open_device` 及 `forensic1394_read_device`/
  `write_device`（含 `_v` 批量接口）的内存读写路径**未在本环境实测**；消费者
  测试只断言无硬件时的文档化行为与全导出符号的可链接性。需要外接 IEEE 1394
  硬件的场景应由具备设备的评审复核，本包不声称这些路径已验证。

## 源码修改

仅 1 个补丁，未新增/删除源文件：

| 补丁 | 修改内容 |
|------|----------|
| `patches/0001-cmake-harmonyos-platform.patch` | `CMakeLists.txt` 第 51 行平台条件从 `MATCHES "Linux"` 扩为 `MATCHES "Linux" OR MATCHES "HarmonyOS"`（1 行） |

不涉及 `__OHOS__` 平台宏；`src/linux/juju.c` 等 C 源码零修改。

## OHOS 平台适配要点

- **firewire-cdev 接口由 SDK 提供**：OHOS SDK 26.0.0.18
  (`ohos/native/sysroot/usr/include/linux/`) 提供完整 `firewire-cdev.h`（270 行，
  `FW_CDEV_VERSION 3`）与 `firewire-constants.h`（含 TCODE_*/RCODE_*），
  因此 Juju 后端无需移植或 stub，`CHECK_INCLUDE_FILE(linux/firewire-cdev.h)` 通过。
  同类先例：libdc1394 2.2.7 的 Juju 后端同样直接编译通过。
- **运行期依赖内核能力**：库通过 `/dev/fw*` 字符设备 + `/sys/bus/firewire/devices/fw<n>/*`
  属性工作。无 FireWire 控制器时 `forensic1394_get_devices` 返回空列表（`*ndev = 0`）、
  `forensic1394_enable_sbp2` 返回 `FORENSIC1394_RESULT_IO_ERROR`，属上游文档行为
  （构造 SBP-2 单元目录需要本地 Juju 节点），不是适配缺陷。
- **clang 与上游编译选项**：`-Werror -Wall -fvisibility=hidden` 仅在上游的
  `CMAKE_COMPILER_IS_GNUCC` 分支（GCC）生效，OHOS clang 下不启用，无需处理。
- **未涉及 VLA-in-struct 类问题**：juju.c 使用固定缓冲（`char buffer[16*1024]`），
  与 libdc1394 遇到的 clang VLA 限制无关。

## 依赖版本

无第三方依赖（仅 libc/syscall 层：`glob`/`poll`/`ioctl`/`open`，OHOS musl 全部提供）。
- 构建工具: clang 15、CMake 4.1.2、Ninja/Make
- 无 `requires`、无 `tool_requires`

## 验证结果

```bash
# conan create（含 test_package）
conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
# 消费者程序输出
forensic1394_api_surface: 37 checks passed
forensic1394_bus_lifecycle: 9 checks passed
```

| 层级 | 结果 |
|------|------|
| 上游测试（0.2 无套件） | 0/0（无入口，清点证据见上） |
| 消费者测试 | 2 程序 / 46 断言全过 |

设备实测输出、产物清单与哈希见 `reports/`（W3 生成）。

## 注意事项

- 0.2 是上游最后一次发布（2010）；master 分支后续增加了 `src/csr.c`（CSR 解析重构）
  但无新 tag。若后续适配 master，需重新核对平台条件块与 CSR 相关代码。
- `forensic1394_get_result_str` 的表中 `FORENSIC1394_RESULT_NO_PERM` 对应字符串
  在上游拼写为 `"Insufficient permisisons"`（原文如此，0.2 ABI 的一部分）；
  消费者测试按原样断言，避免"顺手修正"改变 ABI 行为。
- 库为动态/静态可选（`shared` 选项，默认静态）；`libforensic1394` 与系统库
  不同名，不需要 R26 的强制静态处理。
- python/ 目录的 ctypes 绑定未纳入 Conan 包；如需交付需另立包型（非 C 库产物）。

---

**编译结束**: 2026-09-17
**最终状态**: built
