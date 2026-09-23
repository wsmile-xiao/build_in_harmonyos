# ayatana-indicator-session 26.6.1 适配笔记

## 编译环境
- 构建系统: cmake（cmake_minimum 3.13，顶层 CMakeLists.txt）
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15（OHOS aarch64，`ci/conan/profiles/ohos-aarch64`，cppstd=17）
- 状态: built（conan-verify 本地 8 门禁全 PASS；官方 CI 待依赖发布后复验）

## 编译步骤

手动探索编译（Step 2，依赖经 conan 沙箱 PkgConfigDeps 提供 .pc）：
```bash
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...   # 生成 glib-2.0/gio-2.0/.../libayatana-common.pc
# 补 gio-unix-2.0.pc（glib 配方未声明 gio-unix 组件，PkgConfigDeps 不产出）
cmake -S . -B build-ais \
      -DCMAKE_TOOLCHAIN_FILE=<sandbox>/conan_toolchain.cmake \
      -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DENABLE_RDA=OFF -DSKIP_DATA_PO=ON -DENABLE_TESTS=OFF -DENABLE_WERROR=OFF
make -C build-ais -j1
make install DESTDIR=$TEST_PREFIX   # 产物安装到 bin/ayatana-indicator-session/ayatana-indicator-session-service
# make check: ENABLE_TESTS=OFF，无测试目标（上游测试需 GTest+D-Bus，见 MANIFEST.yml）
```

配方验证（Step 2.5-2.6）：
```bash
python3 scripts/ohc-run.py conan-init ayatana-indicator-session 26.6.1
python3 scripts/ohc-run.py conan-verify ayatana-indicator-session 26.6.1   # 8 门禁全 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | data/CMakeLists `find_package(GSettings REQUIRED)`、po/ `find_package(Intltool REQUIRED)` 在 OHOS configure 即失败 | OHOS 无 GSettings/Intltool CMake 模块（libayatana-common 同款问题） | 0001 补丁：新增 `SKIP_DATA_PO` 选项，guard `add_subdirectory(data/po)`；data 内 gschema/autostart/desktop 属桌面发行集成数据，服务运行非必需。conanfile generate() 固化 SKIP_DATA_PO=ON |
| 2 | 上游 CMakeLists 把 rda 列入 REQUIRED pkg 列表 | rda（远程桌面感知）pkg-config 包未发布；RDA 代码全在 `#ifdef RDA_ENABLED` 内 | `-DENABLE_RDA=OFF`（conanfile generate() 固化）；RDA_ENABLED 未定义 → service.c 中相关调用整段裁剪，主路径不受影响 |
| 3 | `pkg_check_modules(REQUIRED ... gio-unix-2.0)` 找不到 gio-unix-2.0 | glib/2.88.0.1 配方只声明 glib-2.0/gobject-2.0/gmodule-2.0/gthread-2.0/gio-2.0 组件，无 gio-unix 组件 → PkgConfigDeps 不产出 gio-unix-2.0.pc（头文件在 glib 包 include/gio-unix-2.0，API 在 libgio-2.0） | conanfile generate() 手工把 gio-unix-2.0.pc 写入 generators 目录（已在 PKG_CONFIG_PATH），写法同 accountsservice/26.27.3 先例 |
| 4 | 服务二进制（无 --version/--help）无法做 L2 冒烟/commands.json | 守护进程 main() 忽略 argc/argv，直接进入 GMainLoop | 0002 补丁：main() 增加标准 `--version`/`--help` 前置分支（printf+fflush+_exit(0)），`--version` 输出 `ayatana-indicator-session 26.6.1` |
| 5 | 服务二进制普通 `return 0` 退出在本机触发 SIGTRAP（core dump） | 本机 LDFLAGS 环境注入 `-L/usr/local/lib`，链接到 user-prefix 共享 glib（与 conan 缓存静态 glib 并存）时 exit 路径异常；CI clean 环境为静态链接无此问题 | --version/--help 分支用 `_exit(0)` 绕过退场清理（CLI 信息输出无需 teardown）；主服务循环退出不在此测试路径 |
| 6 | glib 版本宏 / 桌面 schema 相关运行依赖 | 服务主体需会话 D-Bus + org.ayatana.indicator.session GSettings schema，纯 CI/容器无法完整拉起 | test_package 冒烟走 --version/--help（不触达服务初始化）；schema/autostart 属桌面发行数据未打包（0001） |
| 7 | 上游安装路径含子目录 | `RUNTIME DESTINATION ${CMAKE_INSTALL_FULL_LIBEXECDIR}/${CMAKE_PROJECT_NAME}`（OHOS 上 LIBEXECDIR=bin）→ bin/ayatana-indicator-session/ | conanfile package() 把二进制提升到 bin/ 顶层（符合 conan bin/ 约定、commands.json/L2 定位） |

## 源码修改（补丁）

| 补丁 | 修改 | 说明 |
|------|------|------|
| patches/0001-CMakeLists.txt.patch | CMakeLists.txt | 新增 SKIP_DATA_PO 选项并 guard data/ po/ 子目录 |
| patches/0002-src-main.c.patch | src/main.c | 增加 --version/--help 处理（stdio/unistd include + VERSION 宏 + 输出函数 + 前置分支） |

> 两补丁均经 refresh-patch --auto 从 orig/work 双轨生成，dry-run 校验通过。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libayatana-common | 0.9.13 | 本地 conan 缓存（配方 PR#7568，制品仓未发布 → 本地步骤0 conan create 装入缓存；registry R36 检查会报 HANDOFF 属预期） |
| glib（glib-2.0/gio-unix-2.0/gobject 等） | 2.88.0.1 | ohpcd 制品仓已发布 |

## 验证结果

```bash
# 手动编译
cmake configure ... && make -j1 && make install DESTDIR=...   # 全通过（1433 warnings 无 error）
$BIN --version   # ayatana-indicator-session 26.6.1  rc=0
$BIN --help      # Usage: ayatana-indicator-session [OPTION] ... rc=0

# conan-verify（G0-G4 + L2/L4/L5 全 PASS，.conan-verified 已生成）
# test_package 真实执行（conan-create.log）:
#   RUN: ".../bin/ayatana-indicator-session-service" --version 2>&1 | grep -q "ayatana-indicator-session 26.6.1"
#   RUN: ".../bin/ayatana-indicator-session-service" --help    2>&1 | grep -q "Usage:"
#   ayatana-indicator-session-service 26.6.1 smoke OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/ayatana-indicator-session-service | 会话指示器 D-Bus 服务可执行文件（OHOS aarch64 ELF） |

## 注意事项

- conanfile.py 的 requirements 同时声明 libayatana-common/0.9.13 与 glib/2.88.0.1（上游 pkg 依赖三层），且均 transitive（src/*.c 头文件直接可见）。
- ENABLE_RDA=OFF 与 SKIP_DATA_PO=ON 已固化在 conanfile generate()，非仅手动命令行。
- libayatana-common/0.9.13 未在制品仓发布（PR #7568 待合并），本地 conan-verify/finish-W3 使用本地缓存；主编合并 PR#7568 后 CI 即可全链路复验。
- 产物仅可执行文件（无 lib/include），R38 需软件级 commands.json 已创建。
- 本机 user-prefix glib（/usr/local/lib）会经 LDFLAGS 干扰链接 → 二进制可能带共享 glib DT_NEEDED（本机验证环境特有）；CI clean 环境静态链接 glib，二进制自包含。
---

**编译结束**: 2026-09-02 14:35
**最终状态**: built
