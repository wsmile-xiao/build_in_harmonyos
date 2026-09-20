# knowthelist 2.3.1 — HarmonyOS PC 适配笔记

## 概述

knowthelist 2.3.1 是 Qt5 派对音乐播放器 GUI 应用（C++，qmake 构建），支持 DJ 模式
与混合模式混音播放、曲库管理（SQLite）、GStreamer 播放、taglib 标签读取。

- 上游: https://github.com/knowthelist/knowthelist (tag v2.3.1, commit 87eb5306)
- 构建系统: qmake（非 autotools！src.pro: QT += core gui xml sql widgets;
  CONFIG += link_pkgconfig; PKGCONFIG += gstreamer-1.0 taglib alsa）
- 产物: bin/knowthelist（GUI 应用，arm64 ELF PIE）

## 编译结果

✅ **编译成功**。qmake + make 生成 `knowthelist`（5.3MB，arm64 ELF，PIE，动态链接 Qt5 与 alsa，
静态链接 gstreamer/taglib/glib）。staging 安装验证通过（bin + pixmaps + desktop）。

### 关键构建命令（探索阶段实测）

```bash
# 环境（探索用，正式配方由 conanfile.py generate() 注入）
export QT=<qt pkg>; export PATH=$QT/bin:$PATH
export PKG_CONFIG_PATH=<PkgConfigDeps 私有 prefix>   # R49
qmake QMAKE_PKG_CONFIG=pkg-config src.pro   # 必须在 src/ 目录下执行（.pro 内 ../locale 相对路径）
make -j1                                     # 必须 -j1：HMDFS 上并行 mkfifo 报 Operation not permitted
make install INSTALL_ROOT=$TEST_PREFIX
```

### 三个必须绕开的坑（均已固化为 conanfile.py）

1. **qmake 交叉编译禁用 pkg-config**：Qt5 mkspec `qt_functions.prf` 在 cross_compile 且
   PKG_CONFIG_LIBDIR/PKG_CONFIG_SYSROOT_DIR 未设时报
   `Cross compiling without sysroot. Disabling pkg-config.` → 必须传
   `QMAKE_PKG_CONFIG=pkg-config`（配方 build() 已传）。
2. **qt/5.15.19 无 lrelease**：上游 src.pro 有 TRANSLATIONS（9 个 .ts），Makefile 生成
   lrelease 目标。qt 包 bin/ 无 lrelease（只有 moc/uic/rcc/qmake）。配方 build()
   用 Python 生成**合法空 .qm**（Qt5 qm v3 头，0 context/0 message，20 字节），
   QTranslator::load 接受空翻译 → 界面回退英文（上游主语言）。这是翻译数据缺失
   而非平台适配 stub（R8 不适用——非 `#ifdef __OHOS__` 空壳），已在配方 docstring 说明。
3. **PkgConfigDeps 命名**：src.pro 的 PKGCONFIG 需求 `gstreamer-1.0`，但 conan 包名是
   `gstreamer`，PkgConfigDeps 生成 `gstreamer.pc` → 配方 generate() 复制出
   `gstreamer-1.0.pc` 别名。

### 依赖 .pc 非可重定位问题

gstreamer/glib 制品包的 `lib/pkgconfig/gstreamer-1.0.pc` 等 `prefix=/`（不可重定位），
taglib 的 .pc 指向旧的 build cache 路径。因此配方**不使用制品包内 .pc**，而是用
`PkgConfigDeps` 在 `build_folder/generators`（R49 私有 prefix）生成可重定位 .pc，
PKG_CONFIG_PATH 指向该目录。

## ⚠️ 运行时崩溃点（R34 必须如实记录）— 完整证据链

上游 `src/main.cpp:64` 强制检查 `QSqlDatabase::drivers().contains("QSQLITE")`，缺失则弹错
`QMessageBox::critical("Unable to load database")` 并 `return 1`（main.cpp:88 使用
`addDatabase("QSQLITE")`）。

制品仓发布的 `qt/5.15.19`（`qt/5.15.19.1` 同样）configure 带 `-no-sql-sqlite`
（`qt5/5.15.19` 配方带 `-no-feature-sql`），**无 QSQLITE 插件**。

### 独立验证证据（本任务实测，非引用）

```
1) conan download qt/5.15.19 -r=ohpcd 后检查制品包内容:
   $ ls <qt pkg>/plugins/            → bearer generic imageformats platforms   （无 sqldrivers/）
   $ ls <qt pkg>/plugins/sqldrivers/ → No such file or directory               （目录不存在）
   $ ls <qt pkg>/include/QtSql/      → QSql QSqlDatabase QSqlError ...          （头文件存在）
   $ ls <qt pkg>/lib/libQt5Sql.so*   → libQt5Sql.so libQt5Sql.so.5 ...          （库存在）

2) 运行时实测（链接 libQt5Sql 的独立探针程序）:
   QSqlDatabase::drivers() → ()     # 空列表！无任何 SQL 驱动注册
   （探针源码与运行输出留档于探索工作区 $TMPDIR/ktl-deps/sqldrv-test/）

3) knowthelist 二进制实测（-platform offscreen, timeout 8s）:
   输出: localization load ":knowthelist_en_US.qm result:" false
         QFontDatabase: Cannot find font directory ...（弹窗创建触发）
         This plugin does not support propagateSizeHints()
   EXIT=124（阻塞于 main.cpp:64 的 QMessageBox，offscreen 弹窗无法关闭）
   → 应用启动后卡死在 QSQLITE 驱动检查点，无法进入主界面（未打印 "load database:"）。

结论: 编译通过，但运行必然在 main.cpp:64 失败。这是制品仓 qt 包缺 QSQLITE 插件的
平台限制（非本包配方问题）。test_package 如实记录（期望退出码 124 或 1）。
```

## R51 上游测试清点（申报表）

| 项 | 清点结果 | 证据 |
|----|---------|------|
| tests/ 目录数 | **0** | `find . -type d -name tests -o -name test` → 无输出 |
| QTest/QTEST 引用 | **0** | `grep -rln "QTest\|QTEST\|testlib" --include=*.pro --include=*.cpp --include=*.h` → 无输出 |
| QT += testlib | **0** | src.pro 仅 `QT += core gui xml sql` (+qt5 widgets)，无 testlib |
| make check 目标 | **0**（qmake 默认空目标） | Makefile `check: first`，`make check` → "Nothing to be done for 'check'" |
| ctest/pytest 注册 | **0** | 非 CMake/非 Python 项目，无 ctest/pytest 配置文件 |
| dist/knowthelist.spec | 打包描述 | 仅 RPM spec（%build 为 qmake-qt5 + make），非测试 |

**结论：上游 2.3.1 无任何测试**（0 个测试目录 + 0 个注册测试）。test_package 的
test.sh 是消费者视角冒烟测试（R34：真实运行 knowthelist 二进制并记录 QSQLITE
崩溃点行为），非上游测试。

## test_package 运行结果

`conan create` 自动执行 test_package/test.sh：
- 找到 `knowthelist` 二进制（PATH）
- 运行 `knowthelist -platform offscreen`（timeout 8s）
- 期望退出码 124（QMessageBox 阻塞）或 1（QSQLITE 缺失退出）= 二进制真实启动并
  运行至 main.cpp:64 检查点
- 退出码 0 视为异常（未走到检查点）

## 已发布的依赖（W0 验证，conan download 确认）

| 依赖 | 版本 | 制品仓 |
|------|------|--------|
| qt | 5.15.19 | ohpcd ✅（含 qmake/Qt5 库/头/mkspecs/plugins/platforms） |
| gstreamer | 1.28.3 | ohpcd ✅（lib/pkgconfig/gstreamer-1.0.pc） |
| taglib | 1.13.1 | ohpcd ✅（lib/pkgconfig/taglib.pc） |
| alsa-lib | 1.2.16 | ohpcd ✅（lib/pkgconfig/alsa.pc） |

依赖注入全部使用 build_folder 私有 prefix（R49），不碰共享 /usr/local。

## 遗留事项

- 制品仓 qt/5.15.19 无 QSQLITE 插件 → knowthelist 运行时无法启动。若需真正运行，
  需先发布含 sqlite 驱动的 qt 适配包（如 qt/5.15.19.2 补 -plugin-sql-sqlite）或打补丁
  绕过 main.cpp:64 检查（后者属功能降级，不建议）。
- 翻译 .qm 为合法空文件，界面为英文（上游主语言）。
---

**编译结束**: 2026-09-19 14:29
**最终状态**: built
