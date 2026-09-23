# DRAFT-bulletml-0.0.6-auto_ptr-cpp17-compat：C++17 移除 `std::auto_ptr` 的布局兼容 shim

## 现象

将 2003 年代旧 C++ 库（本任务为 bulletml 0.0.6 / libBulletML）适配到 HarmonyOS
PC 时，库本身以 C++98（上游 `-ansi -pedantic`）编译成功，但**消费者**按 OHOS
profile 的 `compiler.cppstd=17` 编译时在公共头模板实例化阶段失败：

```text
fatal error: no template named 'auto_ptr' in namespace 'std'
    std::auto_ptr<Number> val_;
                ^
fatal error: no template named 'auto_ptr' in namespace 'std'
    explicit scoped_ptr(std::auto_ptr<T> p): ptr(p.release())
                       ^
```

报错点同时出现在：

- 库的公共 API 头（`bulletmltree.h`：成员 `std::auto_ptr<Number> val_;`）；
- 随包捆绑的 boost 1.29 年代头（`scoped_ptr.hpp` / `shared_ptr.hpp` /
  `detail/shared_count.hpp` 的 `std::auto_ptr<T>` 构造与赋值）。

## 根因

`std::auto_ptr` 自 C++17 起被标准库移除。OHOS 适配 profile 统一设定
`compiler.cppstd=17`，因此消费者包含这些头文件时，模板声明直接引用已不存在的
`std::auto_ptr`。库自身的构建若沿用上游 C++98 标志则不受影响——这正是"库能编译、
消费者编译失败"的典型割裂来源。

## 可复用修复模式

在**公共头**内联一个最小、布局兼容的 `auto_ptr` shim，并用宏在语言标准间切换：

```cpp
#if __cplusplus >= 201703L
namespace bulletml_compat {
template <class T_>
class auto_ptr {
public:
    auto_ptr() : ptr_(0) {}
    explicit auto_ptr(T_* p) : ptr_(p) {}
    auto_ptr(auto_ptr& o) : ptr_(o.release()) {}
    ~auto_ptr() { delete ptr_; }
    auto_ptr& operator=(auto_ptr& o) { reset(o.release()); return *this; }
    T_* release() { T_* p = ptr_; ptr_ = 0; return p; }
    void reset(T_* p = 0) { if (p != ptr_) { delete ptr_; ptr_ = p; } }
    T_* get() const { return ptr_; }
    T_* operator->() const { return ptr_; }
    T_& operator*() const { return *ptr_; }
private:
    T_* ptr_;
};
}  // namespace bulletml_compat
#define BULLETML_AUTO_PTR bulletml_compat::auto_ptr
#else
#define BULLETML_AUTO_PTR std::auto_ptr
#endif
```

随后：

1. 公共头成员声明改用宏：`BULLETML_AUTO_PTR<Number> val_;`
2. bundled boost 头（`scoped_ptr.hpp` / `shared_ptr.hpp` /
   `detail/shared_count.hpp`）的 `std::auto_ptr<T>` 全部改为 `BULLETML_AUTO_PTR<T>`；
   boost 头在公共头之后被包含（经 `bulletmlrunner.h`），宏已可见，无需独立 compat 头。
3. 库自身仍以 C++98 编译，`BULLETML_AUTO_PTR` 解析为 `std::auto_ptr`，ABI 不变。
4. 补丁用 `patches/` 固化（refresh-patch --auto），避免把宏定义散落在配方里。

## 验证方法

1. 干净解包上游 tarball → 应用补丁 → `make CC=clang CXX=clang++ LD=clang++`
   （库以 C++98 编译）成功；
2. 消费者测试以 `-std=c++17` 编译并链接运行，实际调用库 API 通过
   （bulletml：解析 1 个 top action、发射 2 颗子弹）；
3. `conan-verify`（ohos-aarch64 profile，cppstd=17）G2 干净构建通过。

## 适用边界与反例

- **适用**：公共头或随包头（含 bundled boost）直接以 `std::auto_ptr` 作为成员/
  形参类型的旧 C++ 库；消费者按 cppstd>=17 编译。
- **反例**：若库依赖**外部** boost 且可升级版本，应升级/替换 boost，而不是为
  bundled 头打 shim；若库公共头可整体现代化，优先迁移到 C++11 智能指针。
- **限制**：shim 只保证布局与常用语义（拷贝转移所有权、release/reset/get），
  不实现 `std::auto_ptr` 的全部标准接口；对确实依赖罕见 auto_ptr 语义的代码
  需要逐个核对。`__cplusplus` 分支基于语言标准，不使用平台宏。
