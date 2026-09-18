# E581 — meson 的 qt6 模块经 pkg-config 消费 qtbase 自带 .pc 失败，须 QT6_QMAKE 走 qmake 定位

## 错误特征

meson 构建的软件依赖 qtbase（Qt6）时，`dependency('qt6', modules: ['Core', 'DBus', 'Gui', 'Xml'])` 解析失败，典型日志：

```
FAILED: [code=127] libopenrazer.so.0.4.0.p/moc_manager.cpp
In file included from .../moc_manager.cpp:9:
.../include/libopenrazer/manager.h:10:10: fatal error: 'QDBusInterface' file not found
#include <QDBusInterface>
```

meson setup 阶段可能表现为：

```
Program /storage/Users/xxx/.cache/conan2/p/b/qtbas*/p/bin/rcc found: NO
Program /storage/Users/xxx/.cache/conan2/p/b/qtbas*/p/libexec/rcc found: NO
```

即 meson 沿 pkg-config 找到的 Qt6 路径指向 `~/.cache/conan2/...`（构建制品时的机器路径），
该路径在消费者机器上不存在，头文件与 Qt 工具（moc/rcc/uic）全部落空。

## 触发条件

- 软件用 meson 构建，`meson.build` 含 `import('qt6')` 与 `dependency('qt6', modules: [...])`
- Qt6 依赖经 conan 制品仓 qtbase 提供（qtbase/6.11.x 等）
- 构建环境（conan create / 本地）中 pkg-config 优先被 meson 采用来解析 qt6

## 根因

qtbase 制品包内自带 `Qt6Core.pc` / `Qt6DBus.pc` 等 pkg-config 文件，其 `prefix=` 字段
写死为构建该制品时机器上的 conan 缓存绝对路径（形如
`/storage/Users/xxx/.cache/conan2/p/b/qtbas*/p`）。这些 .pc 文件随制品发布但路径
不可迁移——消费者机器上该目录不存在。

meson 的 qt6 模块解析顺序为：**qmake 优先，pkg-config 兜底**。当 `QT6_QMAKE`
环境变量未设置且 PATH 中无 qmake6 时，meson 回退到 pkg-config，拿到错误的
prefix 路径，导致：
1. include 路径错误 → `'QDBusInterface' file not found` 等编译失败
2. moc/rcc/uic 工具路径错误 → `moc found: NO`

## 解决方案

显式设置 `QT6_QMAKE` 指向 qtbase 包内 `bin/qmake6`，并把 qtbase 的 `bin/` 与
`libexec/`（moc/rcc/uic 所在）加入 PATH，qtbase lib 及传递依赖 lib 加入
LD_LIBRARY_PATH（qmake6 运行时需要 libc++_shared.so 等）：

```python
# conanfile.py build() 中（手动 meson 先例参照 c-rbtree/account-utils）
qt_prefix = self.dependencies["qtbase"].package_folder
env_prefix = (
    f"PATH={qt_prefix}/bin:{qt_prefix}/libexec:/data/service/hnp/bin:$PATH "
    f"QT6_QMAKE={qt_prefix}/bin/qmake6 "
    f"LD_LIBRARY_PATH={qt_prefix}/lib:<deps libs>:/system/lib64:..."
)
self.run(env_prefix + f" meson setup {build} {src} --buildtype=release -Ddemo=false --prefix=/", env="conanbuild")
self.run(env_prefix + f" meson compile -C {build} -j1", env="conanbuild")
```

成功标志：meson setup 输出

```
qmake6 found: YES (<qtbase>/bin/qmake6) 6.11.1
Run-time dependency qt6 (modules: Core, DBus, Gui, Xml) found: YES 6.11.1 (qmake)
```

## 验证证据

- libopenrazer 0.4.0 适配：不设 QT6_QMAKE 时 G2 conan create 连续失败
  （`'QDBusInterface' file not found` / `moc found: NO`）；按本方案注入
  QT6_QMAKE + PATH + LD_LIBRARY_PATH 后 meson setup 输出
  `qt6 found: YES (qmake)`，`meson compile` 18/18 通过，conan-verify G0-G4 全 PASS。
- 补充约束：meson sanity check 二进制运行还需 `/system/lib64`（libc++_shared.so）
  在 LD_LIBRARY_PATH，系统路径带前导空格会导致加载失败（本任务已处理）。

## 适用边界

- **适用**：meson 构建 + conan qtbase 依赖的 Qt6 软件；dependency('qt6') 场景
- **不适用**：CMake 构建（Qt6 经 CMakeDeps/Qt6Config.cmake 定位，见 E438/E495）；
  qtbase 无 qmake6 工具的场景（需回退方案或另配 qt6linguisttools）

## 关联条目

- E355：meson host_machine.system() 平台映射 + .pc prefix=/ 修正（同属 meson+.pc 问题族，但根因为 prefix=/ 而非 .cache 绝对路径）
- E438：Qt6 子模块复用 qtbase 的 Qt6Config 与 harmonyos-clang mkspec（CMake 场景）
- E495：Qt6 模块 CMake 构建报 QT_HOST_PATH（CMake 交叉编译场景）

## 来源

- source_event: libopenrazer 0.4.0 适配（G2 conan create 反复失败 4 轮后定位）
- 复现软件: libopenrazer 0.4.0（z3ntu/libopenrazer）
