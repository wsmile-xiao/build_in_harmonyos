# libopenrazer 0.4.0 适配笔记

## 编译环境
- 构建系统: meson（C++17）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（OHOS SDK aarch64）
- 状态: built

## 编译步骤

```bash
# 依赖注入：qtbase/6.11.1.2（Qt6 Core/DBus/Gui/Xml）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=.../ohos-aarch64

# meson 定位 Qt6：必须设置 QT6_QMAKE 指向 qtbase 的 qmake6，
# 并把 qtbase bin/（qmake6）+ libexec/（moc/rcc/uic）加入 PATH，
# qtbase lib 及传递依赖 lib 加入 LD_LIBRARY_PATH（qmake6 运行时需要）。
export QT6_QMAKE=<qtbase>/bin/qmake6
export PATH=<qtbase>/bin:<qtbase>/libexec:$PATH
export LD_LIBRARY_PATH=<qtbase>/lib:<deps>/lib:$LD_LIBRARY_PATH

meson setup build-test --prefix=$DEFAULT_PREFIX -Ddemo=false
meson compile -C build-test
meson install -C build-test --destdir $TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson setup 报 `Executables created by cpp compiler clang++ are not runnable` | 系统 LD_LIBRARY_PATH 中 `/system/lib64` 前有前导空格，加载器找不到 libc++_shared.so，meson sanity check 二进制无法运行 | 显式设置干净的 LD_LIBRARY_PATH（含 /system/lib64），或经 conan 环境注入 |
| 2 | meson 编译报 `'QDBusInterface' file not found` | meson 的 qt6 模块经 pkg-config 消费 qtbase 包内自带 Qt6*.pc，其 prefix 指向构建机 `.cache` 旧路径（本机不存在） | 显式设置 `QT6_QMAKE` 环境变量，强制 meson 走 qmake 定位 Qt6（日志确认 `Run-time dependency qt6 found: YES (qmake)`） |
| 3 | meson setup 报 `qt.compile_translations: lrelease not found` | 上游 translations 子目录依赖 lrelease（Qt LinguistTools），qtbase 制品仓不提供该工具 | patch 跳过 translations 子目录（0001-meson.build.patch）。翻译文件仅影响界面本地化，不影响库核心功能（D-Bus wrapper API） |

## 源码修改

- `patches/0001-meson.build.patch`：注释 `subdir('translations')`，跳过需要 lrelease 的翻译编译。

## 依赖版本

| 软件 | 版本 | 用途 |
|------|------|------|
| qtbase | 6.11.1.2 | Qt6 Core/DBus/Gui/Xml（制品仓已发布） |
| meson | 1.11.0 | 构建工具（tool_requires） |

## 验证结果

```bash
# meson 编译 18/18 全部通过，libopenrazer.so.0.4.0 链接成功
# 安装产物：libopenrazer.so.0.4.0（+ .so.0/.so 符号链接）、
#           头文件 include/libopenrazer*.h、pkg-config libopenrazer.pc
# 上游测试：meson.build 无 test() 注册，上游测试用例数 = 0
# 自研 test_package：7 项断言（效果枚举表/元类型注册/Manager 构造/
#   isDaemonRunning 无 daemon 安全返回/DBusException name/message/元类型反查）
# 适配完整性说明（R40）：libopenrazer 为 Qt/D-Bus 客户端 wrapper 库（非图形/
#   多媒体/外设类），test_package 覆盖无 daemon 环境的 API 面；真实 D-Bus 调用
#   路径依赖 OpenRazer daemon（CI 不可用），未覆盖。
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 构建配方，依赖 qtbase/6.11.1.2 |
| conandata.yml | 源码 URL + SHA256 + 补丁声明 |
| patches/0001-meson.build.patch | 跳过 translations 子目录 |
| test_package/ | 消费者冒烟测试（7 断言） |

## 注意事项

- qtbase 包内自带 Qt6*.pc 的 prefix 指向构建机 `.cache` 路径，任何经 pkg-config 消费 Qt6 的下游软件都可能踩坑，应优先走 QT6_QMAKE / qmake 定位。
- 本包依赖 qtbase/6.11.1.2（含 DBus 模块）；若下游需要 translations 本地化文件，需另行适配 qt6linguisttools（lrelease）。
---

**编译结束**: 2026-09-16 02:57
**最终状态**: built
