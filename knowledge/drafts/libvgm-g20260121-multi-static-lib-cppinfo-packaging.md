# libvgm g20260121 — 单配方多静态库的 cpp_info 四件套（链接序/探测宏/头前缀/依赖传递）（draft）

**Category**: packaging | build-system | conan · **Severity**: 2 · **Tool**: conan/cmake

## 症状

上游一个 CMake 工程构建**多个兄弟静态库**（libvgm：vgm-utils / vgm-audio /
vgm-emu / vgm-player）时，配方若只写 `cpp_info.libs = ["vgm-utils", ...]`
照抄 CMake `add_subdirectory` 顺序，下游静态链接会报**未定义符号**
（vgm-player 引用 vgm-emu/vgm-utils，但传统链接器从左到右解析，被依赖库
排在了前面）；或下游 `#include "stdtype.h"` 编不出与库一致的结构体布局。

## 根因

单 Conan 包聚合一组兄弟静态库时，`cpp_info` 承担了上游 CMake target 间
依赖的全部表达，四个易错点：

1. **libs 顺序 = 静态链接顺序**：必须依赖者在前（vgm-player → vgm-audio →
   vgm-emu → vgm-utils），与 `target_link_libraries` 的图序一致。
2. **configure 期探测宏要传播**：上游在 configure 时
   `check_include_file("stdint.h")` → `-D HAVE_STDINT_H`，公共头
   `stdtype.h` 按该宏切换 typedef 路径——库内目标经
   `target_compile_definitions` 拿到，**下游没有**，须
   `cpp_info.defines = ["HAVE_STDINT_H"]`。凡公共头里 `#ifdef HAVE_*`
   的都属此类（VGM_LITTLE_ENDIAN 这类仅 .c 私有使用的则不必）。
3. **头文件带前缀安装时 includedirs 双拼写**：上游安装到
   `include/vgm/{utils,audio,emu,player}`，设
   `includedirs = ["include/vgm", "include"]` 让
   `#include "player/playera.hpp"`（上游示例风格）与
   `#include "vgm/player/playera.hpp"` 都可用。
4. **间接依赖要显式传递**：vgm-utils 静态链里嵌 zlib 符号，
   `cpp_info.requires = ["zlib::zlib"]`，否则消费者链接缺 `-lz`。

## 对策

```python
def package_info(self):
    # 依赖者在前，满足传统链接器从左到右解析
    self.cpp_info.libs = ["vgm-player", "vgm-audio", "vgm-emu", "vgm-utils"]
    self.cpp_info.includedirs = ["include/vgm", "include"]   # 双拼写
    self.cpp_info.defines = ["HAVE_STDINT_H"]                # 公共头探测宏
    self.cpp_info.requires = ["zlib::zlib"]                  # 静态嵌入的间接依赖
    if self.settings.os in ("Linux", "OHOS"):
        self.cpp_info.system_libs = ["pthread", "m"]         # 上游 find_package(Threads)/m
```

自检法：拿 test_package 分别以"最依赖的库优先"清单链接一遍——能过即序对。

## 验证

libvgm g20260121 真机（ohos-aarch64，clang 15.0.4）`conan create` +
test_package 36/36：test_libvgm 与 consumer_vgm_to_wav 两个消费者目标均以
单 target `libvgm::libvgm` 链接四个静态库 + zlib + pthread/m，编译运行全绿
（消费者用例含 gzip 输入路径，对 zlib 做了运行时消费验证）。
