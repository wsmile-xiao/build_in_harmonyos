# E429 — 老 C++ 源码在 clang 15 + libc++ 下两处典型不可编译（隐式 ostream→bool、非标准类型 uint）

## 基本信息
- **严重度**: 2
- **类别**: portability, cpp, libcxx, clang, legacy-code
- **来源**: vbrfix 0.24 适配（2003 年 KDevelop/autotools 工程，clang 15.0.4 + libc++，OHOS aarch64）
- **状态**: 草稿（draft）

## 错误特征

```
./wputil.h:202:12: error: no viable conversion from returned value of type
    'std::ostream' to function return type 'bool'
    return out << in.rdbuf();
    ^~~~~~~~~~~~~~~~~~~~~~~
/…/libcxx-ohos/include/c++/v1/ios:626:14: note: explicit conversion function
    is not a candidate
    explicit operator bool() const {return !fail();}

vbrfix.cpp:298:36: error: unknown type name 'uint'; did you mean 'int'?
    bool e=false;unsigned char c;uint correctv1=0,correctv2=0,p=0;
```

## 触发条件

- 构建系统: autotools（configure + make），任意
- 阶段: `make`（编译期）
- 源码年代: 约 2000–2010 年、当年以 gcc + libstdc++ 编译通过的老 C++ 项目
- 工具链: clang 15 + libc++（OHOS 默认）

## 根因分析

两处都是「语言/运行库现代化」问题，与平台无关，只是换成 clang + libc++ 后才暴露：

1. **隐式 `std::ostream → bool` 转换被移除**
   老代码常写 `return out << in.rdbuf();`（函数返回 `bool`）——依赖 libstdc++ 时代的
   `std::basic_ios::operator void*()`（`!fail()` 时返回非空指针）完成隐式转换。
   libc++ 只提供 **explicit** `operator bool()`，且 `operator void*` 已被移除，
   因此 `std::ostream` 无法再隐式转 `bool`，编译失败。

2. **非标准类型 `uint`**
   `uint` 是老 BSD `<sys/types.h>` 提供的非标准 typedef；glibc / libc++ 均不提供。
   在 gcc + glibc 环境下常被其它头文件间接引入而“碰巧可用”，换工具链后即报
   `unknown type name 'uint'`。

## 解决方案

### 推荐方案（最小改动，无语义变化、无平台宏）

```diff
--- a/vbrfixc/wputil.h
+++ b/vbrfixc/wputil.h
     // fast portable file copy
-    return out << in.rdbuf();
+    out << in.rdbuf();
+    return !out.fail();
```

```diff
--- a/vbrfixc/vbrfix.cpp
+++ b/vbrfixc/vbrfix.cpp
-      bool e=false;unsigned char c;uint correctv1=0,correctv2=0,p=0;
+      bool e=false;unsigned char c;unsigned int correctv1=0,correctv2=0,p=0;
```

- `return !out.fail();` 与原隐式转换（`operator void*` → `!fail()`）**语义等价**。
- `uint` → `unsigned int` 为保类型宽度最小改动（如项目另有 `typedef unsigned int uint;`
  的统一头文件，亦可集中定义一次）。
- **不**加 `#ifdef __OHOS__` 守卫：这是通用现代编译器可移植性修复，不是平台专有逻辑
  （R8 口径：patches/ 默认不引入平台宏）。

### 禁止做法

- ❌ 用 `-Wno-*` / `-fpermissive` / 降 `compiler.cppstd` 掩盖——`operator bool` 是
  explicit 而非警告，降标准也无效（C++98 下 libc++ 同样不提供 `operator void*`）。
- ❌ 为过编译把 `copyFile` 的返回值写死 `return true;`——掩盖真实 I/O 失败语义。
- ❌ 直接改 `configure`/`Makefile` 注入 `-include` 补丁头来“伪造”类型/转换。

## 验证

```bash
# 1. 定位两处旧写法
grep -n 'return out << in.rdbuf' <src>/vbrfixc/wputil.h
grep -n '\buint\b' <src>/vbrfixc/vbrfix.cpp

# 2. 打补丁后编译应 0 error
make -j4 2>&1 | grep -c 'error:'      # 期望 0

# 3. 产物可用性
./vbrfixc/vbrfixc                    # 期望打印用法横幅，退出码 0
```

## 关联条目

- 相关: **E293**（老 C++ 动态异常规格 `throw()` / `register` 在 C++17 下的同类问题）—
  同属「老 C++ 源码 + 现代 clang」这一族，可合并为「legacy C++ under modern clang」小节。
- 相关: **E191**（libc++/libc++abi 链接问题）— 同为 libc++ 切换差异面。
