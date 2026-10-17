# qt5-qtbase 包未做可重定位处理：qt.conf 与 mkspecs/**/*.pri 内嵌构建期路径，qmake 无法解析 Qt 模块（编译期第一道墙）

> Draft: `DRAFT-MLITE-055-QT5-QTBASE-BAKED-BUILDPATH-QMAKE`
> Stem: `mlite-0.5.5-qtbase-baked-buildpath-qmake` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MLITE-055-QT5-QTBASE-BAKED-BUILDPATH-QMAKE
- **严重度**: 3（3=🔴blocking / 2=🟡medium / 1=🟢minor）
- **类别**: qmake|qt5|relocatability|packaging
- **触发工具**: qmake
- **阶段**: configuration

## 错误特征

```
Cannot read .*mkspecs/modules-inst/qt_lib_.*\.pri|Unknown module\(s\) in QT:|Project ERROR: Unknown module\(s\) in QT
```

匹配关键词：`qmake, Unknown module(s) in QT, modules-inst, qt.conf, mkspecs, qt5-qtbase, .conan2/p/b, relocatable`

## 根因

qt5-qtbase 的 Qt5 构建把构建期前缀写死进 bin/qt.conf（[DevicePaths]/[Paths] Prefix）与 mkspecs/modules(-inst)/*.pri（QT_MODULE_*_BASE / include(...) 全部是绝对路径，形如 …/.conan2/p/b/qt5-qXXXX/b/…）。该构建目录在 conan 包上传后不存在，于是 qmake 加载 mkspecs 时所有 include 失败，报 “Cannot read …/modules-inst/qt_lib_*.pri” 并最终以 “Unknown module(s) in QT: core dbus” 终止——表面像 Qt 模块缺失，实为包不可重定位。

## 影响范围

所有以 qt5-qtbase 提供的 qmake 构建的 Qt5 项目（qmake/.pro 构建系统），尤其是消费 Qt5Core/Qt5DBus 组件的库。

## 验证命令

```bash
grep -rl "\.conan2/p/b/qt5-q" <qtbase_pkg>/mkspecs | head -3   # 命中即说明包内仍有构建期路径
```

## 处置建议

- **优先级**: 2
- **方案**: `fix-qtbase-relocatability-in-generate-or-build`
- **说明**: (1) 构建期改写 qtbase 包的 bin/qt.conf（[DevicePaths]/[Paths] Prefix/HostPrefix 指向 package_folder，TargetSpec/HostSpec=linux-clang）；(2) 递归改写 mkspecs/**/*.pri，把正则 /[^\s\"'()]*?/\.conan2/p/b/qt5-q[0-9a-f]+/b 前缀替换为 package_folder；(3) 改写后再调用 qmake，否则 Qt 模块解析必失败。(4) 反例警告：正则不要写成只匹配 /.conan2/...（贪婪前缀缺失会把 “/storage/Users/currentUser” 当匹配起点，替换后产生 /storage/Users/storage/Users/... 的重复前缀，症状与未修复完全一致）；已出现过一次，二次修复需把重复前缀一并纠正。参考实现：archives/l/libngf-qt/0.3.1（_fix_qtbase_paths）、archives/m/mlite/0.5.5。
- **参考命令**: `python3 -c "…改写 qt.conf 与 mkspecs/**/*.pri…"   # 见 archives/m/mlite/0.5.5/conanfile.py::_fix_qtbase_relocatability`
- **可自动修复**: false

## 可复用知识总结（同类问题通用）

- **问题类**：conan 包化后的 Qt5（qmake）依赖**不可重定位**——Qt 构建期前缀被写死进包内文件。
- **识别信号**：`qmake` 报 `Unknown module(s) in QT: …` 或 `Cannot read …/mkspecs/modules-inst/qt_lib_*.pri`；`grep -rl "\.conan2/p/b/qt5-q" <qtbase_pkg>/mkspecs` 有命中。
- **通用处置**：消费方配方在 `build()`/`generate()` 中改写 `bin/qt.conf`（Prefix/HostPrefix→package_folder，TargetSpec/HostSpec=linux-clang）与 `mkspecs/**/*.pri` 中的构建期前缀；正则须匹配**完整绝对路径**（写成 `/[^\s"'()]*?/\.conan2/p/b/qt5-q[0-9a-f]+/b`），否则会留下重复前缀（`/storage/Users/storage/Users/...`）而症状不变。
- **适用范围**：任何以 qt5-qtbase（或同类"构建期把前缀写入包内"）提供的 qmake 构建的 Qt5 项目。
- **关联**：`archives/l/libngf-qt/0.3.1`（先例实现）、本仓 qmake 存量 14 例（`build-systems.md §13`）。
