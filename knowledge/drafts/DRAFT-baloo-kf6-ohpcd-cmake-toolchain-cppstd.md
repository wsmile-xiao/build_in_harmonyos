# DRAFT-baloo-kf6-ohpcd-cmake-toolchain-cppstd：conan CMakeToolchain cppstd 时序坑

> Contributor: AtomCode/oh-executor | Status: Draft | Updated: 2026-09-06
> Source: baloo 26.04.3（upstream frameworks 6.25.0）HarmonyOS PC 适配，
> conanfile.py configure() 提升 host settings.compiler.cppstd 17→20
> 对应：knowledge/drafts/DRAFT-baloo-kf6-ohpcd-cmake-toolchain-cppstd.kv

## 现象

ohpcd 统一 profile（`ci/conan/profiles/ohos-aarch64`）固定 `compiler.cppstd=17`。
baloo 的 engine 源码需要真正 C++20（`std::ranges`、`std::erase_if`）。最初配方只在
`generate()` 里设：

```python
tc.variables["CMAKE_CXX_STANDARD"] = "20"
tc.variables["CMAKE_CXX_FLAGS"]     = "-std=c++20"
```

结果编译仍是 C++17，报错：

```text
no member named 'erase_if' in namespace 'std'      # orpostingiterator.cpp
no member named 'ranges' in namespace 'std'        # and/phrasepostingiterator.cpp
```

`no member named 'ranges'` 是 C++17 下根本不存在 `std::ranges` 命名空间的直接证据；
`std::erase_if` 同为 C++20 容器自由函数。两报错并存即"实际编译仍是 C++17"的指纹。

## 根因

conan 生成的 `conan_toolchain.cmake` 顶部 **"cppstd" block** 以 profile 的
`compiler.cppstd` 为唯一标准来源：

```cmake
message(STATUS "Conan toolchain: C++ Standard 17 with extensions OFF")
set(CMAKE_CXX_STANDARD 17)          # ← normal var，源 = profile compiler.cppstd
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
variable_watch(CMAKE_CXX_STANDARD conan_modify_std_watch)
```

CMake 的标准编译选项由该 normal var 决定，并在编译命令中**后置**于用户
`CMAKE_CXX_FLAGS` 与 CMakeToolchain.variables 段写入的 cache 变量。实测 build3 树
`balooaaf06454ecc73`：cppstd block L57=`set(CMAKE_CXX_STANDARD 17)`；其后的 variables
段（L206-208）虽把 `CMAKE_CXX_STANDARD "20"` 与 `CMAKE_CXX_FLAGS "-std=c++20"` 写进
cache，但同作用域已有 normal var=17，cache 值不改变 normal var 的读取结果 → 最终
`-std=c++17` 后置生效。这就是"看似已设 -std=c++20、实际编译 C++17"的 toolchain 时序坑。

## 方案

在 `configure()` 提升 **host** 节点的 setting，使 cppstd block 直接以 20 为源：

```python
def configure(self):
    if self.settings.os == "OHOS" and str(self.settings.compiler.cppstd) == "17":
        self.settings.compiler.cppstd = "20"
```

- 仅 `settings.os=="OHOS"` 分支执行，非 OHOS 行为不变（patch 不扩散）。
- 依赖节点保持各自 cppstd=17，不动依赖图。
- `generate()` 里保留原 `CMAKE_CXX_STANDARD`/`CMAKE_CXX_FLAGS` 变量作为冗余。
- 与 `kfilemetadata` 配方笔记的交叉说明：kfilemetadata 记录过
  `CMAKE_CXX_FLAGS=-std=c++20`"强制"写法；baloo 证明在 ohpcd cppstd=17 profile 下
  该写法不生效，可靠手段是 configure() 提升 setting。后续 KF6/C++20 配方应以本条为准，
  避免误抄"只加 CXX_FLAGS"。

## 验证

- toolchain 对照（同一配方、同一 profile，唯一差异 = 是否执行 configure() 提升）：
  - build3 树 `balooaaf06454ecc73`：cppstd block `set(CMAKE_CXX_STANDARD 17)` → 报
    `no member named 'ranges' in namespace 'std'`、`erase_if` 缺失。
  - build4 树 `baloo0038ce75353b5`：cppstd block `set(CMAKE_CXX_STANDARD 20)` → 报错
    前移至 `no member named 'any_of' in namespace 'std::ranges'`（真到 C++20，进入
    libc++15 缺 ranges 算法一环，见 ranges DRAFT）。
  - build9 CI 树 `baloo20010c827875d`：cppstd block=20；日志 L145
    `-- Conan toolchain: C++ Standard 20 with extensions OFF`；`ctest` 21/21 PASS。
- 命令：`grep -n "Conan toolchain: C++ Standard" build9-aci-round1.log`；test_package
  消费者 L1055 仍为 17（消费者未提升，符合预期，不影响包标准）。
- 结果：conan create RC=0、21/21、test_package 1/1（round-1 authoritative CI）。

## 与现有知识的关系（查重证据）

- **DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms**：同一适配链的下一环
  （真 C++20 后 libc++15 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 使 std::ranges 算法仍
  缺失，baloo 以 C++11 `std::any_of` 调用点改写解决）。本条目覆盖"假 C++20（实
  C++17）"的时序坑，两者互补不重复。
- **E538**：同为 ohpcd cppstd=17 profile 语境，主题是发布图 options/package-id 一致性，
  不含 toolchain cppstd block 写入时序。
- **E096 / E130 / E293**：CMake 编译器特性自动检测失败 / libc++ 最低标准 ≥17 /
  旧 C++2003 语法——机制均不同。
- 检索证据：curation-report §5 检索词 C) cppstd|CXX_STANDARD|CMakeToolchain 与
  Auditor §6 独立检索 CMAKE_CXX_STANDARD/CMAKE_CXX_FLAGS/-std=c++20 均无等价条目
  → gap 成立。

## 适用边界

- ohpcd `compiler.cppstd=17` profile 下任何需要 C++20 语义的 CMake/conan 库。
- 诊断指纹：toolchain 打印 "C++ Standard 17" 但配方设了 `-std=c++20`；或编译错误里
  `ranges` 与 `erase_if` 缺失并存。
- 不适用：已经用 C++17 profile + C++17 源码的库（无提升必要）；非 conan
  CMakeToolchain 的构建（autotools/meson 无此 block 机制，见 E538 的 meson 场景）。

## 恢复条件

在 recipe 的 `configure()` 提升 host `settings.compiler.cppstd` 后重跑
`conan create`；确认 toolchain 打印 "C++ Standard 20"、编译命令行末尾为 `-std=c++20`、
且依赖 C++20 能力的报错（ranges/erase_if）消失（若进入 ranges 算法缺失，转 ranges DRAFT）。

---
*created: 2026-09-06 · builder/path-update baloo-26.04.3 · evidence round-1 CI + curation/audit*
