# DRAFT-uc-echo-1.12-tr1-std-cpp11-modernization

OHOS clang/libc++ 无 C++ TR1 头：pre-C++11 源码报 `fatal error: 'tr1/unordered_map' file not found`

## 一句话方案
纯文本语义等价替换（TR1 即 C++11 std 组件原型）：`#include <tr1/X>` → `#include <X>`；`std::tr1::X` → `std::X`；裸 `tr1::X` → `std::X`。

## 错误特征
- `fatal error: 'tr1/unordered_map' file not found`（亦见 tr1/memory、tr1/tuple、tr1/functional）
- 源码内可 grep 到 `#include <tr1/`、`std::tr1::`、裸 `tr1::`

## 根因
2011 年前后代码常用 TR1 扩展。GNU libstdc++ 长期保留 tr1 兼容头所以这些代码在 Linux 上一直能编；
OHOS clang 用 libc++，libc++ 从未提供 std::tr1（TR1 已并入 C++11 std）→ 头文件不存在。
工具链/标准库属性，与构建系统（make/cmake/autotools）和包逻辑无关，换机器不消失。

## 为什么文本替换是语义等价的
- TR1 的 unordered_map/shared_ptr/tuple/get/make_tuple 就是 C++11 std 对应组件的原型，模板签名一致；
- std::unordered_map 的 Hash/KeyEqual 模板参数要求与 TR1 相同（自定义哈希返回 size_t、等值谓词 operator()(a,b)），
  TR1 时代的仿函数通常无需任何改动；
- 注意 sed 顺序：先 `s|std::tr1::|std::|g` 再 `s|tr1::|std::|g`，否则产生 `std::std::`。

## 实证（uc-echo 1.12）
- 首错：DNASeq.hpp:6 `#include <tr1/unordered_map>` not found；
- 清点：10 个 .cpp/.hpp 共 41 处 tr1 引用（unordered_map/shared_ptr/tuple/get/make_tuple）；
- 替换后：6/6 二进制构建成功；消费者端到端纠错测试（构造 12 条目输入，金标逐字断言）+ 两次运行字节级确定性全绿；
- Kmer_hash/Kmer_cmp 与 std::unordered_map 兼容性已逐一核对（cmp 是等值谓词、hash 返回预计算值）。

## 同现陷阱
aarch64 上 plain char 默认无符号：pre-C++11 代码常用 char 存 -1（uc-echo 的 `index_t`/`nerr=-1`），
替换 tr1 后若行为仍异常，加 `-fsigned-char`（配方 CXXFLAGS 级，不进补丁）。

## 禁止
- 为 TR1 兼容 vendor boost 或拷贝第三方 tr1 头；
- 平台宏（`__OHOS__`）包裹 tr1 代码做双路径（违反 R8/PF5）；
- 手写 tr1 兼容层塞 namespace std（UB 边缘，仅作垫片兜底）。
