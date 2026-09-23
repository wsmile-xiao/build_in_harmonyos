# qt5-qtcharts 5.15.2 编译笔记

## 编译环境
- 平台: aarch64-linux-ohos (鸿蒙)
- 编译器: clang++ (OHOS SDK)
- Qt5版本: 5.15.2 (已安装在 ~/usr/local/Qt5/)
- 构建系统: qmake

## 依赖
- qt5-qtbase 5.15.2.2 (Qt Core, Gui, Widgets, Network)
- qt5-qtdeclarative 5.15.2 (Qml, Quick, QmlModels)

## 编译步骤

### 1. 设置环境
```bash
export PATH=/storage/Users/currentUser/usr/local/Qt5/bin:$PATH
export QTDIR=/storage/Users/currentUser/usr/local/Qt5
```

### 2. qmake配置
```bash
cd ~/tmp/qt5-qtcharts-src
/storage/Users/currentUser/usr/local/Qt5/bin/qmake qtcharts.pro
```
成功，生成了.qmake.stash和.qmake.cache文件。

### 3. 编译
```bash
make -j2
```
成功完成，耗时约478秒。有一个deprecation warning（createTextureFromId -> createTextureFromNativeObject），不影响编译。

### 4. 安装
```bash
make install
```
安装到 ~/usr/local/Qt5/，包括：
- libQt5Charts.so.5.15.2（2198080 bytes，**未 strip**——见下方「打包关键点 §2」，
  在鸿蒙 aarch64 上 strip 会破坏动态符号表导致加载失败）
- libQt5Charts.prl, libQt5Charts.la
- Qt5Charts.pc (pkgconfig)
- Qt5Charts headers (include/QtCharts/)
- qt_lib_charts.pri, qt_lib_charts_private.pri
- Qt5Charts cmake config
- QML plugin: qml/QtCharts/libqtchartsqml2.so
- QML types: qml/QtCharts/plugins.qmltypes, qmldir
- Designer QML files

> 注：本节记录的是早期手工 `~/usr/local/Qt5` 验证流程，仅作历史留档。
> 最终交付形态是 Conan 包（见下方「打包关键点」），不再使用该手工 prefix。

## 安装产物验证
- `file libQt5Charts.so.5.15.2`: ELF 64-bit LSB shared object, ARM aarch64,
  dynamically linked, **not stripped** ✅（2198080 bytes）
- 所有头文件正确安装 ✅
- pkgconfig文件正确安装 ✅
- QML插件正确安装 ✅

## 无源码修改
本次编译无需修改任何上游源码，直接使用原始 v5.15.2 源码即可编译通过。
配方不携带任何补丁（`conandata.yml` 的 `patches` 为空，`manifest.yaml` 的
`patches: none`）。

> 更正记录：早期自动补丁生成器曾在归档里留下 8 个「补丁」文件，与本节声明矛盾。
> 经核对，那 8 个目标文件全部**不存在于上游 tarball**——它们是 qmake 在构建目录
> 生成的产物（`QtCharts.version{,.in}` / `*_wrapper.sh` / `.qmake.stash` /
> `QtChartsDepends`），其中 4 个硬编码了本机临时前缀
> `/storage/Users/currentUser/tmp/qt5charts-prefix`，`.qmake.stash` 还冻结了
> 特定 SDK（ohos-sdk_26.0.0.18）与 clang 15.0.4 版本。它们既非源码修改，
> 也从未参与构建（`patches: {}` 使 `apply_conandata_patches` 实为 no-op）。
> 已于 W4 审计打回后全部删除，本节声明现与归档实际状态一致。

## 打包关键点（conanfile.py package()）

### 1. 必须用 `make install INSTALL_ROOT=`，不能手工 copy 构建树
qmake 在**构建树** `include/QtCharts/` 下放的 55 个小写 `.h` 都是转发桩，
内容形如 `#include "../../src/charts/qchart.h"`；private 桩在
`include/QtCharts/5.15.2/QtCharts/private/` 下，形如
`#include "../../../../../src/charts/qchart_p.h"`。
把这些桩打进包，就必须连 51MB 的 `src/` 构建树一起打包，下游才能编译（旧配方做法，包 56MB）。

改用 qmake 自带的安装流程后，`install_gen_headers` / `install_targ_headers` /
`install_private_headers` 会把 `src/charts/` 下**真实**头文件装到
`QT_INSTALL_HEADERS/QtCharts`（真实头用 `<QtCharts/...>` 尖括号引用，自包含），
同时装好 `.so`+符号链接、`.prl`/`.la`/`Qt5Charts.pc`、
`mkspecs/modules/qt_lib_charts{,_private}.pri`、Qt5Charts cmake config、
`qml/QtCharts/` 插件。结果：包 6.0MB、无 `src/`、头文件自包含。

Qt 模块装进的是 **qtbase 的 prefix**（`QT_INSTALL_PREFIX`），所以
`INSTALL_ROOT=<tmp>` 后产物落在 `<tmp>/<qtbase 包路径>/`，再把其下
`lib/ include/ qml/ mkspecs/ plugins/` 搬到 `self.package_folder`
（`copytree(symlinks=True)` 保住 `libQt5Charts.so -> .so.5.15.2` SONAME 链）。
`/tmp` 在鸿蒙上只读（E002），INSTALL_ROOT 必须落在 build_folder 内。

### 2. `make install` 必须带 `STRIP=true`（关键陷阱）
qmake 的 `install_target` 规则对已安装的 `.so` 执行 `strip --strip-unneeded`。
在鸿蒙 aarch64 上这一步会**静默破坏动态符号表**：`readelf --dyn-syms` 里
5155 个符号（含 `_ZN8QtCharts11QLineSeriesC1EP7QObject`）看起来都在，但加载器拒绝该库：
```
Error loading shared library libQt5Charts.so.5: (needed by ./test_qt5_qtcharts)
Error relocating ./test_qt5_qtcharts: _ZN8QtCharts11QLineSeriesC1EP7QObject: symbol not found
... (每个 QtCharts 符号都 symbol not found)
```
对照实验：未 strip 的 2198080 字节库 test 退出码 0；同一库 `strip --strip-unneeded`
后变 1669192 字节，test 退出码 127。故 `make install ... STRIP=true`
（与 `build()` 里 `make QMAKE_STRIP=""` 同因）。

### 3. `.pc` / `.la` 的 prefix 需回指本包
`Qt5Charts.pc` 的 `prefix=` 和 `libQt5Charts.la` 的 `libdir=` 被写成 qtbase 的
包路径（因为 Qt 模块名义上装进 Qt prefix）。package() 末尾把这两处改为
`self.package_folder`；其余指向 qtbase 的 `-L/-l`（Qt5Core/Gui/Widgets）保持原样，
因为那些库确实住在 qtbase 包里。

## 适配过程记录

### 对话 #1 — 源码编译打通
qmake 构建体系（qtcharts.pro）。依赖 qt5-qtbase/5.15.2.2 与
qt5-qtdeclarative/5.15.2 均已发布至 ohpcd 制品仓，直接从 conan 包取
qmake 与 mkspecs。产物 `lib/libQt5Charts.so.5.15.2` 编译通过。

### 对话 #2 — Conan 配方与门禁
补齐 conanfile.py / conandata.yml（官方 sha256 校验）/ test_package。
test_package 初期 `find_package(Qt5Core)` 失败：qt5-qtbase 仅生成聚合
`Qt5Config.cmake`，不产出 per-component config。改为链接顶层
`qt5-qtbase::qt5-qtbase` target（与已发布的 qt5-qtdeclarative 同一模式）后
conan-verify 8 道门禁（G0-G4 + L2/L4/L5）全部 PASS。

### 对话 #3 — 主编质量检查打回（缺陷 1：QML 插件缺失）
审计发现包内缺少 manifest 声明的 `libqtchartsqml2.so`。根因：
`_fix_qtbase_paths()` 重写 qtdeclarative 的 `mkspecs/modules*.pri` 时用的正则
只匹配 `.conan2/p/b/...`，未覆盖 `.cache/conan2/p/b/...` 形态 → 旧构建目录路径
残留 → qmake 报 `Cannot read .../qt_lib_qml.pri` → `qtHaveModule(quick)` 失败 →
`src/src.pro` 的 `SUBDIRS += chartsqml2` 被静默跳过。
修复：提取类级 `_BUILD_DIR_PATTERN` 宽版正则（同时覆盖两种形态），两处调用点统一使用。

### 对话 #4 — 主编质量检查打回（缺陷 2：包体积膨胀 56MB）
`package()` 把整个构建树 `src/`（Makefile/.moc/目标文件，约 51MB）拷入包。
直接删除 `src/` 后 test_package 编译失败：qmake 生成的 `include/QtCharts/*.h`
全部是转发桩（`#include "../../src/charts/qchart.h"`），私有头桩位于
`include/QtCharts/5.15.2/QtCharts/private/`，均依赖构建树相对路径。
修复：改用 Qt 惯用 `make install INSTALL_ROOT=<tmp>` 落地 syncqt 处理后的真实
头文件，再搬迁 lib/ include/ qml/ mkspecs/ plugins/ 到 package_folder。
结果：包体积 56MB → 6.0MB，55 个公开头 + 162 个私有头全部自包含（0 个残留
`../../src` 引用），`qml/QtCharts/libqtchartsqml2.so` + `qmldir` 在位。

### 对话 #5 — 补跑上游 tests/auto 套件

此前本配方未执行上游测试套件（`MANIFEST.yml` 以「CI 45 分钟硬超时」申报豁免）。
本次按路径 B Step 2 要求实测补跑，结果如下。

**构建测试套件**

用 qmake 生成 `tests/auto` 的 Makefile 并编译，得到 29 个可执行测试程序。

踩坑：首次用 `qt5-q828d2380abd85` 那份 qtbase 的 qmake，报
`Project ERROR: Unknown module(s) in QT: core gui testlib widgets`。根因是该包
`bin/qt.conf` 的 `Prefix` 指向一个**已被删除**的构建目录
（`.conan2/p/b/qt5-qb50cf451f6ac0/p`），qmake 因此解析不到 mkspecs。
换用自洽的 `qt5-q9ce0d1d008b3f`（`Prefix` 指向自身、84 个 modules）后
qmake 零告警通过，`make -j4` 退出码 0。

这个坑同时印证了 W4 审计的 P1 结论：配方 `_fix_qtbase_paths()` 就地改写依赖包
的 `qt.conf` / `mkspecs`，会把依赖包污染成不自洽状态。

**运行结果（QT_QPA_PLATFORM=offscreen）**

```
28 passed / 1 failed / 0 crashed  （共 29 个测试程序）
断言级：1237 passed, 0 failed, 28 skipped
```

全部 28 个通过的用例覆盖 QChart / QChartView / 各 series（line/spline/scatter/
bar/pie/area/candlestick 及 horizontal 系列）/ 各 axis（value/logvalue/category/
barcategory/datetime）/ QLegend / 各 modelmapper / QML（tst_qml 66 断言全通）。

唯一失败项 `tst_qml-qtquicktest`，**非 qtcharts 缺陷**：

```
tst_barcategoryaxis.qml:38:5: Type TestCase unavailable
.../qt5-q6aab6a1d72ddf/p/qml/QtTest/TestCase.qml: No such file or directory
```

即上游 qt5-qtdeclarative 包只装了 `qml/QtTest/libqmltestplugin.so` + `qmldir`，
漏装了同目录的 `TestCase.qml` 等 QML 文件（源码树
`src/qmltest/TestCase.qml` 确实存在，说明是 qtdeclarative 的打包遗漏）。
本测试依赖该文件，故与 qtcharts 本身无关；已记为 qt5-qtdeclarative 的待修项。

日志留档：`.ci_logs/upstream-tests-auto-build.log`、
`.ci_logs/upstream-tests-auto-run.log`。

复现命令：

```bash
B=<qtcharts build dir>; Q=<自洽的 qtbase 包>; QD=<qtdeclarative 包>
cd $B/tests && $Q/bin/qmake auto/auto.pro -o Makefile.auto && make -f Makefile.auto -j4
env QT_QPA_PLATFORM=offscreen QT_PLUGIN_PATH="$Q/plugins:$QD/plugins" \
    QML2_IMPORT_PATH="$QD/qml:$B/qml" LD_LIBRARY_PATH="$B/lib:$Q/lib:$QD/lib" \
    ./<case>/tst_<case>
```

**结论**：上游测试套件在 OHOS aarch64 + offscreen 下实际可跑且 1237 条断言全通，
原「CI 时限」豁免仅适用于 `conan create` 阶段（全套构建+运行约 5 分钟，仍不宜
塞进 CI 的 45 分钟预算内与其他门禁争抢），但豁免理由不应被解读为"测试不可运行"。
`MANIFEST.yml` 已据此更新为「本地实测通过 + 不在 build() 中执行」。

## 编译结束
**最终状态**: built

## 与 main:5.15.2.1 的版本对账说明（2026-09-17 续跑时补充）

本分支（feat/qt5-qtcharts-5.15.2，PR #4630，2026-08-07 起）是 qt5-qtcharts
上游 5.15.2 的**原始完整适配分支**；2026-09-02 积分赛（goblinrs）将该分支
成熟形态 fork 改号为 **5.15.2.1** 合入 main 并发布制品仓（rev 988d2e12）。
经全目录 diff 核实，main:5.15.2.1 与本分支 5.15.2 仅版本标识差异
（32 行：版本号/docstring/时间戳），无任何功能性差异。

main 上的 `archives/q/qt5-qtcharts/5.15.2/` 目录当前仅为早期占位
（只有 manifest.yaml + notes.md，无 conanfile/conandata/test_package）。
本 PR 合入后将以完整配方补齐该目录。**后续维护决策**（超出本 PR 职权，
留给主编/维护者）：鉴于 5.15.2.1 已发布制品仓，可择一保留——
(a) 以本 PR 的 5.15.2 为准、删除 main:5.15.2.1（需同步制品仓）；
(b) 以已发布的 5.15.2.1 为准、本 PR 仅作归档合入不再发布 5.15.2。
两者取一即可消除重复，版本线即可收敛。

---


**编译结束**: 2026-09-17 17:27
**最终状态**: built
