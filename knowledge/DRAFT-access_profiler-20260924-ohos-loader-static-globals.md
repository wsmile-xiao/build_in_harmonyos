# DRAFT: OHOS PIE 装载期外部链接全局对象 SIGSEGV -> 改 static 内部链接修复

- 来源库：access_profiler 20260924（arvidn/access_profiler）
- 类型：路径 B 知识草稿（装载器/链接适配，跨库可复用）

## 问题

上游 `access_profiler.cpp` 在文件作用域以外部链接（默认可见性）声明 7 个全局对象：

```cpp
std::mutex pagemutex;
std::unordered_map<uintptr_t, type_t> pagemap;
std::mutex typemutex;
std::unordered_map<std::type_info const*, std::uint8_t> typemap;
int next_typeidx = 0;
std::vector<access_t> access;
pthread_key_t last_page = 0;
```

使用 OHOS aarch64 工具链（clang 15 / lld，PIE + `BIND_NOW`）链接后，程序在
**main 之前、静态初始化/装载期** 以 `Signal 11 (core dumped)`（exit 139）崩溃。

## 根因

OHOS（HongMeng Kernel 1.12 / musl 系）PIE 装载器对外部链接（可预占、默认可见性）
全局对象的初始化路径处理存在缺陷/差异；`static`（内部链接、不可预占、由主程序
直接持有）后初始化路径正常。触发面是"外部链接全局对象 × OHOS PIE 装载器"，
与具体容器类型（mutex/unordered_map/vector/pthread_key_t）无关。

## 排查过程（二分定位）

1. **main 未进入**：main 首行 fopen/fprintf 探针、库自动初始化对象探针均无输出
   → 崩溃发生在装载/静态初始化期。
2. **与函数无关**：将库中函数全部去掉、仅保留全局对象的最小程序仍崩溃
   （exit 139）。
3. **与类型无关**：最小程序使用完全相同的类型（std::mutex / unordered_map /
   vector / pthread_key_t），外部链接形态崩溃、`static` 形态正常（exit 0）。
4. **结论**：触发面 = 外部链接全局对象 × OHOS PIE 装载器。

## 修复

将文件内使用、未被公开 API（access_profiler.hpp）引用的 7 个全局对象全部改为
`static` 内部链接：

```cpp
static std::mutex pagemutex;
static std::unordered_map<uintptr_t, type_t> pagemap;
...
```

补丁使用标准 C++ `static` 关键字，不含 `__OHOS__` 平台宏（符合 R8/PF5）。

## 验证

| 项目 | 结果 |
|------|------|
| minimal repro 二分 | extern 形态 exit 139 / static 形态 exit 0 |
| 上游测试 test | exit 0，stdout=55，access_profile.out = `test / 52: 1`（与上游 README release 输出一致） |
| conan create（G2 干净构建） | exit 0 |
| conan-verify 全部门禁 | G0-G4 + L2/L4/L5 通过 |
| W3 本地 CI | L0/L1/L4/L5 pass，1/1 通过 |

## 适用边界

- 适用：OHOS（及同系 musl/HongMeng Kernel）上以 PIE 链接、含文件作用域
  外部链接全局对象的可执行程序与库消费者；任何上游声明非 static 容器/互斥量
  全局对象的 C++ 库都可能命中。
- 反例/不适用：仅交付静态库即可、或目录级多个头文件共享同一全局状态（必须
  保持外部链接以跨 TU 共享）的场景，不能盲目 static；已在公开头文件声明
  extern 的符号不能改 static（会破坏 ABI/链接）。

## 查重与关系

- 四范围查重（正式知识/图谱索引/草稿/正式文档）均未命中：E444（.init_array
  构造器未执行类）、E457/DRAFT-libxmlb（静态依赖嵌入 .so 双实例运行时崩溃）、
  E234/E236（PIC/libtool 链接配置）均为不同根因/阶段/解法。
- 七轴：exact=false, causal=false, trigger=partial(SIGSEGV+OHOS 面), 
  solution=false, combination=true, boundary=true, test_migration=true。
- similar_to: E444, E457；caused_by/prerequisite_of/conflicts_with: 无。

## 关联交付

- 本草稿与 `archives/a/access_profiler/20260924/**` 在同一 PR 交付；
  草稿仅保留在 `knowledge/` 根目录，不修改正式知识图谱/文档/索引。