# 上游零测试的库，编译期缺陷只在下游消费者实例化公开头模板时才暴露

**条目 ID**：`DRAFT-ifcplusplus-0-git20190402-consumer-only-header-defects`
**软件**：ifcplusplus `0-git20190402.13744d5`（git 快照 `13744d58f9b99ce3b4d49567b7085917cd7a6a3c`，2019-04-02）
**平台**：OpenHarmony PC aarch64 / clang 15 / libc++ / `compiler.cppstd=17`
**来源 PR**：（PR 建后回填）

---

## 1. 问题

IFC++ 是一个读写 IFC（Industry Foundation Classes）STEP 文件的 C++ 库。该快照的适配过程中，出现了两类
**"上游自己编译得好好的、一到下游就编译不过"** 的缺陷：

| # | 缺陷 | 表现 |
|---|------|------|
| ① | 公开头 `BuildingGuid.h` 中函数模板体内的 lambda 返回类型推导冲突 | 消费者一旦调用 `decodeBase64Uuid<T>()` 即编译失败 |
| ② | 内置几何内核 Carve 使用 C++17 已移除的 `std::auto_ptr` / `std::bind1st` / `std::bind2nd` | 库自身编译失败（libc++ 按标准删除这些设施） |

关键上下文：**上游该快照没有任何测试用例**——没有 `add_test()`、没有 `enable_testing()`、没有 gtest/catch2/doctest，
也没有 CI 配置，仓库里唯一的可执行目标是依赖 Qt 的 `examples/SimpleViewerExampleQt`。

```
$ grep -rn "add_test\|enable_testing" . --include=CMakeLists.txt
（无输出）
$ grep -rniE "gtest|catch2|doctest|boost/test" . --include=CMakeLists.txt
（无输出）
$ find . -iname '*test*'
（无输出；只有 IfcPlateStandardCase.* 这类名字里含 "te" 的实体类）
```

正因为零测试，①②在上游都不可能被发现；而**只构建库本身**的验证同样发现不了 ①。

---

## 2. 根因

### ① 模板/内联体延迟实例化掩盖缺陷

`IfcPlusPlus/src/ifcpp/model/BuildingGuid.h` 中：

```cpp
template<typename T>
inline boost::uuids::uuid decodeBase64Uuid(std::basic_string<T> const& input)
{
    ...
    auto index_of = [](T const in){
        for (uint8_t i = 0; i < base64Chars.size(); i++)
            if(in == base64Chars[i]) return i;      // 返回 uint8_t
        return 0;                                   // 返回 int —— 类型不一致
    };
```

lambda 没有尾置返回类型，其返回类型由体内 `return` 推导；clang 要求所有 `return` 类型一致，于是报：

```
error: return type 'int' must match previous return type 'uint8_t'
       (aka 'unsigned char') when lambda expression has unspecified explicit return type
```

这只是**语言规则**，与平台、架构、字节序都无关。它之所以长期存活，是因为 `decodeBase64Uuid()` 是函数模板，
上游代码库中**没有任何调用点**——模板从不被实例化，函数体从不被完整语义检查。

用一段不依赖本库的最小复现即可确认这是纯语言规则：

```cpp
#include <cstdint>
template<typename T> int f(T const in) {
    static constexpr T a[4] = {'0','1','2','3'};
    auto idx = [](T const in){
        for (uint8_t i = 0; i < 4; i++) if (in == a[i]) return i;
        return 0;
    };
    return idx(in);
}
int main(){ return f<char>('1'); }
```

```
$ clang++ -std=c++17 -c probe.cpp
error: return type 'int' must match previous return type 'uint8_t' ...
```

**判据**：仅"库能编译通过"对这类库不构成任何可移植性证据。必须有一个真正**实例化**公开 API 的消费者用例。

### ② C++17 已移除设施 + libc++ 严格执行

内置第三方源码 `external/Carve` 使用：

| 设施 | 数量 | 位置 |
|------|------|------|
| `std::auto_ptr` | 8 | `src/lib/intersect.cpp` |
| `std::bind2nd` | 2 | `src/lib/mesh.cpp` |
| `std::bind1st` | 1 | `src/include/carve/spacetree.hpp` |

这些在 C++17 中**已从标准移除**。profile 固定 `compiler.cppstd=17`，libc++ 按标准把它们整个删掉
（不像 libstdc++ 在某些模式下仍保留向后兼容），因此错误是硬失败而非弃用警告：

```
error: no member named 'auto_ptr' in namespace 'std'
error: no member named 'bind2nd' in namespace 'std'
error: no member named 'bind1st' in namespace 'std'
```

注意这里还有一个容易被忽略的连带点：`intersect.cpp` 原来是通过间接包含拿到 `auto_ptr` 的，
把类型换成 `unique_ptr` 后必须**显式补 `#include <memory>`**。

---

## 3. 处置

### 步骤 1：先定性（决定验证策略）

```bash
grep -rn "add_test\|enable_testing" . --include=CMakeLists.txt   # 空 → 无 CTest 注册
ls -d test tests unittest 2>/dev/null                            # 无测试目录
grep -rniE "gtest|catch2|doctest|boost/test" . --include=CMakeLists.txt
```

结论为"零上游用例"时，把"存在真实实例化公开 API 的消费者用例"当成适配完成的**先决条件**，而不是可选项。

### 步骤 2：修 ①——补显式 lambda 返回类型

最贴近原意的修复就是补上显式返回类型（原意就是"base64 字符下标"）：

```cpp
auto index_of = [](T const in) -> uint8_t {
    for (uint8_t i = 0; i < base64Chars.size(); i++)
        if(in == base64Chars[i]) return i;
    return 0;
};
```

不要改调用方，也不要把 lambda 整个重写成别的结构。

### 步骤 3：修 ②——按语义一对一替换

```cpp
// auto_ptr → unique_ptr（仅当原用途是作用域内 RAII、只以 .get() 交出裸指针）
std::auto_ptr<face_rtree_t> a_rtree(...)   →   std::unique_ptr<face_rtree_t> a_rtree(...)

// bind2nd(f, x) → lambda
std::bind2nd(std::not_equal_to<const vertex_t*>(), next)
  →  [next](const vertex_t* v) { return v != next; }

// bind1st(f, x) → lambda
std::bind1st(intersection_test, children[i].aabb)
  →  [&](const typename child_t::aabb_t& a) { return intersection_test(children[i].aabb, a); }
```

并补齐 `<memory>` 等直接依赖的头。

> **不要用无校验的批量文本替换**（`sed -i 's/auto_ptr/unique_ptr/g'`）。`auto_ptr` → `unique_ptr` 只有在
> "作用域内 RAII、无拷贝转移"时才语义等价；盲替换会引入编译错误或微妙的生命周期改变。必须逐处确认，
> 并把补丁纳入版本管理的 `patches/` 以便按文件粒度复核。

### 步骤 4：把消费者用例当回归门

在 `test_package` 里**真实调用**公开头模板，让"模板被实例化"这件事每次 `conan create` 都被强制执行：

```cpp
boost::uuids::uuid u = decodeBase64Uuid<char>(createBase64Uuid<char>());
if (u.is_nil()) return 1;      // 走到实例化，才会触发编译期缺陷
```

---

## 4. 验证证据（本地实测）

配方 `archives/i/ifcplusplus/0-git20190402.13744d5/`，profile `ohos-aarch64-run`
（`CMAKE_CROSSCOMPILING_EMULATOR = /root/ohpc/bin/ohos-qemu-aarch64`，经 qemu 真实执行）：

```
$ bash outputs/local-validate-recipe.sh .../archives/i/ifcplusplus/0-git20190402.13744d5
==> conan exit=0

1/2 Test #1: test_ifcplusplus .................   Passed    0.36 sec
2/2 Test #2: test_ifcplusplus_ohos ............   Passed    0.42 sec
100% tests passed, 0 tests failed out of 2
```

两个用例各自的检查项（全部真实执行，非纯断言）：

- `test_ifcplusplus`（消费者端到端，16 项）：解析 64 个实体的 IFC4 模型 → 类型化取出 IfcProject /
  IfcBuildingStorey / IfcWall → 遍历墙的 BRep（6 面 / 24 顶点）→ `WriterSTEP` 回写 3770 字节 →
  **重新解析写出结果**，实体数仍为 64。
- `test_ifcplusplus_ohos`（鸿蒙专项，13 项）：Carve CSG 布尔运算（交集 10 面 / 8 顶点，并集 26 面 / 20 顶点）→
  IFC GUID 基 64 编解码 64/64 回环 + 2 项非法输入拒绝 → 50 面墙模型 STEP 回写再解析守恒。

其中 CSG 用例直接覆盖步骤 3 的修复路径（`intersect.cpp` / `mesh.cpp` / `spacetree.hpp`）。

---

## 5. 附：本次踩到的相邻坑（同一类"调用约定写错"）

Carve 的 `MeshSet` 从点集构造时，`face_indices` 是**"每面一段"的扁平编码** `[N, i0, i1, ..., iN-1]`，
**不是**三角形索引三元组：

```cpp
// 错误：纯三元组，会被 CARVE_ASSERT(face_indices[p] > 1) 拒绝 → 抛 carve::exception → SIGABRT
const std::vector<int> faces = { 0,2,1,  0,3,2, ... };

// 正确：每面以顶点数 N 开头
const std::vector<int> faces = { 3, 0,2,1,  3, 0,3,2, ... };
```

`mesh_impl.hpp` 中 `CARVE_ASSERT(face_indices[p] > 1)` 校验这一点。**不要用 `-DCARVE_NODEBUG` 关掉断言来"解决"中止**——
那只会让错误数据静默流过、掩盖真实的误用。正确做法是把调用约定改对（见 `forbid_2_*`）。
