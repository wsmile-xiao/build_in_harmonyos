# pixman 0.46.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（真机 conan create -pr ohos-native 通过）

## 编译步骤

meson setup(禁 tests/demos/gtk/libpng/openmp) → ninja。核心库仅依赖 libm+pthread 系统库。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 报 Unknown linker: llvm-ar/ar not found | conan MesonToolchain 不把 compiler_executables 的 ar 写进 native file，meson 按 PATH 探归档器失败 | generate() 里 tc.generate() 后手工把 ar/ranlib 注入 conan_meson_native.ini 的 [binaries] |
| 2 | test_package 编译报 pixman-version.h not found | 头装在 include/pixman-1/，pixman.h 内部 #include <pixman-version.h> | cpp_info.includedirs=["include/pixman-1","include"] |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- 无 conan 依赖（仅系统库）

## 验证结果

- 真机 conan create + dlopen libpixman-1.so 通过

## PR 审查修复记录

- 2026-08-26: 修正 test_package/MANIFEST.yml 的上游测试声明。官方 pixman-0.46.4 tarball
  sha256=d09c44ebc3bd5bee7021c79f922fe8fb2fb57f7320f55e97ff9914d2346a591c，
  test/ 目录递归统计为 48 个文件，其中 42 个 .c 源文件；本轮最小化 OHOS 构建仍关闭
  meson tests，但不再将上游测试数声明为 0。
- 2026-08-26: 增强 test_package/test.c，从单一 dlopen smoke 扩展为 3 类消费者断言：
  公开头 <pixman.h> 编译、pixman_version_string 可解析且非空、pixman_region32_contains_point
  区域命中/未命中行为正确。test_package/conanfile.py 同步优先使用
  tools.build:compiler_executables 中的 c 编译器，并移除固定 bash 路径依赖。
- 2026-08-26: 针对复查规则 4，将 test_package/test.c 明确标注并扩展为上游
  test/region-contains-test.c 的可移植确定性子集：运行期解析
  pixman_region32_contains_point 与 pixman_region32_contains_rectangle，覆盖点 inside/outside/边界
  以及矩形 IN/OUT/PART 三类结果。该子集在 CI #31652 之后的下一轮 CI 中作为
  ./test_probe 执行，MANIFEST assertion_count 同步提升至 7。
- 2026-08-28: 再次适配 test_package 测试用例，将 region-contains 子集拆成
  3 组确定性场景（单矩形、双矩形、空区域），更贴近上游 region-contains-test.c 的
  contains_point / contains_rectangle 语义，同时补充 pixman_version_string、
  pixman_region32_init / init_rect / union_rect / fini 的运行时符号验证，
  并将 MANIFEST assertion_count 更新为 25。
