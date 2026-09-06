# spirit-po 1.1.2 适配笔记

## 范围

- 上游标签：`v1.1.2`
- 上游提交：`3e3e4d75fa1ce19735c37fad74e188f4faa9c333`
- 构建系统：custom（库本身 header-only；上游 `test/Makefile` 仅用于测试）
- 编译日期：2026-09-03
- 目标：OHOS/aarch64，clang 15，libc++，C++11
- 当前状态：built（设备验证完成，尚未经过合并后的 release upload）

## 依赖预检（W0）

`boost/1.90.0` 使用工作区 Conan 2.29.1 的 `conan download --only-recipe -r=ohpcd` 核验通过；同一 profile 下 `conan install --build=never` 已回读本地缓存二进制。spirit-po 是 header-only，Boost 是唯一 Conan 构建依赖。

## 上游问题与补丁

未修改上游测试。严格 OHOS clang 编译上游 `test/main.cpp` 首次失败：

```text
include/spirit_po/exceptions.hpp:24:3: error: unknown type name 'uint'; did you mean 'int'?
```

上游 `exceptions.hpp` 的 `iterator_context()` 和 debug 宏启用时的 `po_message.hpp` 使用未声明的 `uint`。这是公开头文件在严格 C++11 编译器下的可复现可移植性问题，不是通过空壳 stub 绕过。使用规范 `refresh-patch --auto` 生成：

- `0001-include-spirit_po-exceptions.hpp.patch`：`uint count` → `std::size_t count`
- `0002-include-spirit_po-po_message.hpp.patch`：debug 循环索引 `uint` → `std::size_t`

## 构建与测试

上游单元测试实际命令（补丁应用后的源码）：

```bash
make -C /storage/Users/currentUser/builds/spirit-po-1.1.2.work/test \\
  clean main CXX=/data/service/hnp/bin/clang++ \\
  BOOST_DIR=/storage/Users/currentUser/.conan2/p/boost4c158f4cbbd30/p/include
/storage/Users/currentUser/builds/spirit-po-1.1.2.work/test/main
```

结果：`All 126 tests passed.`，退出码 0。上游 22 个 unit PO fixture（12 个正常 + 10 个失败输入）由这 126 个 assertion-level checks 覆盖。

上游 `test_libintl` 目录含 206 个 PO 数据驱动用例，但本 OHOS 环境虽然有 `msgfmt 0.26`，没有 `libintl.h`，也没有 `libintl.so`/`libintl.a`；`test_libintl/CMakeLists.txt` 明确要求 `find_package(Intl REQUIRED)` 并链接 `${INTL_LIBRARIES}`。因此 206 项不能运行，按允许的环境限制/缺特性原因明确跳过，不将跳过伪报为通过，也没有修改测试代码或用 stub 代替 libintl。

## Conan 消费者测试

`test_package/` 使用 CMakeDeps/CMakeToolchain，真实链接 `spirit-po::spirit-po`，测试 `catalog::from_range`、header metadata、`size()`、`gettext`、`pgettext`、`ngettext` 和缺失 key 回退，共 1 个消费者可执行用例（7 个断言）。

## 用例统计口径

| 类别 | 上游用例数 | 适配后/设备结果 | 口径 |
|---|---:|---:|---|
| 单元测试 | 126 | 126 PASS | `test/main.cpp` 运行时 assertion |
| libintl 对照集成 | 206 | 206 SKIP | 每个 `test_libintl/po/*.po` 一个数据驱动 executable-level case |
| 其他 | 0 | 0 | 无其他上游 suite |
| **合计** | **332** | **126 PASS + 206 SKIP / 332** | 分母保留，失败 0 |
| 消费者测试（独立） | — | 1 PASS | 不重复并入上游 332 分母 |

## 知识库扩展（路径 B）

新增草稿 `knowledge/drafts/E543-draft-SP11.{kv,md}`，主题是严格 OHOS C++11 下未限定整数类型导致 header-only Spirit/PO 配方失败，以及将上游 unit assertion、libintl 数据驱动 case、消费者 case 分开统计并对有据跳过保持完整分母。已对 E035、E099、E257、E307、E321、E322 及 Boost header overlay 草稿查重，新增价值集中在 Spirit/PO 的公开头可移植性和测试计数/跳过证据闭环。
---

**编译结束**: 2026-09-03 23:26
**最终状态**: built
