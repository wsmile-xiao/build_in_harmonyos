# LCMAPS 插件的 test_package 必须静态链接引擎库模拟引擎进程映像

> Draft: `DRAFT-LCMAPS-PLUGIN-TEST-NEEDS-STATIC-ENGINE-WHOLE-ARCHIVE`
> Stem: `lcmaps-plugin-test-needs-static-engine-whole-archive` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-LCMAPS-PLUGIN-TEST-NEEDS-STATIC-ENGINE-WHOLE-ARCHIVE
- **严重度**: 2
- **类别**: testing|packaging|upstream-semantics
- **触发工具**: conan|cmake
- **阶段**: testing

## 错误特征

lcmaps 插件包（lcmaps-plugins-voms 等）的 test_package 若只
`dlopen("liblcmaps_voms.so", RTLD_NOW)`，musl 报：

```
FAIL: dlopen(.../liblcmaps_voms.so): Error relocating ...:
      lcmaps_log: symbol not found
```

即使测试程序已经 NEEDED 了 `liblcmaps_without_gsi.so.0`（框架已加载）也照样失败。

## 根因

1. 插件引用 `lcmaps_log` 等**框架内部符号**：`llvm-nm -D liblcmaps_without_gsi.so`
   显示这些符号**不在 .so 的 dynsym**（不导出）——它们只在
   `liblcmaps_without_gsi.a` 里（T 定义在）。
2. LCMAPS 的生产形态：评估引擎**静态嵌入**消费程序（链接 .a），主程序经
   `-rdynamic` 把符号放入 dynsym，dlopen 插件时从主程序全局命名空间解析。
3. 因此"链接 .so 版框架"的测试形态永远无法解析 lcmaps_log；且 .a 是静态库
   **按需拉取**——测试程序不引用 lcmaps_log 时，定义它的 TU 根本不会进主程序，
   `-rdynamic` 无从导出——必须 `--whole-archive`。

## 影响范围

- lcmaps-plugins-* 全系列插件包的 test_package/CI 冒烟。
- 其他"插件引用宿主内部符号、宿主静态嵌入"型上游（同类架构可复用判断方法：
  先 `nm -D <宿主>.so | grep <符号>` 判导出性，再 `nm <宿主>.a | grep` 判归属）。

## 推荐方案

**方法**: `static-engine-whole-archive-rdynamic`

CMakeLists.txt（test_package）：

```cmake
find_package(lcmaps REQUIRED CONFIG)
add_executable(test_lcmaps_plugins_voms test.c)
target_link_libraries(test_lcmaps_plugins_voms PRIVATE
    -Wl,--whole-archive
    ${lcmaps_PACKAGE_FOLDER_RELEASE}/lib/liblcmaps_without_gsi.a
    -Wl,--no-whole-archive)
target_link_options(test_lcmaps_plugins_voms PRIVATE -rdynamic)
```

要点：
1. `--whole-archive` 全量拉入引擎 .a（未引用符号也要进主程序）。
2. `-rdynamic` 把引擎符号导出到主程序 dynsym（musl dlopen 解析范围）。
3. `${lcmaps_PACKAGE_FOLDER_RELEASE}` 是 CMakeDeps 注入的包根变量，
   避免硬编码路径。
4. test_package/conanfile.py 需显式 `self.requires("lcmaps/1.6.7")`
   （CMakeDeps 只为直接 requires 生成 config，见同族知识
   DRAFT-CONAN-TOOLCHAIN-GENERATE-ENV-DROPPED-PKG-CONFIG-PATH）。
5. test() 运行时 `LD_LIBRARY_PATH` 只需插件目录
   `<tested_pkg>/lib/lcmaps`（引擎已静态进程序）。

## 验证命令

```bash
llvm-nm -D $LCPKG/lib/liblcmaps_without_gsi.so | grep -c "lcmaps_log"   # 0（不导出）
llvm-nm $LCPKG/lib/liblcmaps_without_gsi.a | grep -w "T lcmaps_log"     # 有定义
# 修复后 test_package: RESULT: PASS (0 skip(s) allowed)
```

## 取证记录

- 包: lcmaps-plugins-voms 1.7.1（`archives/l/lcmaps-plugins-voms/1.7.1`）
- 逐字证据: `reports/conan-create.log`（修复前 6×reloc FAIL、修复后
  6 插件 dlopen+dlsym 全 PASS）、`test_package/CMakeLists.txt`
