# LASi 1.1.3 HarmonyOS PC 适配说明

## 上游与构建

- 官方源码来自 SourceForge 的 `libLASi-1.1.3.tar.gz`，SHA256 为
  `5e5d2306f7d5a275949fb8f15e6d79087371e2a1caa0d8f00585029d1b47ba3b`。
- 上游使用 CMake，生成 `libLASi.a`；公共头为 `LASi.h`。
- 直接构建依赖由上游 `pkg_check_pkgconfig("pangoft2;pango;freetype2")`
  确定。配方使用赛事仓已经发布并实测可解析的
  `pango/1.50.14.1.1`，同时显式声明公共头闭包所需的 GLib、FreeType
  与 HarfBuzz，使 `lasi::lasi` 对消费者传播完整编译信息。

## 平台适配

1. `util.h` 使用了 C++17 已禁止的动态异常说明，补丁仅删除该说明，
   保留原来的 `std::runtime_error` 行为。
2. 上游旧版 pkg-config CMake 宏要求每个 `-l` 参数都能由
   `find_library()` 找到实体文件。HarmonyOS 将 `m`、`pthread`、`dl`
   等系统能力合并提供，补丁在找不到独立文件时保留原始链接参数，
   由 OHOS 链接器按系统规则处理。
3. CMake 4.1.2 没有 `Platform/HarmonyOS.cmake`，配方只把 CMake 平台
   规则别名设为 Linux；实际编译器、架构、ABI 和 Conan 设置仍为
   OHOS/aarch64/clang 15/libc++。
4. fontconfig 的通用 Unix 默认目录不包含 HarmonyOS 字体位置，配方
   为构建测试和包运行环境提供包含 `/system/fonts`、`/data/fonts`
   的 `fonts.conf`，避免 Unicode 排版退化为空输出。

## 测试清点与结果

上游 `examples/CMakeLists.txt` 共有且仅有 3 个 `add_test()`：

1. `MissingGlyphExample`
2. `SimpleLASiExample`
3. `ComplexTextLayoutExample`

真机通过 `ctest --test-dir <build> --output-on-failure` 全部执行，结果
为 3/3。消费者测试另有 2 项：`test_lasi` 验证真实文本度量和 EPS
生成 API；`test_lasi_ohos` 验证 HarmonyOS 内核、系统字体、Unicode
复杂文本排版与可写 TMPDIR，结果 2/2。合计 5/5，不少于上游 3 项。

## 结束标记

编译结束。最终状态：HarmonyOS PC 真机 `conan create`、上游 CTest
3/3、消费者测试 2/2 及仓库 12 组规范测试全部通过；未执行 commit、
push 或 PR 操作。
