# DRAFT-hashmap-0.8.1-no-build-system-single-tu-lib — 无构建系统单 TU C 源库（.c+.h）custom 配方直接编译为静态库

- 触发事件：hashmap 0.8.1（tidwall/hashmap.c）首轮适配。上游仅 hashmap.c
  （1154 行）+ hashmap.h（62 行），无 configure/make/CMake/meson；conan-init
  误判为 autotools 生成的配方在 build() 必然失败。
- 路径：Path B（知识库扩展）
- 编号：DRAFT-hashmap-0.8.1-no-build-system-single-tu-lib

## 现象

conan-init 生成 Autotools 模板配方（configure + make），但上游没有 configure
脚本和 Makefile；且该库不是 header-only（实现体在 .c），不是 stb 单头实现库
（实现体不在头文件）。需要用 custom 配方直接编译单 TU。

## 根因

纯 .c+.h 且无任何构建系统的上游，conan-init 的构建系统推断可能落到
autotools/makefile 模板；header-only 形态（E257）与 stb 单头实现库形态
（DRAFT-enet）都无法覆盖"实现体在 .c、无构建系统"的库。正确形态是
custom 配方：build() 用 Conan conf 提供的编译器把上游 .c 编译成静态库。

## 修复（已在本轮验证）

conanfile.py 三要素：

```python
package_type = "library"
settings = "os", "compiler", "build_type", "arch"
options = {"shared": [True, False]}
default_options = {"shared": False}

def build(self):
    execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = execs.get("c", "clang")
    ar = execs.get("ar", "llvm-ar")
    ranlib = execs.get("ranlib", "llvm-ranlib")
    # 静态：clang -c hashmap.c → ar rcs libhashmap.a → ranlib
    # shared：clang -fPIC -shared -o libhashmap.so hashmap.c

def package(self):
    copy(self, "hashmap.h", src=..., dst=include)
    copy(self, "libhashmap.a", src=..., dst=lib)
    copy(self, "LICENSE*", src=..., dst=licenses, keep_path=False)

def package_info(self):
    self.cpp_info.libs = ["hashmap"]
```

## 验证

- conan-verify：G0-G4 + L2/L4/L5 全部 PASS
- W3 本地 CI：L0/L1/L4/L5 全过，Pass rate 100%（1/1）
- 消费者 test_package：`1/1 Test #1: test_hashmap Passed`（exit 0）
- 鸿蒙专项测试：tests-ohos/ohos_test.c PASSED（exit 0）
- 上游测试：HASHMAP_TEST 内置自检 1/1 PASSED（默认 + SEED/N 变体），
  基准模式 BENCH=1 6 组正常执行——独立运行并记双口径台账，不并入配方 build()

## 适用边界 / 反例

- 适用：实现体在 .c、无任何构建系统的单 TU C 源库（.c+.h），如 hashmap.c。
- 反例/边界：有 Makefile 的走 E392（raw makefile 配方）；实现体在头文件宏
  实例化的 stb 风格走 DRAFT-enet；纯 header-only 走 E257/E321/E322。

## 关系

- similar_to: [E257, E392, DRAFT-enet-2.7.0-single-header-impl-lib]
- caused_by: [E392（compiler_executables 字典获取为同一配方内根因）]
- prerequisite_of: [] / conflicts_with: []
