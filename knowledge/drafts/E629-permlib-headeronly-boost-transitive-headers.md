# E629 — header-only 包的接口面两处缺口（依赖头未按组件传递 / Boost≥1.90 隐式包含消失）

- **任务**: permlib 0.2.9（`feat/permlib-0.2.9`），纯头文件 C++ 模板库（置换群/BSGS）
- **日期**: 2026-09-20
- **结论**: 两处都是「包侧接口面」缺陷，不是平台差异 —— 补丁不含任何平台宏，配方对任意平台同一份

## 症状

### A. 消费者编译期 `file not found`（组件化依赖的包级目标没有 include）

header-only 包的公开头直接 `#include <boost/...>` 时，若配方只写
`requires("boost/1.90.0.4.1", transitive_headers=True)` 而不写组件级
`cpp_info.requires`，下游消费者编译自家 TU 时报：

```
fatal error: 'boost/shared_ptr.hpp' file not found
```

根因不是「boost 没装」——boost 包就在依赖图里。是 **boost 配方声明了 components**
（`headers` / `atomic` / `filesystem` / `unit_test_framework` …），此时 CMakeDeps 生成的
**包级**目标 `boost::boost` 的 `INTERFACE_INCLUDE_DIRECTORIES` 是空的，只有
`Boost::headers` 组件带 include 目录。`transitive_headers=True` 传递的正是那个空列表。

> 设备里若恰好另有 boost 头（harmonybrew / 系统前缀），消费者会被「喂饱」而编译通过 ⇒
> **设备绿、CI 红**。判据仍是「消费者在干净环境里编译」，见下。

permlib 实测：84 个公共头里 **47 个** 直接 include boost（`boost/foreach.hpp` 26 处、
`boost/scoped_ptr.hpp` 11 处、`boost/shared_ptr.hpp` 10 处、`boost/dynamic_bitset.hpp` 10 处 …）。

### B. Boost≥1.90 不再隐式提供 `boost::next()` 声明

permlib（2011 年前后的 C++98 模板库）在 4 个公共头里用 `boost::next`，但只 include 了
`<boost/utility.hpp>` / `<boost/iterator/...>` 等，靠旧 Boost 的间接包含拿到声明。
Boost 1.90 起不再传递，`conan create` 编译上游测试时报 **19 个错误**：

```
include/permlib/bsgs.h:315:32: error: no member named 'next' in namespace 'boost';
                                        did you mean 'boost::foreach_detail_::next'?
        unsigned long beta = *(boost::next(this->U[l].begin(), randomInt(this->U[l].size())));
                               ^~~~~~~~~~~
include/permlib/generator/schreier_generator.h:171:16: error: no member named 'next' in namespace 'boost';
                                        did you mean simply 'next'?
include/permlib/change/base_transpose.h:142:44: error: no member named 'next' in namespace 'boost'
```

（`note` 链会一路指到 libc++ 的 `std::binary_function` 弃用告警上，容易把方向带偏成
「编译器/标准库不兼容」。）

### C. 同批发现的第三处：上游模板死代码路径

`include/permlib/abstract_bsgs.h:139` 的 `setStabilizer()` 一直调用
`new AbstractBSGS<TRANS>(stabilizer, m_support)`，但类里只声明了
`AbstractBSGS(const boost::shared_ptr<PermutationGroup>&, bool computeSupport = true)` ——
第二个实参是 `boost::shared_ptr<std::set<dom_int> >`，**没有任何编译器会接受**。这是上游
潜在缺陷（模板方法未被实例化时不报错，一旦用到即失败）：

```
error: no matching constructor for initialization of 'AbstractBSGS<permlib::SchreierTreeTransversal<permlib::Permutation>>'
note: candidate constructor not viable: no known conversion from
      'const boost::shared_ptr<std::set<dom_int>>' to 'bool' for 2nd argument
```

## 修复

```python
# conanfile.py
def requirements(self):
    self.requires("boost/1.90.0.4.1", transitive_headers=True, transitive_libs=False)

def package_info(self):
    ...
    # 组件级！包级 "boost::boost" 的 include 目录为空（boost 配方声明了 components）
    self.cpp_info.requires = ["boost::headers"]
```

外加 5 个最小补丁（`refresh-patch --auto` 生成的 per-file 形态）：

| 补丁 | 内容 |
|---|---|
| `0001-include-permlib-abstract_bsgs.h.patch` | 补 `AbstractBSGS` 的 support 构造重载（症状 C） |
| `0002..0005` | 4 个 `boost::next` 使用点补 `#include <boost/next_prior.hpp>`（症状 B） |

补丁内**无任何平台宏**（无 `__OHOS__`、无平台分支），任意平台同一份修正。

## 复现命令（设备可直接执行）

```sh
TASK_DIR=$HOME/tmp/permlib-0.2.9
REPO=$HOME/ws/worktrees/permlib-0.2.9

# 0) 取 boost 包路径（组件 include 的实际来源）
BOOST=$(conan cache path boost/1.90.0.4.1:01d92cf349a0dd98ff915f4bd99a04430171517f)
ls "$BOOST/include/boost/next_prior.hpp"          # 存在 ⇒ 修 B 只需显式 include

# 1) 复现 B：用**未打补丁**的上游源编任一上游用例，报 no member named 'next'
SRC=$(conan cache path permlib/0.2.9 2>/dev/null || echo "$HOME/ws/tmp/builds/permlib-0.2.9.work")
clang++ -std=c++17 -fsyntax-only -I "$SRC/include" -isystem "$BOOST/include" \
        "$SRC/test/test-base.cpp"                 # 预期：19 个 error（未打补丁时）

# 2) 复现 A：消费者只写 transitive_headers（不写组件级 requires）时找不到 boost 头
grep -n 'cpp_info.requires' "$REPO/archives/p/permlib/0.2.9/conanfile.py"

# 3) 正解验证：消费者只 include 公开头、不写 boost 路径，编译+裸环境运行
conan create "$REPO/archives/p/permlib/0.2.9" \
  -pr:h="$REPO/ci/conan/profiles/ohos-aarch64" -pr:b="$REPO/ci/conan/profiles/ohos-aarch64" \
  --build=missing -c tools.build:jobs=2
# 期望：上游 Boost.Test 13/13 可执行文件（59/59 test case）通过 + test_package 消费者
#       PERMLIB_CONSUMER_RESULT PASS（含 env -u LD_LIBRARY_PATH 的裸环境一遍）
```

## 适用面（为什么值得进图谱）

- 本仓 `package_type = "header-library"` 的配方有 **461 个**（`git grep -l 'header-library' upstream/main -- 'archives/*/*/*/conanfile.py' | wc -l`），
  其中公开头直接 include 第三方头的是同一族；`boost` 只是最常见的那一个组件化依赖。
- 「依赖包声明了 components ⇒ 包级目标 include 为空」是 Conan 2 + CMakeDeps 的一般行为，
  与具体包无关：任何 `cpp_info.requires` 写错层级的 header-only 包都会命中 A。
- B 是**版本漂移类**失败：Boost≥1.90 的隐式包含收窄会一次性打到所有 C++98/03 时代的老库
  （permlib、以及同批的 liborigin2 类"只当头文件用"的包），错误签名稳定、可被引擎直接命中。

## 关联

- 同族先例：`archives/l/liborigin2/20110117/conanfile.py`（公开头 include boost +
  `cpp_info.requires = ["boost::headers", "tree-hh::tree-hh"]`，同样是"必须写组件级"的实证）
- 相关条目：`E612`（依赖 option 与实际产物不一致导致 runenv 缺失，同属「包侧接口面」族）
