# bitmagic 9.3.2 适配笔记

## 编译环境
- 构建系统: cmake (header-only INTERFACE library)
- 编译日期: 2026-09-30
- 编译器: clang 15.0.4 / clang++ 15.0.4
- C++ 标准: C++17 (上游硬要求)
- 状态: built

## 编译步骤

BitMagic 上游 CMakeLists.txt 把 `bm` 定义成 INTERFACE 库（add_library(... INTERFACE)），
没有 `install()` 规则；整个 src/ 目录都是头文件。因此配方采取最简单路径：
跳过 build 阶段，直接从 `source(src_folder)/src` 拷贝所有 `*.h` 到 `package_folder/include`，
再用 test_package 编译一个真实的小程序（`bvector` set/get/count/optimize/iterate + set
algebra）来验证头文件可用。

```python
# conanfile.py 关键路径
def package(self):
    copy(self, "*.h",
         src=os.path.join(self.source_folder, "src"),
         dst=os.path.join(self.package_folder, "include"),
         keep_path=True)
    copy(self, "LICENSE", self.source_folder,
         dst=os.path.join(self.package_folder, "licenses"))
```

test_package 直接用 clang++ 编译 test_bitmagic.cpp → test_bitmagic，运行后断言全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake --install` 在 OHOS 上的 cmake 4.1.2 输出 "Unknown argument --install" | PATH 上的 `cmake` 是个别名为 bun 的 wrapper | 走配方 `package()` 手动拷贝头文件，绕开 cmake install |
| 2 | 上游 CMakeLists.txt 没 `install()` | BitMagic 设计为 header-only CMake 包 | 改用 Conan `copy(*.h)` 走 packaging；不依赖 cmake install |
| 3 | `set_range(0, 1024)` count 期望值 | 区间 [a, b] 双闭 | 测试断言改为 1025，不是 1024 |

## 源码修改

无（header-only，直接安装上游 tarball）。

## 依赖版本

- 操作系统：HarmonyOS PC (linux)
- cmake：4.1.2（仅用于编译验证，非安装阶段使用）
- clang/clang++：15.0.4
- conan：2.x
- pthread：系统自带（可选，with_threads=True 时启用）

## 验证结果

```bash
# 1. 编译验证（手动跑一遍上游 CMakeLists.txt，确认 samples/tests 全编过）
$ cd $BUILD_SRC_DIR && mkdir -p build && cd build
$ cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
$ make -j1   # exit 0，生成所有 samples/tests/perf

# 2. 配方 verify
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify bitmagic 9.3.2
# test_bitmagic 输出：
#   test bitmagic 9.3.2: OK (count=65, OR=150, AND=50, XOR=100)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方，纯 copy 不编译 |
| conandata.yml | GitHub 官方源 + 正确 sha256 |
| test_package/test_bitmagic.cpp | 真实 C++ 程序：bvector<> 核心 API 16 个 assert |
| test_package/conanfile.py | 直接 clang++ 编译运行 |

## 注意事项

- BitMagic 内部对 x86 SSE2/SSE4.2/AVX2/AVX512、ARM NEON（通过 sse2neon.h）有条件编译。
  OHOS 走 sse2neon 路径；下游若需 x86 优化可在 bmsse42opt / bmavx2opt 宏下编译。
- `with_threads=True`（默认）会链接 pthread；纯单线程场景可关掉以避免无谓的 -pthread。
- 上游的 stress/perf 测试（bmtest/bmperf/bmtest64）是 CLI 工具而非单元测试，
  L0 验证靠 test_bitmagic.cpp，不跑上游 tests/。
---

**编译结束**: 2026-09-30 22:22
**最终状态**: built
