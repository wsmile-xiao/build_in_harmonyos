# E643: KF6/KDE 配方在「无法执行目标平台二进制」宿主机上的构建期阻塞（configure 期 ECM qtpaths / build 期 AUTOMOC moc）

> 草稿状态：pending-editor-review（最终编号由主编确认）
> 交付实例：libkcddb 26.04.0（任务 #8241，PR !11783）
> 相邻条目：E429 / E543（同为 qtpaths 故障，**退出码与根因不同，修法互不适用**）

## 错误特征

在**非 OHOS 的 x86-64 宿主机**（普通 Linux / WSL2）上交叉构建 KF6 / KDE Gear 配方：

```
# 第一处：configure 期（必然命中，凡 include KDEInstallDirs）
CMake Warning at .../ECM/modules/ECMQueryQt.cmake:97 (message):
  Failed call: .../qtbase/6.11.1/p/bin/qtpaths
  --query QT_INSTALL_PREFIX
CMake Error at .../ECM/modules/ECMQueryQt.cmake:98 (message):
  Qt6 qtpaths call failed: 255
Call Stack (most recent call first):
  .../ECM/kde-modules/KDEInstallDirs6.cmake:210 (ecm_query_qt)
  .../ECM/kde-modules/KDEInstallDirs.cmake:17 (include)
  CMakeLists.txt:17 (include)
```

```
# 第二处：build 期（凡含 QObject 头，AUTOMOC 必然命中）
AutoMoc subprocess error
  The moc process failed to compile "SRC:/libkcddb/client.h" ...
  Process failed with return value 255
  Command: .../qtbase/6.11.1/p/libexec/moc -D... -o .../moc_client.cpp .../client.h
  Output: aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1': No such file or directory
```

## 根因

KF6/KDE 的构建面在**两个不同阶段**各要求执行一次**目标平台（aarch64 OHOS）**二进制：

1. **configure 期**：`KDEInstallDirs6.cmake:210` → `ecm_query_qt(qt_install_prefix_dir QT_INSTALL_PREFIX)`；
   `ECMQueryQt.cmake` 用 `get_target_property(_qtpaths_executable Qt6::qtpaths LOCATION)`
   取路径后 `execute_process` 运行。conan 的 `Qt6::qtpaths` 指向**目标包** qtbase 的
   `bin/qtpaths`（`Machine: AArch64`，`INTERP: /lib/ld-musl-aarch64.so.1`）。
   ECMQueryQt **没有 cache 变量逃生口**（`QUERY_EXECUTABLE` 只能来自 target 属性），
   因此 `-DQT_INSTALL_PREFIX=...` 一类的预置无效。
2. **build 期**：`CMAKE_AUTOMOC` 执行 `$qtbase/libexec/moc`，同样是 aarch64 OHOS 动态 ELF。
   失败点晚于 configure，容易被误判为源码/补丁问题。

宿主机没有 aarch64 musl 动态加载器，因此两处都直接失败（exit 255）。**为什么加载器拿不到**（三条实测）：

- OHOS SDK **不提供**可用的 `ld-musl-aarch64.so.1`；唯一近似物是
  `native/sysroot/usr/lib/aarch64-linux-ohos/libc.so`（musl，`static-pie`），
  把它当加载器交给 `qemu-aarch64-static -L`，运行**最小**的 aarch64-linux-ohos
  **动态** `hello world` 即 `uncaught target signal 11`；同程序 `-static` 编译后正常运行
  → 失败点是「OHOS musl 加载器 × QEMU」组合，不是被测程序；
- 换用非 OHOS 的 musl 加载器（Debian `musl:arm64` 的 `ld-musl-aarch64.so.1`）后 QEMU 不再
  段错误，但 OHOS 侧产出的 `libc++_shared.so` / `libQt6Core.so.6` 出现大量
  `Error relocating ... symbol not found`（`__cxa_guard_acquire`、`_Znwm`、
  `_ZTVN10__cxxabiv1…` 等）→ 不能作为运行时替代；
- 因此「给 binfmt/QEMU 补一个加载器」这条路在本机不成立。

## 与 E429 / E543 的分诊（重要）

| 现象 | 根因 | 正确处置 |
|---|---|---|
| `Qt6 qtpaths call failed: 127` + `Error loading shared library libc++_shared.so` | qtpaths **能启动**，但 OHOS 沙箱 `LD_LIBRARY_PATH` 中不兼容的 libc++ 遮蔽了 `/system/lib64` 的兼容版 | **E429 / E543**：向 `LD_LIBRARY_PATH` 前置 `/system/lib64` 与 SDK `llvm/lib` |
| `Qt6 qtpaths call failed: 255` + `Could not open '/lib/ld-musl-aarch64.so.1'` | 宿主机**根本不能执行** aarch64 动态产物（没有加载器），与 libc++ 无关 | **本条目**：注入 `LD_LIBRARY_PATH` 无效；不要改配方，改验证边界 |
| `AutoMoc subprocess error ... return value 255` | 同上，只是换成 moc | 本条目 |

## 为什么不能用 E456 / E495 的宿主工具方案

`conan list "qtbase/6.11.1:*" -r ohpcd` 实测：制品仓中 qtbase 每个版本**只有一个 package**，
settings 为 `os=OHOS, arch=armv8, compiler=clang, compiler.version=15, compiler.libcxx=libc++`
——**本生态不存在宿主（x86-64）Qt**。因此：

- **E456**（Qt5/Windows：提供 native `moc`/`rcc`/`uic` 并注入 `CMAKE_AUTOMOC_EXECUTABLE`
  等）——拿不到宿主 Qt，方案不适用；用系统发行版 Qt（如 6.4）的 moc 代跑 6.11 的目标构建
  属于伪验证（见红线）。
- **E495**（设 `QT_HOST_PATH` 指向宿主 Qt 前缀）——同样没有宿主 Qt 前缀可指。

结论：这类配方的**编译与测试只能在能执行 aarch64 目标产物的环境**（官方 CI worker / OHOS 沙箱）
完成。配方本身没有问题：同一份配方与补丁在 CI 上可正常编译并跑上游 CTest
（同族归档 `libkcddb/26.04.3` 已由 CI 构建并合入）。

## 推荐方案：归因 → 不改配方 → 降级本地验证目标 → 交 CI

1. **归因（10 分钟）**：先看 `qtpaths call failed: <N>` 的 N —— 127 且伴随
   `Error loading shared library` → 走 E429/E543；255/126 或伴随
   `Could not open '/lib/ld-musl-aarch64.so.1'` → 本条。再用
   `readelf -h $qtbase/bin/qtpaths | grep Machine` 与 `readelf -l … | grep INTERP` 坐实。
2. **不要为了本地跑通改配方**：配方在 CI 上是好的；引入宿主工具替换会污染归档（红线 1、2）。
3. **把本地验证目标降级为「配置面 + 源码等价性」**：
   - **配置面**：可用宿主侧 `qtpaths` 桩把 `cmake.configure()` 走通。
     `KDEInstallDirs6` 只有 `QT_INSTALL_PREFIX` 是**无条件**查询的（`QT_INSTALL_PLUGINS/QML`
     仅在 `_qt_prefix_is_cmake_install_prefix` 为真时查，`QT_INSTALL_DOCS` 仅在建文档时查），
     而 Qt6 是可重定位安装，真实 qtpaths 对 `QT_INSTALL_PREFIX` 返回的就是 qtbase 包目录本身，
     所以桩只需逐项回包内路径即与真实行为等价。实测：桩到位后 configure/generate 全过，
     `package_id` 计算与同族 26.04.3 一致。**桩只用于本地定位，绝不进交付面。**
   - **源码等价性**：用同族已归档版本做「编译面逐字节等价」证明（见 E644）。
4. **真实编译与测试交 CI**，PR 中如实申报本地验证边界与结论来源，不伪造本地执行结果。

## 回退方案

若既无法在目标环境构建、又需要本地证据链：以「同族已归档版本（CI 已验证）+ 同一补丁 →
打补丁后全树 `diff -rq`」给出编译面等价性证明（E644），明确写出「编译/测试结论以 CI 为准」。

## 红线

- **禁止**用宿主发行版 Qt 的 `moc`/`rcc`/`uic` 冒充目标 Qt 的构建期工具——moc 输出必须由
  与被构建 Qt 同版本的工具生成，否则得到的是「能编过但语义可能不匹配」的伪验证。
- **禁止**把 `qtpaths` 桩写进交付配方（CI/设备端真 qtpaths 可用，桩会让 KDEInstallDirs
  算出错误的插件/QML 目录）。
- **禁止**用桩或静态检查冒充测试通过；本场景下测试二进制同样无法在宿主执行，必须如实申报。

## 实证记录

| 项目 | 内容 |
|----|------|
| 交付实例 | libkcddb 26.04.0（archives/l/libkcddb/26.04.0，PR !11783） |
| 宿主 | x86-64 Ubuntu 24.04（WSL2）+ Conan 2.29.1 + OHOS SDK v7.0（clang 15.0.4） |
| 失败 1 | `CMake Error at ECMQueryQt.cmake:98: Qt6 qtpaths call failed: 255`（configure 期） |
| 失败 2 | `AutoMoc subprocess error … moc_client.cpp … return value 255`（build 期） |
| 桩验证 | 宿主 qtpaths 桩到位后 configure/generate 全过；`package_id=08ff4866…` 与同族 26.04.3 相同 |
| 加载器实测 | OHOS musl 加载器 + QEMU 8.2.2：最小动态 hello `uncaught target signal 11`（`-static` 正常）；Debian musl 加载器：OHOS `libQt6Core.so.6` 大量符号重定位失败 |
| 生态事实 | `conan list "qtbase/6.11.1:*" -r ohpcd` → 唯一 package 为 `os=OHOS,arch=armv8`（无宿主 Qt） |
| 同族对照 | archives/l/libkcddb/26.04.3（CI 已验证并合入，源码树与本版本逐字节等价） |
| 草稿作者 | Zmaomao |
