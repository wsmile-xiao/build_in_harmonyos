# mINI 0.9.20 适配笔记（header-only C++ INI 库）

## 0. 交付摘要

| 项 | 值 |
|---|---|
| 上游 | metayeti/mINI（host 不带 scheme：`github.com/metayeti/mINI`） |
| 版本 | 0.9.20（tag `0.9.20`） |
| 类型 | **header-only**（唯一交付头文件 `include/mini/ini.h`，781 行，C++17，零依赖） |
| conan ref | `mini/0.9.20`，`package_type = "header-library"` |
| 消费契约 | CMake：`find_package(mINI CONFIG REQUIRED)` → `mINI::mINI`；pkg-config：`mini` |
| 上游测试 | tests/ 下 **9 个 test*.cpp → 9 个测试可执行目标**，**54 个 lest CASE 用例**；`ctest --output-on-failure -V -j1` 实测 **9/9 程序、54/54 用例通过** |
| 消费者用例 | `test_package/test_mini_consumer.cpp`：**64 项**显式判据（真值比对） |
| 交付形态自检 | `test_package/test_mini_shape.py`：**M1–M13（13 项）** |

## 1. 源码获取（source）

```
url    : github.com/metayeti/mINI/archive/refs/tags/0.9.20.tar.gz
sha256 : 966c023f04d31f88944fba9c7e6b1c99ad802f3608d2ce8efc645de0fbcaa8c0
tar tf | wc -l : 32
```
- 下载后双校验：`sha256sum` 与 `tar tzf | wc -l`（32 条）均与上面一致（同一份字节也可从
  codeload 端点取到，两个端点实测 sha256 相同）。
- URL 以 `.tar.gz` 结尾，conan 的 `get()` 能自动判定归档格式（codeload 端点结尾是版本号，
  `get()` 会误判为 zip，故采用 tag 归档端点）。
- 无补丁：上游源码在 OHOS aarch64 上无需任何改动（`patches/` 目录不存在）。

## 2. 打包（package）

- `src/mini/ini.h` → `include/mini/ini.h`（sha256 与上游一致：
  `35857afbb7d42b742d58c1cad5ab301fdb89c2367da01cb6e4609d6d6cf76b5e`）。
- `LICENSE` → `licenses/LICENSE`（sha256：
  `e8164252c3414652447418b5e9b40a31c3ba7cd1a21e235c23a3192c87cf7649`）。
- 不交付 `bin/`、不交付 `lib/`（无 `.so`/`.a`），故 **OHOS「.so 必须逐个签名」硬坑（硬坑 D）
  对本包不适用**；包内无任何 ELF。
- `package_id()` 清空（header-only：settings 组合不影响包内容）。

## 3. 上游测试真跑（build() 集成）

上游 `tests/` 自带测试套件：lest 单头框架（`tests/lest/lest.hpp`，随 tarball 一起发布）
+ 9 个 `test*.cpp`，上游 `tests/CMakeLists.txt` 为每个 `test*.cpp` `add_executable`，
`tests/runalltest.sh` 逐个 `./*.test -p` 跑。

**适配做法（不改上游源码）**：`build()` 里生成一个极小的 CTest harness（`ctest_harness/CMakeLists.txt`），
`add_subdirectory(<source>/tests)` 复用上游 9 个可执行目标，再 `add_test()` 注册（带上游 `run.sh`
用的 `-p`），然后：

```
ctest --output-on-failure -V -j1
```

`-V` 让日志展开每个测试的 lest 输出（逐用例可见），任一用例失败即 `ctest` 非零退出
⇒ `conan create` 失败。该命令与 `test_package/MANIFEST.yml` 的 `upstream_check_command`
**逐字一致**。

**口径**：9 个测试程序 / 54 个 `CASE` 用例 = 6(testbom) + 1(testcasesens) + 1(testcopy)
+ 9(testgenerate) + 2(testhuge) + 5(testpath) + 13(testread) + 2(testutf8) + 15(testwrite)。

**实测结果（本地 x86_64 / gcc 15 / C++17）**：
```
testbom        All 6 selected tests passed.
testcasesens   All 1 selected test passed.
testcopy       All 1 selected test passed.
testgenerate   All 9 selected tests passed.
testhuge       All 2 selected tests passed.
testpath       All 5 selected tests passed.
testread       All 13 selected tests passed.
testutf8       All 2 selected tests passed.
testwrite      All 15 selected tests passed.
=> 9/9 程序、54/54 用例 = 100%
```

## 4. 消费者用例（test_package）

`test_package/CMakeLists.txt` 用 `find_package(mINI CONFIG REQUIRED)` +
`target_link_libraries(mini_consumer PRIVATE mINI::mINI)` 真编译真链接
（即 CMake 消费契约的机器验证），`test()` 里直接运行。

`test_mini_consumer.cpp`（**64 项显式判据**，全部为真值比对，无「解析成功即通过」式断言）：

1. **真实 INI 文本**（含 UTF-8 BOM、CRLF 与 LF 混用、`;` 行注释、`#` 行、段行行内注释、
   键值行内的 `;`（属于值）、双引号（不是语法）、空行、重复键、UTF-8 段名/键名/值、
   数值与布尔字符串、空键/空值、`\=` 转义键）→ 逐键逐值比对：
   - BOM 被剥离；段总数 3；首个 `[section]` 之前的键被丢弃；
   - `Port=8080` 与 `port = 9090` 重复键 ⇒ **后写胜出**（值 `9090`），且**位置保持首次出现处**；
   - 键名/段名大小写不敏感（`ini["SERVER"]["HOST"]` 命中）；值**不做**大小写折叠
     （`enabled_upper = TRUE` 原样保留，消费者需自行归一化）；
   - 段行尾部 `; 注释` 被剥离；键值行尾的 `;` **不**剥离（属值）；
   - `quoted = "hello world"` ⇒ 值含引号（引号不是 INI 语法）；
   - 键 `esc\=key` 还原为 `esc=key`；值里允许 `=`（`eqvalue = a=b=c`）；
   - 11 个键的顺序 == 首次出现顺序。
2. **类型转换**：`std::stoi`/`std::stod`/`std::stof` 对 `9090` / `0.125` / `30` 等做**具体数值**比对。
3. **错误/边界路径**（期望值逐字取自上游 `tests/testread.cpp`，外部可核对）：
   - 畸形段名 `[[name1]` / `[name2]]` / `[[name3]]` ⇒ 段名 `[name1` / `name2]` / `[name3]`
     （= 上游 Malformed case 1 的断言）；
   - 畸形键 `key\==value` / `\===` / `a\= \===b` / `   c\= \=  = =d ` ⇒ 键 `key=` / `=` /
     `a= =` / `c= =`（= 上游 Malformed case 2 的断言）；
   - `GARBAGE`（无 `=`）行整行忽略、段行尾部注释被剥离后仍归入正确段；
   - 读取不存在的文件 ⇒ `read()` 返回 **false**（不抛异常）；空文件 ⇒ `true` 且 0 段。
4. **`generate()` 逐字节比对**：紧凑与 `pretty=true` 两种输出的**完整文件字节**与手写期望串
   逐字节相同（含值 trim、键里 `=` 写成 `\=`、无尾随换行）。
5. **`write()` 惰性写**：注释行保留、已存在键就地更新、新键追加 —— 结果逐字节比对。

## 5. 交付形态自检 M1–M13（test_package/test_mini_shape.py）

| 编号 | 检查 |
|---|---|
| M1 | `include/mini/ini.h` 存在且 sha256 == 上游 `src/mini/ini.h`（外部真值） |
| M2 | `include/` 交付清单恰为 `['mini/ini.h']`（无多余条目） |
| M3 | 无 `bin/`、无 `.so/.a/.o`、无带可执行位的交付文件（header-only 无二进制） |
| M4 | `licenses/LICENSE` sha256 == 上游 `LICENSE`（外部真值） |
| M5 | 包内无隐藏文件 / `__pycache__` / `*.pyc` / `conanbuild.sh` 等构建残留（JC5 口径） |
| M6 | 交付头文件不含构建/缓存绝对路径字面量（源码树泄漏） |
| M7 | CMake 契约：`mINI-config.cmake` 存在且定义 `mINI::mINI` |
| M8 | CMake 契约的 `INTERFACE_INCLUDE_DIRECTORIES` 指向本包 `include/` |
| M9 | pkg-config 契约：`mini.pc` 的 `Name/Version/prefix` 正确且 `Cflags` 用 `${prefix}`（可重定位） |
| M10 | 真调用 `pkg-config --modversion/--cflags mini`（自设 `PKG_CONFIG_PATH`）复核可用性 |
| M11 | 把 `include/` 搬迁到临时目录后仍能编译**并运行**真实 API（可重定位 + 取值正确） |
| M12 | 同一 TU 连续 `#include "mini/ini.h"` 两次可编译运行（include guard） |
| M13 | 版本三处一致：被测 conan ref / `mini.pc` / `mINI-config-version.cmake` |

## 6. 平台适配说明（OHOS）

- **无编译产物**：头部库 ⇒ 不触发 OHOS「.so 未签名拒载」（硬坑 D）、不触发「包目录 ELF 不可
  execve」（硬坑 E）、无需 SONAME/RPATH 处理（硬坑 F）。
- **无依赖**：零 `requires`（上游自身零依赖），故不涉及跨 DSO `dynamic_cast`（硬坑 A）与
  依赖重签（cairomm 那类）。
- 上游测试用相对文件名在 **ctest 的工作目录**（= conan build 目录）读写自己的 `.ini` 夹具，
  不写 `$HOME`、不碰 `/tmp`（OHOS 上 `/tmp` 只读）——`testpath.cpp` 用
  `std::filesystem::path` 传相对路径（含 u16/u32 路径）。
- `tests/CMakeLists.txt` 里 `cmake_minimum_required(VERSION 3.5)`，配方通过
  `CMAKE_POLICY_VERSION_MINIMUM=3.5` 显式放行（仓库先例：`dbg-macro/0.5.1`、`autodiff/0.4.0`）。
- `can_run(self)` 为假（交叉 profile）时跳过上游测试并**显式打印告警**（不静默跳过）；
  CI 的 `ohos-aarch64` profile 为原生构建，会真实执行。

## 7. 复现命令

```bash
export PATH=/home/silhouette/conanenv/bin:$PATH
export CONAN_HOME=/home/silhouette/.conan2-ohos
conan create archives/m/mini/0.9.20 -pr:h=default -pr:b=default --build=missing
```

## 8. 已知风险

- CI 侧 worker 偶发 OOM/桥接故障（与配方无关）；若日志停在 `worker_prep`/`git-clone`，
  补发一次 `/rebuild` 即可。
- 上游无 `#` 注释语义：`#` 行仅因「不含 `=`」被忽略；`#k=v` 会被当成键 `#k`。这是上游
  既有行为（本包不做任何改动），消费者用例已把该边界行为显式固定下来。
