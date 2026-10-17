# E543 — PkgConfigDeps 嵌套 include 导出导致同名转发头遮蔽真实公共头

## 错误特征

上游源码已经显式包含正确的公共头，但编译仍报告该头应提供的符号不存在：

```text
main.cc:1322:26: error: no member named 'join' in namespace 'fmt'
                    fmt::join(argv + optind, argv + argc, " "));
                    ~~~~~^
```

本例源码包含 `<fmt/ranges.h>`，而单独编译一个最小探针时 `fmt::join` 存在；
只有经 Conan `PkgConfigDeps` 和 Meson 生成的真实编译命令失败。

## 触发条件

- Conan 2 消费方使用 `PkgConfigDeps`，上游通过 Meson `dependency()` 探测依赖。
- 某依赖同时导出公共根和嵌套根，例如 `include` 与 `include/spdlog`。
- 嵌套根内存在另一依赖的同名前缀目录，例如
  `include/spdlog/fmt/ranges.h`。
- 生成的编译命令把该嵌套根排在真实 fmt 公共根之前。

本次真机编译命令的关键顺序为：

```text
-I<spdlog>/include
-I<spdlog>/include/spdlog
-I<fmt>/include
-I<fmt>/include/fmt
```

## 根因分析

预处理器解析上游的 `<fmt/ranges.h>` 时，先在
`<spdlog>/include/spdlog` 下命中 `fmt/ranges.h`，因此读到的是
`spdlog/fmt/ranges.h` 转发头，而不是 fmt 自己的公共头。

该转发头在 `SPDLOG_FMT_EXTERNAL` 模式下再次执行：

```cpp
#include <fmt/ranges.h>
```

搜索顺序未变，它再次命中自身；由于 `#pragma once`，第二次包含立即结束，
真正的 fmt `ranges.h` 从未加载，所以预处理结果里没有 `fmt::join` 声明。
这不是 fmt 12 API 变化，也不是上游漏 include，而是 Conan 包元数据经
`PkgConfigDeps` 展开后的头文件搜索路径碰撞。

## 解决方案

### 推荐方案：在消费方生成 `.pc` 前规范 include 根

软件 PR 不能顺带修改依赖包时，在消费方 `generate()` 中先收窄相关依赖的
`cpp_info.includedirs`，再运行 `PkgConfigDeps`：

```python
def generate(self):
    for dep_name in ("fmt", "spdlog", "catch2"):
        dep = self.dependencies.get(dep_name)
        if dep and dep.package_folder:
            dep.cpp_info.includedirs = [
                os.path.join(dep.package_folder, "include")
            ]
    PkgConfigDeps(self).generate()
```

公共根已经可以解析 `<spdlog/...>`、`<fmt/...>` 和 `<catch2/...>`；删除嵌套
`-I` 不会降低 API 可见性，却能消除跨包同名前缀碰撞。

### 根治方案：修正生产方包元数据

若依赖包允许发布修订版本，应在其 `package_info()` 中只导出必要的公共 include
根，并用真实消费者验证生成 `.pc` 的 `Cflags`。这会一次修复全部下游，但应在
依赖包自己的原子 PR 中完成。

## 验证方法

```bash
# 修复前：没有输出
clang++ <真实编译参数> -E src/main.cc | grep "auto join(It"

# 修复后：能看到 fmt/ranges.h 中的声明
clang++ <真实编译参数> -E src/main.cc | grep "auto join(It"

# 最终验证
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

`j4-dmenu-desktop/3.2` 真机验证结果：主程序和测试程序成功链接；Catch2
73 通过、0 失败、6 因系统 `/tmp` 只读跳过（256 条断言通过）；pytest
10 通过、0 失败、7 个终端模拟项跳过；消费侧功能测试通过。

## 禁止做法

- 不要删除上游 `fmt::join` 或给源码增加针对 Conan 缓存的绝对 include。
- 不要仅追加一个更靠前的 `-I<fmt>` 来赌搜索顺序；依赖图或生成器顺序改变后会复发。
- 不要把问题误判为 fmt 版本不兼容而无依据降级依赖。

## 关联条目与查重边界

- E133 同属 include 搜索顺序遮蔽，但它是全局系统 include 遮蔽 SDK/编译器头；
  本条是 Conan 依赖元数据形成的跨包同名前缀碰撞。
- E217 是已安装头目录与 `cpp_info.includedirs` 不匹配导致“找不到头”；本条能
  找到文件，但找到的是错误包的转发头。
- E348 是 `PkgConfigDeps` 模块命名/转发 `.pc` 问题；本条模块已找到，错误发生在
  `.pc` 的 `Cflags` 展开和预处理阶段。
