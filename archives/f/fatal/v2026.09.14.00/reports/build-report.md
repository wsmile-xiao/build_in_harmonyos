# 编译过程记录 — fatal v2026.09.14.00

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名称 | fatal（Facebook Template Library） |
| 版本 | v2026.09.14.00（上游 tag `v2026.09.14.00`） |
| 编译日期 | 2026-09-25 |
| 包类型 | **header-only**（无编译产物，仅有头文件树） |
| 补丁数量 | 2（均为 portability） |

## 环境信息

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS PC / HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4（ohos-sdk 26.0.0.18 native） |
| 标准库 | libcxx-ohos（C++17） |
| 构建系统 | 无（header-only）；上游 harness `test.sh` + `compile.sh` |
| 包管理器 | Conan 2.x |

## 源码获取

```bash
# 官方 archive tag（sha256 已核验）
curl -sL -o fatal-v2026.09.14.00.tar.gz \
  https://github.com/facebook/fatal/archive/refs/tags/v2026.09.14.00.tar.gz
sha256sum fatal-v2026.09.14.00.tar.gz
# da43cabebbe0a1b279f5eaf3fe7d3460ed7320887ca033d805b84079bc29e3a1
tar xzf fatal-v2026.09.14.00.tar.gz   # → fatal-2026.09.14.00/
```

## 补丁

| 序号 | 文件 | 类型 | 内容 |
|------|------|------|------|
| 0001 | `patches/0001-rope-std-iterator-deprecated.patch` | portability | `fatal/string/rope.h` 的 `const_iterator` 去掉 C++17 弃用的 `std::iterator` 基类，改为等价显式 typedef（修 `-Werror -Wdeprecated-declarations`） |
| 0002 | `patches/0002-deprecated-transform-test-libcxx-tuple-element.patch` | portability | `fatal/type/test/deprecated_transform_test.cpp` 对 `std::tuple_element<2, std::pair>` 的「不完整类型」断言加 `#if !defined(_LIBCPP_VERSION)` 守卫（新版 libc++ 的越界 `static_assert` 使该探测成为硬错误） |

## 构建/打包

header-only 无需编译：`package()` 只把 `fatal/` 头文件树安装到包里。

```
<pkg>/include/fatal/**/*.h      # 157 个头文件
<pkg>/licenses/LICENSE
```

`build()` 的全部职责是执行上游官方测试（详见 `reports/test-report.md`）。

## 关键日志（真机实测）

```
$ conan create archives/f/fatal/v2026.09.14.00 --profile=ohos-aarch64
[fatal upstream tests] upstream official tests via ./test.sh (fatal's make check / ctest equivalent; header-only harness)
[fatal upstream tests] harness=test.sh+compile.sh TUs=67 declared_cases=845 compiler=/data/service/hnp/bin/clang++ jobs=4
[fatal upstream tests] fatal/benchmark/test/benchmark_test.cpp          compile=ok run=ok 1/1
[fatal upstream tests] fatal/codec/test/varint_test.cpp                 compile=ok run=ok 55/55
...（67 行逐 TU 结果，全部 compile=ok run=ok）
[fatal upstream tests] fatal/string/test/rope_test.cpp                  compile=ok run=ok 47/47
[fatal upstream tests] fatal/type/test/deprecated_transform_test.cpp    compile=ok run=ok 85/85
[fatal upstream tests] SUMMARY: TUs=67 compiled=67 executed_cases=839 passed=839 failed=0 skipped=0 pass_rate=100.0%
[Launching test_package]
[fatal consumer] fatal v2026.09.14.00 consumer tests OK: 3/3 passed
```

## 阻塞与解决

| # | 问题 | 解决 |
|---|------|------|
| 1 | 上游 `compile.sh` 固定写 `/tmp/.build`，而鸿蒙 PC 的 `/tmp` 是只读 erofs（实测 `touch /tmp/_probe` → `Read-only file system`） | 配方不复用 `compile.sh`，直接编译到 Conan 构建目录，编译参数逐字一致 |
| 2 | OHOS 下 subprocess 不通过 PATH 解析裸可执行名（`posix_spawn` 差异） | 编译器使用绝对路径，保留 PATH 兜底 |
| 3 | `rope.h` 的 `std::iterator` 在 `-Werror` 下编译失败 | patch 0001 |
| 4 | `std::tuple_element` 越界 `static_assert` 击穿 SFINAE 探测 | patch 0002 |

## 产物基线（头文件数量）

```
$ find <pkg>/include -name '*.h' | wc -l
157
```

---
*记录时间: 2026-09-25*
