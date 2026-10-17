# libaccounts-qt 1.17 适配笔记

## 编译环境
- 构建系统: cmake（自写 CMakeLists.txt，随 exports_sources 分发）
- 编译日期: 2026-10-02
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，clang 15）
- 状态: built

## 编译步骤

上游 `libaccounts-qt` 只提供 qmake 构建（`accounts-qt.pro`），而 ohpcd 的 `qtbase`
包不含 qmake 可执行文件，因此配方改为自带 `CMakeLists.txt`：

1. `conan create` 拉取 `qtbase/6.11.1.1`、`libaccounts-glib/1.27`、`glib2/2.88.0`
2. `generate()` 通过 `CMakeToolchain` 注入工具链，并设置
   - `Qt6_DIR=<qtbase pkg>/lib/cmake/Qt6`
   - `CMAKE_PREFIX_PATH=<qtbase pkg>/lib/cmake;<qtbase pkg>`
   - `GLIB_GIO_UNIX_INCLUDE_DIR=<glib2 pkg>/include/gio-unix-2.0`
3. `build()` 用自带 CMakeLists 编译出 `libaccounts-qt6.a`（静态）并安装
   `include/Accounts/*`、`lib/libaccounts-qt6.a`、`lib/cmake/AccountsQt6/*`

关键 configure（手工探索阶段等价命令）：

```bash
cmake -S . -B build -G Ninja \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$QTBASE_PKG/lib/cmake" \
  -DGLIB_GIO_UNIX_INCLUDE_DIR="$GLIB_PKG/include/gio-unix-2.0" \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build -j1 && cmake --install build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 CMake 构建，ohpcd qtbase 无 qmake | 上游仅 `accounts-qt.pro`；qtbase 包不打包 qmake | 自写 `CMakeLists.txt` 经 `exports_sources` 随配方分发（与仓内 1.13 配方同法） |
| 2 | `find_package(Qt6)` 失败 | qtbase 根 `cpp_info` 设了 `cmake_find_mode=none`，CMakeDeps 不生成可用 Qt6 配置 | 构建侧用 `Qt6_DIR` 指向 `<qtbase>/lib/cmake/Qt6`；消费侧把 qtbase 映射到真实目标（`set_property cmake_target_name=Qt6::Core`）并显式 `find_package(Qt6 CONFIG)` |
| 3 | test_package 报 `Qt6::Core ... target was not found` | CMakeDeps 生成的 `AccountsQt6` 接口引用 `qtbase::qtbase`，而 qtbase 无该目标 | test_package 先 `find_package(Qt6 COMPONENTS Core Xml CONFIG REQUIRED)` 再 `find_package(AccountsQt6)`，并显式链接 `Qt6::Xml` |
| 4 | W3 镜像注入后 `KeyError: '1.17'` | conandata 用了版本键控结构，ghfast 镜像改写脚本按扁平结构处理 | `conandata.yml` 改为扁平结构（`sources.url`/`sha256`） |
| 5 | 源码解压后落子目录，配置脚本找不到 `accounts-qt6.pc.in` | `get()` 未加 `strip_root` | `get(..., strip_root=True)` |
| 6 | 链接期缺 gio 头/符号 | CMakeDeps 未导出 `gio-unix-2.0` 头目录，glib2 属传递依赖 | `glib2` 以 `transitive_headers`/`transitive_libs` 声明，并显式传 `GLIB_GIO_UNIX_INCLUDE_DIR` |

## 源码修改

无补丁（无 `patches/` 目录）。唯一随包文件是自写的 `CMakeLists.txt`（构建系统替代，非源码修改）。

## 依赖版本

| 包 | 版本 | 用途 |
|----|------|------|
| qtbase | 6.11.1.1 | Qt6 Core/Xml（构建 + 运行） |
| libaccounts-glib | 1.27 | 账号后端（公开头依赖） |
| glib2 | 2.88.0 | libaccounts-glib 传递依赖（GIO/GLib） |

## 验证结果

```bash
# 配方验证（8 道门禁）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libaccounts-qt 1.17
# → Verdict: PASS（G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS）

# W3 本地 CI 模拟
bash ci/conan/setup.sh && bash ci/conan/build_and_test.sh libaccounts-qt/1.17
# → PASS exit 0，测试报告 .ci-result.json（exit_code=0）

# 上游测试（QtTest，实跑）
cd tests && TESTDIR=$PWD ./accountstest
# → Totals: 4 passed, 32 failed, 1 skipped（36 项）
#   32 项失败为沙箱环境（无 accounts DB / 无 accounts D-Bus 服务），非库缺陷
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libaccounts-qt6.a | 静态库 | 包内 `lib/`（本地打包证据 `packaging/*.tar.gz`，被 .gitignore 忽略不入 PR） |

## 注意事项

- 消费方（如 kaccounts-integration）若用 CMakeDeps，需照上面第 2/3 条处理 qtbase：
  `find_package(Qt6 CONFIG)` + 映射 qtbase 目标名，并额外链接 `Qt6::Xml`。
- `libaccounts-qt6` 为静态库（非系统同名库，故不受 R26 静态约束影响，纯因 Qt 依赖链选择静态）。

---

**编译结束**: 2026-10-02 22:34
**最终状态**: built
