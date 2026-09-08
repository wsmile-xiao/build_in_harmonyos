# bobcat 6.14.00 适配笔记

## 编译环境
- 构建系统: custom（上游 icmake 13.00.03 驱动的 `./build light`；conanfile 以 Python 复刻其编译/链接语义）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，libc++）
- 状态: built
- C++ 标准: C++20（上游要求；`ICMAKE_CPPSTD=--std=c++20`）

## 编译步骤

1. 源码：Debian 权威镜像 `bobcat_6.14.00.orig.tar.gz`（上游 sourcetar 布局，`./build` 位于顶层），
   SHA-256 `92ac3879e92ec941c67c0505976349d4ba8c239a71a797257ad795afa514f5d2`（与 Debian .dsc 声明一致）。
   同 tag GitLab 归档（仓库根布局）内容一致性已比对。
2. 原生探索构建（设备端，真实上游工具链）：
   - 引导构建 icmake 13.00.03（GitLab tag；任务私有前缀，未改全局环境）
   - `ICMAKE_CPPSTD=--std=c++20 CXX=clang++ ./build light` →
     `tmp/liba/libbobcat.a`（8.25 MB）、`tmp/libso/libbobcat.so.6.14.00`（1.15 MB，soname libbobcat.so.6）、
     `tmp/bobcat/` 公共头 128 个（light 类集全集）+ 3 个探索期残留头（非上游安装集）
3. 原生消费者验证：clang++ 链接 libbobcat.so，运行 11 项 API 行为断言全部通过
   （Exception/DateTime/Pattern/String/Glob/Process，含真实 fork/exec 子进程）。
4. Conan 构建：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
   （conanfile.build() 复刻 light 语义，见 conanfile.py 头注释；日志 bobcat_compile_log.txt）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `strerror_r` 返回 int 不能初始化 char*（exception/errnodescr.cc） | OHOS musl 为 POSIX strerror_r；上游按 glibc GNU 语义 | 补丁 0001，POSIX 等价写法 |
| 2 | missing 'typename'（clockbase/highsysclock 公共头与 .f） | gcc 宽松、clang 严格（P0634 未覆盖别名/该场景） | 补丁 0002，补显式 typename |
| 3 | `std::chrono::clock_cast` 不存在 | C++23 特性，OHOS libc++15 未实现 | 补丁 0003，`file_clock::from_sys` 等价（C++20 规定的 sys 链转换） |
| 4 | filesystem.f 的 to_sys 结果隐式转换失败；`fs::file_status` 比较报 invalid operands | OHOS libc++ 类型差异：system_clock::duration=微秒、file_clock rep=__int128/nano | 补丁 0004，显式 time_point_cast + type() 比较 |
| 5 | reverse_iterator< const_hdr_iterator > 静态断言失败 | 迭代器实现有 operator-- 但 category 声明为 input（声明错误；libstdc++ 不检查） | 补丁 0005，改 bidirectional_iterator_tag |
| 6 | 裸 `mode_t`（7 个公共头）、裸 `STDxx_FILENO`（proc.ih） | 头未包含 sys/types.h / unistd.h，依赖 glibc 环境传递包含 | 补丁 0006/0007，显式包含 |
| 7 | `bind(...)` 解析为 std::bind（__bind 对象无 operator<） | 内部头 using namespace std；libc++ 下模板精确匹配抢占 POSIX bind | 补丁 0008，改 `::bind` |
| 8 | 上游 icmake 依赖（W0b） | 设备与 CI 均无 icmake | conanfile 复刻 light 语义（CI 可重复）；真机用引导构建的 icmake 13.00.03 完成上游构建实证 |

## 源码修改

全部补丁见 `patches/`（8 个，均在 pristine 树验证干净回放），声明见 `conandata.yml`。
主题：musl/libc++ 与 glibc/libstdc++ 兼容性（portability）为主，1 个真实缺陷修复
（0005 迭代器 category 与实现不符）。

## 依赖版本

无第三方依赖（light 模式）。上游完整模式（`./build libraries all`）需要的
openssl/readline/X11/libmilter 类在 light 模式中按上游文档排除
（W0 实证：ohpcd 制品仓无 openssl/readline 的 OHOS binary）。

## 验证结果

```bash
# 原生上游构建（设备端，icmake 13.00.03）
$ icmake -t. build light   # exit 0；产出 libbobcat.a / libbobcat.so.6.14.00 / 公共头 128

# 原生消费者（链接动态库，真实 API 行为断言）
$ ./test_bobcat
consumer OK: 11 checks passed   # exit 0

# Conan 构建（CI 等价路径）
$ conan create . --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package: consumer OK: 11 checks passed
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libbobcat.so.6.14.00 | 1.15 MB | 共享库（soname libbobcat.so.6，含软链） |
| libbobcat.a | 8.25 MB | 静态库（shared=False 时交付） |
| include/bobcat/* | 128 头 | 公共头（`#include <bobcat/xxx>`，上游安装布局；light 类集全集） |

## 注意事项

- 下游使用本包需以 **C++20** 编译（bobcat 公共头使用 C++20 特性）。
- light 构建不含 SSL/Readline/X11/Milter 类（BigInt、DiffieHellman、DigestBuf、
  ReadLineBuf、Milter、Xpointer 等）；如需这些类需先发布 openssl/readline 依赖。
- 与上游构建的说明性差异：上游一次产出 .a + .so；Conan 由 shared option
  驱动只编所需遍（产物语义不变，编译时间减半）。
- 上游无自动化测试套件，测试统计见 test_package/MANIFEST.yml（上游 TOTAL=0；
  消费者 11 断言）。
