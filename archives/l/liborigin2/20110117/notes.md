# liborigin2 20110117 适配笔记

## 上游身份

| 项 | 值 | 依据 |
|----|----|------|
| 项目 | liborigin2 — 读取 OriginLab Origin 4.1 – 8.5.1 `.opj` 工程文件的 C++ 库 | 源码 `FORMAT` / 归档主页正文（Wayback） |
| 作者 | Ion Vasilief（QtiPlot 项目） | 归档主页 “Author: Ion Vasilief”；`copying` |
| 版本 | 20110117（日期式版本号，来自 `OriginFile.h` 的 `LIBORIGIN_VERSION 0x00110117` / `LIBORIGIN_VERSION_STRING "2011-01-17"`） | 源码实测 |
| 语言 | **纯 C++**，无 `.c` 文件 | 顶层 16 个 `.cpp/.h` + `endianfstream.hh` + `logging.hpp` |
| 许可 | 声明 **GPL-3.0-or-later**（见下“许可歧义”） | `copying` 首行 “GNU GENERAL PUBLIC LICENSE / Version 3, 29 June 2007” |
| 构建系统 | **只有 qmake**（`liborigin2.pro`） | `find` 全树无 Makefile/CMakeLists/configure/meson |

### 上游已不可用，源码来源必须说明

- 当年权威主页 `soft.proindependent.com/liborigin2/` 已下线（Debian 只能用
  Wayback 快照当 Homepage）；下载托管 `berlios.de` 已关闭；
  `sourceforge.net/projects/liborigin2/` 返回 404。
- SourceForge 现存的同名项目是 **liborigin**（后继重写，3.0.x），其
  `liborigin2/` 目录只有 2009/2010 两版，**没有 20110117**。
- 因此本配方取 **Debian 源码池的 orig tarball**，sha256 与
  `liborigin2_20110117-7.dsc` 的 `Checksums-Sha256` 逐字一致，是当前唯一
  可复现、可校验的 20110117 来源。

### 许可歧义（如实记录）

`copying` 写的是 GPL-3，但多个源文件头（如 `OriginFile.h`/`OriginFile.cpp`）写的是
“GNU General Public License … either version 2 of the License, or (at your option)
any later version”，归档主页又写 “GPL License, Version 3 and Commercial”。
Debian 的 `debian/copyright` 判定为 `GPL-3+`。本配方按 **GPL-3.0-or-later** 申报，
与 Debian 一致；`files/logging.hpp`（来自 Boost）与 tree.hh（GPL-2+）是各自独立许可
的第三方头文件，不改变主库许可。

## 依赖分析

| 类别 | 内容 | 结论 |
|------|------|------|
| build_requires | 无 | 配方自带 CMake 构建描述，不需要 qmake |
| host_requires | `boost/1.90.0.4.1` | **只用头文件**：`lexical_cast` / `format` / `date_time` / `tuple` / `shared_ptr` / `lambda` / `bind` / `algorithm/string` / `variant`；无 `boost/filesystem`、无 `boost/system` |
| host_requires | `tree-hh/3.18` | 上游 20110117 tarball **缺 `tree.hh`**，而 `OriginParser.h:33` 直接 include 它 |
| system | libc / libstdc++ / libm（OHOS 上是 libc++_shared + libc） | 无其它系统库 |
| optional | 无 | — |
| test-only | 无（上游无测试） | — |
| Qt | **不需要** | 不能凭 “qmake 工程” 判断：`.pro` 里 `QT -= gui core`，源码里 `Q[A-Z]` 只命中一处注释，Debian 也显式去掉了 Qt 依赖 |

### boost 只作头文件使用的三重证据

1. Debian build log 的链接行有 `-lboost_date_time`，但产出 `.so` 的
   `readelf -d` NEEDED 只有 `libstdc++/libm/libgcc_s/libc`（`--as-needed` 丢弃）；
2. 本机实测：`g++ -shared obj/*.o`（**不传任何 `-lboost*`**）链接成功，
   `nm -D --undefined-only | grep -i boost` 为空；
3. Debian 自己的 `01_makefile.diff` 就把 `-lboost_thread` 注释掉了。

### boost 版本下限是 OHOS 决定的

`boost/core/detail/sp_thread_sleep.hpp` 里 `pthread_setcancelstate`（OHOS musl 没有）：

- **1.84 / 1.85**：该文件带 `!defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)` 守卫，
  必须由 boost 包通过 `cpp_info.defines` 把宏传给消费者（本仓库 1.84.0 配方正是
  这么做的）；
- **1.90 起**：上游直接加了 `!defined(__OHOS__)` 守卫，无需任何宏。

本配方固定 `boost/1.90.0.4.1`（ohpcd 已发布），避免依赖宏传递路径。
**这是本地实测出来的**：先用 1.84 头文件交叉编译报 16 处
`use of undeclared identifier 'pthread_setcancelstate'`，换 1.90 头文件后消失。

## 构建

上游只有 qmake 工程。因为库本身零 Qt 依赖，为了一个构建工具把整套 Qt5 base
拉成构建依赖不划算，配方改为注入 `files/CMakeLists.txt`：

- 源文件清单与 `.pro` 的 `SOURCES` **逐条一致**（9 个 `.cpp`）；
- `TARGET = origin2` → `liborigin2.so.1.0.0`，SONAME `liborigin2.so.1`
  （与 Debian 打包的 ABI 一致；qmake 对未设 `VERSION` 的 lib 工程默认 1.0.0）；
- 不引入任何新的编译宏或构建逻辑；源码侧改动全部在 `patches/` 里，可单独审阅。

`qmake` 工程、`.pro` 与其它上游文件保持原样（配方不修改也不使用它们）。

## 上游测试（精确清点 = 0，含证据）

上游 20110117 源码树**没有任何测试或示例**，逐条核验（在解包目录下执行）：

```
$ find . -iname '*test*' -o -iname '*example*' -o -iname '*demo*'   → 无输出
$ grep -rn "int main" .                                             → 无命中
$ grep -rn "add_test\|enable_testing" .                             → 无命中
$ grep -n "test\|check" liborigin2.pro   → 只匹配 CONFIG += warn_on release thread
```

同项目 SourceForge 的 20101029 tarball 同样没有测试。因此 `build()` 中
**无从执行上游测试**，上游测试数如实记为 **0**（不是省略、不是为省事填 0），
并在 `test_package/MANIFEST.yml` 中列出上述证据命令。

## 源码补丁（6 个，全部为最小改动）

| 补丁 | 文件 | 问题 | 触发条件 |
|------|------|------|----------|
| 0001 | `OriginFile.h` | `auto_ptr` 已从 C++17 移除 | clang 15 / libc++ 硬错误 |
| 0002 | `logging.hpp` | `*s == std::cout` 是流对象比较，应为指针比较 | 编译期错误 |
| 0003 | `OriginObj.h` | 用 `std::find_if` 但未含 `<algorithm>` | 新标准库不再间接引入 |
| 0004 | `Origin750Parser.h` | `boost::posix_time::seconds(double)` | Boost ≥ 1.67 只接受整型 |
| 0005 | 4 个 `OriginXXXParser.cpp` | `h & 0x60 == 0x60` 实为 `h & (0x60 == 0x60)`，恒为 `h & 1` | 语义 bug，与平台无关 |
| 0006 | `endianfstream.hh`、`OriginDefaultParser.cpp` | `register` 存储类 | C++17 已删除；clang 下是硬错误（gcc 只是告警） |

0001–0004 与 Debian 打包补丁（10/20/30/40）解决的是同一批问题，本配方按自己的
最小范围重写（例如 30 号只取 `<algorithm>` 那一块，不引入 Debian 针对 qmake 的改动）；
0005 采用了 Debian 同名修复；**0006 是本配方新增的**（Debian 用 gcc 构建，`register`
只是告警，clang 15 下是错误，且该头文件是**公共**的 `endianfstream.hh`，不修则下游
消费者用 C++17 也无法编译）。

### 0004 的修正（PR 检视反馈，已改）

初版 0004 照搬了 Debian 补丁的写法
`static_cast<long>(jdt-(int)jdt)*86400`，这是**错的**：C++ 运算符优先级让它等价于
`(static_cast<long>(jdt-(int)jdt)) * 86400`，先把 [0,1) 的小数截断成 0，再乘 86400
仍为 0 —— `seconds()` 恒为 0，任何带小数部分的儒略日都丢掉时间分量（日期不受影响）。
旧版 Boost 的 `seconds(double)` 是先算乘积再隐式转整型，能得到真实秒数，所以这是
本补丁引入的**功能回归**。

现改为把整个乘积放进 cast：

```cpp
boost::posix_time::seconds(static_cast<long>((jdt-(int)jdt)*86400))
```

（注：Debian 侧的同一处补丁仍是旧写法，有同样的问题；本配方不复用其写法。）

诚实说明：`doubleToPosixTime()` 是 `Origin750Parser` 的 `protected` 成员，不在公共
API 上，test_package 无法直接覆盖它；这条修正是**静态审阅**得出并由 PR 检视指出的，
不是运行期测试发现的。

## 本机验证边界（WSL，**不是** Harmony 结论）

### 1) 原生 (Ubuntu x86_64 + gcc 15 + boost 1.84 头 + tree-hh 3.18)

| 步骤 | 结果 |
|------|------|
| 9/9 源文件编译（仅打 6 个补丁后） | 通过 |
| `g++ -shared` 链接，不传任何 `-lboost*` | 通过，SONAME `liborigin2.so.1`，NEEDED 仅 libstdc++/libm/libgcc_s/libc |
| 消费者测试程序（10 条断言） | 全部 PASS |

**记为 `WSL_NATIVE_PASS`（Ubuntu x86_64）**，不代表 OHOS 通过。

### 2) OHOS aarch64 交叉编译（WSL 内的 OHOS SDK clang，不接触 Harmony PC）

```
aarch64-unknown-linux-ohos-clang++ 15.0.4  -std=c++17 -fPIC
  -I<src> -I<boost 1.90 headers> -I<tree-hh 3.18 headers>
```

- 9/9 对象文件编译成功；
- 链接产出 `ELF 64-bit LSB shared object, ARM aarch64`，SONAME `liborigin2.so.1`，
  NEEDED = `libc++_shared.so`, `libc.so` —— **无 boost、无 Qt**。

**只能记为 `WSL_CROSS_COMPILE_ONLY`**：只证明能编译链接，二进制未在 OHOS 上
执行过（aarch64 OHOS 程序无法在 WSL x86_64 上运行）。真正的 `conan create`
与消费者测试必须在 Harmony PC 上完成，本轮未执行。

## 依赖传播：为什么 test_package 自己也要声明 boost / tree-hh

liborigin2 的**公共头**直接 include 第三方头：
`OriginObj.h → boost/variant.hpp`、`OriginParser.h → tree.hh`。按 Conan 的语义，
主配方在 `package_info()` 里用
`self.cpp_info.requires = ["boost::headers", "tree-hh::tree-hh"]` 声明了这种接口依赖。

但在本环境（Conan 2.29.1）实测：**消费者图里，boost 的 include 目录不会被带出来**。
本地复现与证据：

| 场景 | CMakeDeps 生成的 `boost_INCLUDE_DIRS_RELEASE` |
|------|---------------------------------------------|
| `conan install --requires=boost/1.90.0.4.1`（boost 是**直接**依赖） | `${boost_PACKAGE_FOLDER_RELEASE}/include`（正常） |
| `conan install --requires=liborigin2/20110117`（boost 是**传递**依赖） | **空**，于是消费者 `#include "boost/variant.hpp"` 直接找不到头文件 |

同一份 boost 配方版本（`488e123eb5ef34a58565da809bd47a1b`）、同一个包
（`boosta16b8cb52a1e1`，OHOS/armv8），差别只在图的层级；`boost::boost`、
`boost::headers`、以及完全不写 `cpp_info.requires` 三种写法实测结果一致（都为空）。
作为对照，仓库里已发布的 header-only 包 `mdds/3.2.1` 走的是 **旧版 boost 配方 revision**
（其 CMakeDeps 数据是包级组件模型），该场景下 include 是正常的 —— 也就是说这不是
"liborigin2 配方写错"，而是当前 boost revision 在传递位置上的行为。

处理方式（都在本包范围内，不改公共 recipe）：

1. 主配方的 `cpp_info.requires` 保留正确声明（对能正常传播的 Conan 版本/图仍然生效）；
2. `test_package` 显式声明 `boost/1.90.0.4.1` 与 `tree-hh/3.18`，并在 CMakeLists 里
   `find_package` 后显式链接 `Boost::headers` / `tree-hh::tree-hh`。这既是让测试能编译，
   也是把"消费者该怎么用"固化成可执行的示例；
3. README 里明确写出这条消费要求。

**待 Harmony 阶段复核**：Harmony PC 上的 Conan 版本与远程包若行为一致，则消费者同样
需要显式声明 boost/tree-hh；若那边传播正常，本包的 `cpp_info.requires` 会自动生效，
test_package 的显式声明也无副作用（重复声明同一依赖不冲突）。

## OHOS 产物：无 SONAME，必须补

OHOS profile 下 CMake **不会生成版本化实体与符号链接**，只产出 `liborigin2.so`，
且该 `.so` **没有 DT_SONAME**（本机交叉构建实测：`readelf -d` 只有 NEEDED，
没有 SONAME；这点与本地 Linux 原生构建不同，后者正常产出
`liborigin2.so.1.0.0` + `.so.1` + `.so`，SONAME 为 `liborigin2.so.1`）。

缺 SONAME 的后果**不在本包而在下游**：CMake 会按完整路径链接，把构建机 conan cache
的绝对路径写进下游的 DT_NEEDED，换机器即无法加载 —— 本仓库已有三个制品因此损坏
（fontconfig / poppler / tbb）。因此 `package()` 在 OHOS + shared 时对产物做两步处理：

1. `patchelf --set-soname liborigin2.so`（产物本来就是无版本名实体，SONAME 取文件名
   本身即与上游本意一致）；
2. `llvm-objcopy --remove-section .codesign` → `binary-sign-tool -selfSign 1`
   （改 ELF 会破坏链接器自签，顺序不能颠倒；未签名的 ELF 在鸿蒙 PC 上会被 XPM
   拒绝加载，报 EACCES / rc 126）。

产物定位用 `glob("lib/liborigin2.so*")` 而不是硬编码 `.so.1.0.0`，避免真机上
因文件名与 Linux 不同而找不到文件。

## 留给 Harmony 阶段的已知风险

1. **`OriginFile` 构造会写日志文件**：`logging::sink s(new ofstream("./opjfile.log"), 1)`
   会在**当前工作目录**创建 `opjfile.log`。test_package 的 `test()` 用
   `cwd=self.build_folder` 运行，可写；若换成只读目录会静默失败（不致命）。
2. 配方默认为 **shared**；静态构建同样支持（`-o shared=False`），已在本机原生
   模式下验证，但 OHOS 静态尚未验证。
3. OHOS shared 产物在 `package()` 里调用 `llvm-objcopy --remove-section .codesign`
   + `binary-sign-tool` 自签（未签名的 ELF 会被 XPM 拒绝加载）。该步骤只在
   `os=OHOS 且 shared` 时触发，本机原生构建不会走到。
4. 上游无测试，本包唯一的运行期验证来自 test_package（10 条断言）。这意味着
   上游测试通过率无法申报——**在 PR 模板里必须如实写“上游测试 0”**，不得
   用消费者测试冒充上游测试。
5. 本机交叉验证时，`patchelf` 与 `binary-sign-tool` 都不在 WSL 上：前者用桩脚本
   占位（只验证调用顺序与产物定位，**没有真正写 SONAME**），后者同理。**SONAME
   补写与自签必须在 Harmony PC 上复核**（`readelf -d` 应能看到
   `SONAME liborigin2.so`，且文件带 `.codesign` 段）。

## 可复用知识候选

- **“上游 tarball 不完整”**：liborigin2 20110117 的源码引用了包内不存在的
  `tree.hh`，原样无法编译。遇到“缺头文件”时先查本仓库是否已有对应 Conan 包
  （本例 `tree-hh/3.18` 已存在），比 vendoring 或下拉旧发行包更干净。
- **boost 在 OHOS 上有版本下限**：`pthread_setcancelstate` 缺失使得 1.84/1.85
  必须靠 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 宏，1.90+ 由上游 `__OHOS__` 守卫
  自动跳过。选 pin 版本时这是硬约束，不是偏好。
- **`register` 是 gcc/clang 的分界**：C++17 下 gcc 只告警、clang 报错，所以
  Debian（gcc）不需要打的补丁，在 OHOS（clang 15/libc++）上是必需补丁。
