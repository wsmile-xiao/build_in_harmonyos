# libgooglepinyin 0.1.2 适配笔记

## 编译环境

- 构建系统：CMake（上游最低版本声明 2.6，本适配提升到 3.5）
- 编译日期：2026-09-17
- 目标编译器：OHOS Clang 15（profile `ci/conan/profiles/ohos-aarch64`）
- 状态：built

## 编译步骤

1. 从 Google Code 官方归档下载并校验 libgooglepinyin-0.1.2.tar.bz2（SHA-256 `1a339ae45721a60b9fadd15e43c34b9bb27af3bb999c00ed0d88b4084cfd0637`）。
2. `conan create` 内：先以构建机 CMake pass（不带 OHOS toolchain）构建 `dictbuilder` 目标并运行，生成 `dict_pinyin.dat` 到源码 `data/` 目录。
3. 再以 OHOS profile 的 `CMakeToolchain` 全量构建：补丁后的 `data/CMakeLists.txt` 检测到源目录已有 `dict_pinyin.dat` 时直接安装，不再运行目标架构的 `dictbuilder`。
4. `cmake install` 安装共享/静态库、`include/googlepinyin/` 头文件、系统词典与 pkg-config 元数据。

## 关键适配点

### 1. 词典构建工具的交叉编译问题（核心）

上游 `data/CMakeLists.txt` 用 `add_custom_command` 在构建期运行刚编译的 `dictbuilder`（目标架构可执行文件）把 UTF-16 词典文本编译成二进制词典 `dict_pinyin.dat`。线上 CI 为交叉编译环境（构建机不能执行 aarch64 OHOS 二进制），该步骤必然失败。配方统一改为两阶段：构建机 pass 生成词典 → 目标 pass 安装预置词典。该行为对 native 构建同样正确，`dictbuilder` 工具仍会正常构建（上游 tools/ 目录不变，只是数据文件改由构建机工具生成）。

### 2. CMake 4 兼容

设备实测 CMake 4.1.2 对 `cmake_minimum_required(VERSION 2.6)` 直接报错（`RC=1`，"Compatibility with CMake < 3.5 has been removed"）。补丁提升到 3.5，无策略行为变化。

### 3. staged 安装

上游把 `${CMAKE_INSTALL_PREFIX}/lib` 等绝对路径用作 `install(... DESTINATION)`，`cmake --install --prefix` 无法重定向（探索实测 install 到 `/usr/local/lib` 失败）。补丁将头文件、库、词典、pkg-config 的 DESTINATION 改为相对路径；`googlepinyin.pc.in` 仍由 `configure_file` 用 CMake 变量展开，内容语义不变。

### 4. Conan shared 选项生效

上游默认同时构建共享库，`ENABLE_STATIC=ON` 时额外构建静态库，两者同名安装。补丁改为 `ENABLE_STATIC` 二选一（STATIC 或 SHARED），Conan `shared` 选项真实控制产物类型。

### 5. HarmonyOS 平台下的共享库 SONAME（W3 L5a）

首轮 W3 的 L5a 门禁失败：打包的 `libgooglepinyin.so` 缺少 DT_SONAME。根因：OHOS 的 Conan toolchain 设 `CMAKE_SYSTEM_NAME=HarmonyOS`，其平台模块沿用 Android 风格（`CMAKE_PLATFORM_NO_VERSIONED_SONAME`），忽略目标的 VERSION/SOVERSION 属性，既不生成版本符号链接也不给链接器传 `-soname`。补丁在共享目标上显式追加 `LINK_FLAGS -Wl,-soname,libgooglepinyin.so`，SONAME 与安装文件名一致（符合 OHOS 无版本 so 惯例），readelf 实测 `SONAME: [libgooglepinyin.so]`。

## 上游测试清点（R51）

上游无测试套件。清点证据（0.1.2 tarball）：

- 归档仅含 `CMakeLists.txt`、`INSTALL`、`cmake/`、`data/`、`include/`、`src/`、`tools/`，无 `tests/`、`test/` 目录；
- 全部 5 个 CMakeLists.txt 均无 `add_test`/`enable_testing`/CTest 注册；
- 无 `make check` 目标，无任何测试源文件。

因此上游测试 0/0（确无入口），消费者测试由 test_package 提供：1 个 C++ 程序、4 个断言（见下）。

## 消费者测试（test_package）

`test_libgooglepinyin.cpp` 链接打包后的 libgooglepinyin，以打包的 `dict_pinyin.dat` 为系统词典、新建空用户词典：

1. `im_open_decoder` 返回真；
2. `im_search("nihao", 5)` 返回非零候选数；
3. `im_get_candidate(0, ...)` 返回非 NULL；
4. 前 10 个候选中出现 U+4F60 U+597D（"你好"）。

实测（OHOS aarch64 设备原生运行）：`PASS: candidates=62 top=你好`。词典 sha256 `13c2ccc012f77ea1c9a6e2c38e278ad6d5d8ccec3802b6c75718a97feb3d3798`（1071858 字节）。

## 验证结果

- 构建机（OHOS 设备）dictbuilder 生成词典：PASS。
- OHOS aarch64 共享 `conan create`：PASS（W3，见 reports/）。
- 消费者配置/编译/链接：PASS。
- 消费者实跑（打开词典、解码 "nihao"→"你好"）：PASS。
- 共享库 DT_SONAME（readelf）：`SONAME: [libgooglepinyin.so]` PASS。
- 补丁按序 `git apply`：PASS（4/4）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libgooglepinyin.so.0`（shared）或 `libgooglepinyin.a`（static） | 解码引擎库 |
| `include/googlepinyin/*.h` | 公共头文件（18 个） |
| `lib/googlepinyin/data/dict_pinyin.dat` | 二进制系统词典 |
| `lib/pkgconfig/googlepinyin.pc` | pkg-config 元数据 |

---

**编译结束**：2026-09-17

**最终状态**：built
---

**编译结束**: 2026-09-17 15:30
**最终状态**: built
