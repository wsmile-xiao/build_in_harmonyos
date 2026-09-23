# ksystemlog 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake (CMakeToolchain via conan)
- 编译日期: 2026-09-20
- 编译器: clang 15 (OHOS SDK, /data/service/hnp/bin/clang++)
- 状态: built（本地 conan create 全量验证 + test_package 冒烟通过；未上传制品仓）
- package_id: 4b4a1271519cde81c4c981693ed5d816d2d2d414

## 编译步骤

1. 依赖预检（W0/R35/R36）：`conan download -r=ohpcd --only-recipe` 逐一验证
   qtbase/6.11.1 + KF6 6.14.0 全闭包 13 框架 + ecm/6.26.0 均已发布（Qt6Concurrent、
   Qt6Test 确认存在于 qtbase 制品中；Qt6PrintSupport 确认不存在）。
2. 探索编译（模式 B，BUILD_TESTING=ON）：`conan install` 生成工具链后
   `cmake -DBUILD_TESTING=ON ...` + `make -j` —— 100% 编译通过（含 4 个 autotests
   测试与主程序 ksystemlog），ctest 4/4 通过。
3. W3 正式验证：`conan create archives/k/ksystemlog/26.04.0
   -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` —— 源码下载 → 打补丁 →
   构建 → 打包 → test_package 冒烟（--version / --help）全部通过。

## 上游测试三步法（R51）

- 清点：`grep -rn ecm_add_test autotests/CMakeLists.txt` → 4 个测试
  （logModeFactoryTest / systemAnalyzerTest / kernelAnalyzerTest / kioLogFileReaderTest，
  均链接内部静态库 testCore）。
- 运行：BUILD_TESTING=ON on-device 构建 + `ctest --output-on-failure`：

```
1/4 Test #1: ksystemlog-logModeFactoryTest .....   Passed    0.07 sec
2/4 Test #2: ksystemlog-systemAnalyzerTest .....   Passed    8.15 sec
3/4 Test #3: ksystemlog-kernelAnalyzerTest .....   Passed    0.10 sec
4/4 Test #4: ksystemlog-kioLogFileReaderTest ...   Passed    0.08 sec

100% tests passed, 0 tests failed out of 4
```

- 回填：结果写入本笔记、manifest.yaml、reports/test-report.md。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 失败：找不到 Qt6PrintSupport | 制品仓 qtbase/6.11.1 以 FEATURE_printsupport=OFF 构建，无 Qt6PrintSupport（algobox 1.1.1 / conducteo 5.0.2 先例） | 补丁 0001：从根 CMakeLists REQUIRED 组件与 ksystemlog_lib 链接中移除 |
| 2 | 打印功能不可用 | QPrinter/QPrintDialog/QPrintPreviewDialog 属 PrintSupport | 补丁 0002：printSelection() 改用 QPdfWriter（QtGui，与 QPrinter 共享 QPagedPaintDevice 基类）导出 PDF；printPreview() 同路由；菜单动作保留、功能以 PDF 形式可用 |
| 3 | 构建期 kconfig_compiler_kf6 报符号找不到 | 宿主工具为 OHOS 二进制，加载时缺 Qt/KF6 库路径 | 构建环境注入 LD_LIBRARY_PATH（/system/lib64 + 各依赖包 lib + llvm/lib） |
| 4 | 测试二进制加载失败（symbol not found） | 发布的 KF6 6.14.0 包 DT_NEEDED 带构建机绝对路径（$HOME/.cache/conan2/...），OHOS musl 加载器对路径型 NEEDED 无 LD_LIBRARY_PATH 兜底 | ELF DT_NEEDED 提取（用 SHT_DYNAMIC 的 sh_link 定位 .dynstr）→ 缺失绝对路径符号链接兜底；逻辑内嵌 test_package/conanfile.py `_fix_absolute_needed`（kfourinline 26.04.0 先例） |
| 5 | 绝对路径修复后仍失败（../../bin/libKF6*.so） | 发布包还有相对 cwd 解析的相对路径 NEEDED | <build>/bin 与 <build>/../../bin 符号链接农场（kfourinline / kgoldrunner 先例），收录全部 .so/.so.N 命名变体 |
| 6 | 农场建成后仍报 ZSTD_*: symbol not found | karchive 的 NEEDED 是 ../../bin/libzstd.so.1，首轮农场只收录实体文件漏掉符号链接变体 | 农场重建时 readlink -f 解引用，覆盖 .so 与 .so.N 全部别名 |

## 源码修改

- `patches/0001-ohos-cmake-drop-printsupport.patch`：
  - 根 `CMakeLists.txt`：find_package(Qt6) 移除 PrintSupport 组件（附 OHOS 说明注释）
  - `src/lib/CMakeLists.txt`：ksystemlog_lib 移除 Qt6::PrintSupport 链接
- `patches/0002-ohos-print-to-pdf-export.patch`：
  - `src/lib/logViewExport.h`：`class QPrinter;` → `class QPagedPaintDevice;`，print() 签名同步
  - `src/lib/logViewExport.cpp`：QPrintDialog/QPrinter/QPrintPreviewDialog include →
    QPdfWriter/QFileDialog；printSelection() 以 QFileDialog 选目标文件 + QPdfWriter(1200dpi)
    输出；printPreview() 路由至同一 PDF 导出；print() 体内 printer->newPage() → device->newPage()
- 无 `__OHOS__` 宏注入（PF5）；journald/audit/kdoctools 为上游可选依赖，OHOS 上自动跳过，未改动。

## 依赖版本

- qtbase/6.11.1（Qt6 Core/Concurrent/Gui/Widgets/Test；PrintSupport 缺失）
- KF6 6.14.0 全闭包：kconfig, kconfigwidgets, kcoreaddons, kcrash, ki18n, karchive,
  kitemviews, kwidgetsaddons, kcompletion, ktextwidgets, kio, kxmlgui
- tool_requires: ecm/6.26.0
- 间接：qtsvg/6.11.1（kiconthemes 传递）、zstd/1.5.7 等（conan 解析，共 29 包）

## 验证结果

### 对话 #1（2026-09-20）

- 用户：将 ksystemlog 26.04.0 适配鸿蒙 PC（aarch64-linux-ohos），按积分赛流程执行（W0 依赖预检 → W1 基线同步 → R47 语言预检 → 编译适配 → R51 上游测试三步法 → W3 conan create 全量验证 → finish → 推送分支 → PR 正文）。
- 助手：W0 确认 KF6 6.14.0 全闭包 + qtbase/6.11.1 + ecm/6.26.0 全部发布；R47 通过（cpp, cmake）；探索编译 BUILD_TESTING=ON 全量通过，ctest 4/4（100%）；W3 conan create + test_package 冒烟 2/2 通过；finish 全部门禁通过（G0–G4、W2、submit 就绪）。
- 结论：状态 built，package_id 4b4a1271519cde81c4c981693ed5d816d2d2d414。

```bash
# W3 正式验证
$ conan create archives/k/ksystemlog/26.04.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
...
[test] ksystemlog --version
ksystemlog 26.04.0
[test] ✅ --version reports 26.04.0
[test] ksystemlog --help
Usage: ... [options] URL
System Logs Viewer by KDE
[test] ✅ --help shows the ksystemlog usage banner
[test] ALL SMOKE ASSERTIONS PASSED
ksystemlog/26.04.0 (test package): ksystemlog runtime smoke passed

# 上游测试（探索构建，BUILD_TESTING=ON，on-device ctest）
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 4
```
---

**编译结束**: 2026-09-20 01:17
**最终状态**: built
