# DRAFT-fast-cdr-2.3.5-cdrversion-enum-scope — CdrVersion 枚举作用域知识草稿

**路径**: B（知识库扩展）
**来源任务**: fast-cdr-2.3.5-r01-bootstrap-and-adapt-pc1-11-20260903T012213Z
**触发事件**: fast-cdr 2.3.5 `conan-verify` G2 环节 test_package 消费者测试编译错误

## 问题

eProsima Fast-CDR 的 `CdrVersion` 枚举（`CORBA_CDR=0`、`DDS_CDR=1`、`XCDRv1=2`、`XCDRv2=3`）声明在 `include/fastcdr/CdrEncoding.hpp` 的 `eprosima::fastcdr` 命名空间作用域（`typedef enum { ... } CdrVersion;`），**不是** `class Cdr` 的嵌套成员。

消费者按直觉写 `eprosima::fastcdr::Cdr::DDS_CDR` 作为 `Cdr` 构造函数第三参（`cdr_version`）实参时，clang 报：

```
error: no member named 'DDS_CDR' in 'eprosima::fastcdr::Cdr'
```

## 根因

```cpp
// include/fastcdr/CdrEncoding.hpp, namespace eprosima::fastcdr
typedef enum {
    CORBA_CDR = 0,
    DDS_CDR = 1,
    XCDRv1 = 2,
    XCDRv2 = 3
} CdrVersion;

// include/fastcdr/Cdr.h line 167-168
Cdr(FastBuffer&, const Endianness endianness = DEFAULT_ENDIAN,
    const CdrVersion cdr_version = XCDRv2);
```

枚举与 `class Cdr` 同层命名空间，`DDS_CDR` 只是枚举值而非 `Cdr` 成员。API 文档注释写法 `CdrVersion::DDS_CDR` 容易让从其他库（如 FastDDS）移植串行化代码的开发者误写成 `Cdr::DDS_CDR`。

## 方案

```cpp
eprosima::fastcdr::Cdr cdr(fastbuffer,
                           eprosima::fastcdr::Cdr::DEFAULT_ENDIAN,
                           eprosima::fastcdr::CdrVersion::DDS_CDR);
```

或省略第三参（默认 `XCDRv2`）。不要给 `Cdr` 类打补丁硬塞嵌套别名——上游头文件保持原样，配方零补丁。

## 验证

- 修复后 `ohc-run.py conan-verify fast-cdr 2.3.5` G2 通过（milestone=conan_verify_passed）
- test_package ctest：`100% tests passed, 0 tests failed out of 1`
- W3 本地 CI：100% (1/1)，L1e sabotage 反向验证确认测试真实依赖包产物

## 适用边界

- 针对 fast-cdr 2.3.5 头文件布局；上游若迁移枚举进 `class Cdr`，限定名写法依然成立
- 不适用于其他序列化库的同名枚举
- 验证命令：`python3 <SKILL_ROOT>/scripts/ohc-run.py conan-verify fast-cdr 2.3.5`

## 反例与限制

- 禁止为快速通过编译而 patch `Cdr` 类添加嵌套别名（R8：补丁平台宏/无实质逻辑变更禁区）
- 库本身编译、安装、config.h 生成均不受影响，仅消费者限定名写法需注意

## 查重差异

- E130/E133/E196（`no member named 'nullptr_t'` 等）：musl/libcxx 头文件冲突，不同根因
- E469（`no member named 'bind_port' in 'httplib::Server'`）：cpp-httplib API 演进，不同库
- 本条目：fastcdr 独立枚举作用域（`CdrEncoding.hpp` 命名空间级 `typedef enum`），知识库无等价条目