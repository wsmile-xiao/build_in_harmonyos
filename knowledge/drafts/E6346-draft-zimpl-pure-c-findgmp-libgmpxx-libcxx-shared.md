# E6346-draft-zimpl-pure-c-findgmp-libgmpxx-libcxx-shared：纯 C 项目 FindGMP 误链 libgmpxx（zimpl 3.7.1）

## 错误特征

```
Error loading shared library libc++_shared.so: (needed by <pkg>/lib/libgmpxx.so.4)
Error relocating <pkg>/lib/libgmpxx.so.4: _ZNSt4__n113basic_istream...: symbol not found
ERROR: zimpl/3.7.1@ohpcd/stable (test package): Error in test() method
```

test_package 执行包内 bin/zimpl 时：`libgmpxx.so.4`（GMP 的 C++ 封装库）被
加载，但其依赖的 `libc++_shared.so` 不在默认搜索路径，且 `_ZNSt4__n1*`（libc++
命名空间）符号在纯 C 可执行文件内无定义 → relocation symbol not found。

## 触发条件

- 项目使用自带 `cmake/Modules/FindGMP.cmake`（其 `GMP_LIBRARIES` = libgmp + libgmpxx）
- 项目是 **纯 C**（只 `#include <gmp.h>` 用 C API，从不调用 gmpxx 的 C++ 类）
- OHOS 平台：libc++_shared.so 在 `/system/lib64`，默认 loader 搜索路径不含它

## 根因

FindGMP.cmake 无条件把 `libgmp` 与 `libgmpxx` 都加入 `GMP_LIBRARIES`：
```cmake
find_library(GMP_LIBRARY  NAMES gmp  HINTS ${GMP_DIR} PATH_SUFFIXES lib)
find_library(GMPXX_LIBRARY NAMES gmpxx HINTS ${GMP_DIR} PATH_SUFFIXES lib)
SET(GMP_LIBRARIES ${GMP_LIBRARY} ${GMPXX_LIBRARY})
```
纯 C 项目（zimpl 的 gmpmisc.c/numbgmp.c 只用 gmp.h）本不需要 gmpxx，但 CMake
仍把 `libgmpxx.so` 链进 bin，造成对 `libc++_shared.so` 的运行时依赖链，而
OHOS 上默认路径不含 `/system/lib64`，且 libgmpxx 的 C++ 符号（`_ZNSt4__n1*`）
无定义 → 启动即失败。

## 解决方案

在 conanfile generate() 中预设 `GMPXX_LIBRARY=""`（空串缓存值会阻止
find_library 再次搜索 gmpxx），使 `GMP_LIBRARIES` 只剩 libgmp：

```python
def generate(self):
    tc = CMakeToolchain(self)
    gmp = self.dependencies["gmp"]
    tc.cache_variables["GMP_DIR"] = gmp.package_folder
    tc.cache_variables["GMPXX_LIBRARY"] = ""   # 纯 C 项目无需 C++ 接口库
    ...

```

修复后 `readelf -d bin/zimpl | grep NEEDED` 只含 `libgmp.so.10` 与 `libc.so`，
不再出现 libgmpxx/libc++_shared，运行时无外部符号解析问题。

## 验证证据

- 修复前：NEEDED 含 `libgmpxx.so.4`；test_package 报 libc++_shared not found + _ZNSt4__n1* symbol not found
- 修复后：NEEDED 仅 `libgmp.so.10`/`libc.so`；conan-verify G2-G5 全绿；check.sh 195/198 通过

## 适用与不适用边界

**适用**：纯 C 项目 + 自带 FindGMP.cmake + OHOS；任何"Find 模块默认链接 C++
封装库导致纯 C 二进制引入 libstdc++/libc++ 运行时依赖"的同类场景（如
FindGSL/FindBoost 的 C++ 头文件库对纯 C 项目同理）。

**不适用**：C++ 项目（确实使用 gmpxx 的 C++ 类和 std 类型）；GMP 提供
静态 libgmpxx.a 且全静态链接的场景；项目明确需要 GMP 的 C++ 接口时不应
置空。

## 与既有条目关系

- **相似 E019**（set-ld-library-path）：E019 症状是 ld.so 找不到 .so 的通用
  情况（方案注入 LD_LIBRARY_PATH）。本条目症状同为"库加载/符号解析失败"，
  但**根因不同**：不是缺少搜索路径，而是纯 C 项目**误链了不需要的 C++
  封装库**；正确修法是**不链入**（GMPXX_LIBRARY 置空）而非加路径，否则
  libgmpxx 的 C++ 符号在纯 C 进程内仍无法解析（注入路径也启动失败）。
- **相似 E004**（modify-ldshared）：E004 是 dlopen Python 扩展缺符号，本条目
  是 exec 二进制 relocation 缺 C++ 符号；同属"运行时符号解析失败"族，诊断
  与修法不同。
- **相似 E520**（qsb 宿主工具需 LD_LIBRARY_PATH）：E520 是 Qt Shader Baker
  构建期运行加载 libQt6 依赖库缺搜索路径（方案 cmake -E env 注入
  LD_LIBRARY_PATH）；本条目是**最终产物 bin 启动时** relocation 缺 C++
  符号，根因是 FindGMP 误链 C++ 封装库（方案不链入），两者错误场景
  （构建期工具 vs 运行期产物）、注入方式（构建期 env vs 链接期裁剪）不同。

## 新增价值

既有知识库（E019/E004）未覆盖"Find 模块默认链 C++ 封装库 → 纯 C 项目运行时
引入 libc/libc++ 依赖"这一根因与修法组合；本条目补充 OHOS 上纯 C + GMP 家族
项目的可复用处理范式（GMPXX_LIBRARY 置空消除误链），并给出 NEEDED 级证据。