# transfuse 0.7.6 — HarmonyOS PC (OHOS aarch64) 适配笔记

- 上游：https://github.com/TinoDidriksen/transfuse ，release `v0.7.6`（2025-08-14）
- 源码：`transfuse-0.7.6.tar.bz2`，SHA256 `6ef69d8e2a2361d0add7a9fe0eb0b3af9cad3a29a7c77605e918d1d5f71aaad4`
- 目标：`aarch64-linux-ohos`，clang 15 + libc++，profile `ohos-aarch64-wsl`
- 配方版本策略：首次适配上游版本号 `0.7.6`（R37）；若后续同版本修复则用 `0.7.6.N`

## 1. 软件形态

`package_type = "application"`。上游 `src/CMakeLists.txt` 只构建一个
`transfuse` 可执行文件，并为其三个模式创建别名：

| 产物 | 说明 |
|---|---|
| `bin/transfuse` | 主程序，`extract` / `inject` / `clean` 三模式 |
| `bin/tf-extract` | `transfuse` 的别名（上游 `create_symlink`） |
| `bin/tf-inject` | 同上 |
| `bin/tf-clean` | 同上 |
| `share/man/man1/transfuse.1` | man 页（及三个别名软链） |

因此按 R38 需要软件级 `commands.json`。

## 2. 依赖解析与四类适配

上游 `CMakeLists.txt` 用四种不同机制找依赖，全部要满足：

| 依赖 | 上游查找方式 | Conan |
|---|---|---|
| libxml2 | `pkg_search_module(LIBXML2 REQUIRED libxml-2.0)` | `libxml2/2.15.3.1` |
| sqlite3 | `pkg_search_module(SQLITE3 REQUIRED sqlite3)` | `sqlite3/3.53.4` |
| libzip | `find_path(zip.h PATH_SUFFIXES libzip)` + `find_library(zip)` | `libzip/1.11.4` |
| icu | `find_package(ICU REQUIRED)` | `icu/76.1`（静态） |
| xxhash | `find_path`/`find_library`（`BUNDLED_XXHASH=OFF`） | `xxhash/0.8.4` |

W0 依赖发布检查（`conan download <pkg>/* -r=ohpcd --only-recipe`，R35）：
5 个依赖全部已发布（`icu/76.1`、`libxml2/2.15.3.1`、`libzip/1.11.4`、
`sqlite3/3.53.4`、`xxhash/0.8.4`），无需先适配依赖。

### 2.1 C++ 标准：profile 的 cppstd 会覆盖上游探测（cppstd 20）

**症状**：`src/dom.cpp:103/107: error: no member named 'contains' in
'std::map<...>' / 'std::set<...>'`（`contains` 是 C++20 特性）。

**根因**：上游会自己探测并把 `-std=c++20` 追加进 `CMAKE_CXX_FLAGS`
（`CHECK_CXX_COMPILER_FLAG` 依次试 `-std=c++20`/`c++2a`/`c++17`）。但 OHOS
profile 的 `compiler.cppstd=17` 被 `conan_toolchain.cmake` 无条件翻译成
`set(CMAKE_CXX_STANDARD 17)`，而 CMake 会把由该变量导出的 `-std=` 追加到
`CMAKE_CXX_FLAGS` **和** `CMAKE_CXX_FLAGS_RELEASE` **之后**，于是最后一个
`-std=`（=17）生效，上游探测的结果被覆盖。

实测三条路都不通：

1. `-DCMAKE_CXX_STANDARD=20` → 无效（toolchain 的 normal `set()` 屏蔽 cache 与命令行）；
2. `tc.variables["cppstd"] = 20` → 无效（Conan 2.29 的 `CppStdBlock.context()`
   只从 `self._conanfile.settings.get_safe("compiler.cppstd")` 取值，没有 conf 开关）；
3. 钩子里 `unset(CMAKE_CXX_STANDARD)` → 更糟，CMake 回退到
   `CMAKE_CXX_STANDARD_DEFAULT`，clang 15 默认 gnu++14，于是追加一个
   `-std=c++14`，依旧排在最后（实测 flags：`... -std=c++20 -O3 -DNDEBUG -fPIE -std=c++14`），
   症状从 `contains` 变成 `no member named 'filesystem' in namespace 'std'`
   （libc++ 的 `_LIBCPP_BEGIN_NAMESPACE_FILESYSTEM` 只有在 C++17 以上才是 inline 命名空间）。

**正解**：`CMAKE_PROJECT_INCLUDE` 钩子，在 `project()` 之后以 top-level 目录作用域
`set(CMAKE_CXX_STANDARD 20)`（arg_router 1.3.0 同款手法）。修正后实测链接行尾为
`-std=c++20`，无任何 `-std=c++17`/`-std=c++14` 残留。

### 2.2 pkg_search_module 丢掉 `-L`（ld.lld: unable to find library -lxml2）

**症状**：`ld.lld-15: error: unable to find library -lxml2` / `-lsqlite3`。

**根因**：CMake 的 `FindPkgConfig.cmake` 对 `LIBRARIES` 用的是 `--libs-only-l`
（模块第 636 行），`-L` 被单独放进 `<PREFIX>_LIBRARY_DIRS`。上游只把
`${LIBXML2_LIBRARIES}`/`${SQLITE3_LIBRARIES}` 交给 `target_link_libraries`，
从不加对应的 `LIBRARY_DIRS`，于是链接行上是裸 `-lxml2`。

实测 `.pc` 本身是对的（`pkg-config --libs-only-L libxml-2.0` 正常返回 `-L...`），
问题纯在 CMake 的变量拆分。

**正解**：钩子里 `link_directories()` 列出**所有 host 依赖的 libdir**（从 Conan
依赖图取，不写死路径，R49）。修正后链接行出现 5 个 `-L`。

### 2.3 FindICU 不查 data 组件（undefined symbol: icudt76_dat）

**症状**：`ld.lld-15: error: undefined symbol: icudt76_dat`，引用来自
`libicuuc.a(udata.cpp)`。

**根因**：ICU/76.1 是静态构建（`icu/76.1` 默认 `shared=False`），`libicuuc.a`
保留对 `icudt76_dat` 的未定义引用，该符号只在 `libicudata.a` 里。而
`FindICU.cmake` 只在 `ICU_FIND_COMPONENTS` 含 `data`（或 `dt`）时才去
`find_library(ICU_DATA_LIBRARY_RELEASE NAMES icudata icudt ...)`；
上游写的是 `find_package(ICU REQUIRED)`，**不带组件**，于是 data 归档从未被查找
（实测配置日志只有 `Found ICU libraries: .../libicuuc.a`）。

**正解**：钩子里用 `link_libraries()` 显式加入 `libicudata.a`（路径从 Conan 依赖图的
`icu` 包 `cpp_info.libs` 里带 `icudata` 的那一项 glob 出来）。因为
`link_libraries()` 的条目排在目标自身库之前，所以同时设
`CMAKE_LINK_INTERFACE_MULTIPLICITY 3` 让静态库重复出现，使链接顺序无关。

### 2.4 上游 xxhash 头路径拼写错误（唯一的源码补丁）

**症状**：即使依赖齐全，`src/{state,dom,transfuse}.cpp` 的
`#include <xxhash.h>` 仍找不到头文件。

**根因**（上游自身 bug，非平台问题）：`include/xxhash/CMakeLists.txt` 里

```cmake
find_path(XXHASH_INCLUDE_DIR xxhash.h)
find_library(XXHASH_LIBRARIES xxhash)
set(XXHASH_INCLUDE_DIRS ${XXHASH_INCLUDE_DIRS} PARENT_SCOPE)   # 自我赋值
```

`find_path` 填的是单数 `XXHASH_INCLUDE_DIR`，但向上传播时又读了从未被赋值的
复数 `XXHASH_INCLUDE_DIRS`，于是 `src/CMakeLists.txt` 里
`target_include_directories(transfuse PRIVATE ${XXHASH_INCLUDE_DIRS})` 展开为空。

**补丁**：`patches/0001-fix-xxhash-include-dir-parent-scope.patch`，把
`${XXHASH_INCLUDE_DIRS}` 改成 `${XXHASH_INCLUDE_DIR}`。不含任何平台宏（R8），
`git apply` 级别的单行 bugfix，对上游 Linux 构建同样有益。

## 3. 测试面

### 3.1 上游测试（ctest，14 个用例，实跑）

上游 `tests/CMakeLists.txt` 用 `add_test()` 注册 14 个用例：

- `extract-{docx,html,html-fragment,pptx,odt,txt}-{apertium,visl}` = 6 × 2 = 12
- `clean-html-{apertium,visl}` = 2

它们由 `tests/extract.sh` / `tests/clean.sh` 驱动刚构建出的 `transfuse`，
再与源码树里已提交的 `.expect` 做 `diff`。配方 `build()` 里用 `cmake.test()`
实跑（满足 CI L1c「上游测试须在 build 阶段执行」）。

**14 个 `.expect` 期望输出文件零修改、零删除**；两个驱动脚本**只改了解释器行**
（见 §3.4），测试逻辑与断言未动。

实测结果：**14/14 全部 Passed**（含依赖 libzip 的 docx/odt/pptx 6 个用例、
依赖 libxml2 的 html 用例、以及 xxhash 驱动的 `[tf-block:N-<hash>]` 标识比对）。

### 3.2 消费者测试（test_package，11 条断言，鸿蒙特有）

`test_package/test.sh` 调用**已安装进 `bin/` 的**可执行文件，断言：

1. `transfuse` 在 PATH 上且可执行
2. `transfuse` 是 ELF
3. `--version` 报出 `0.7.6`（来自构建期 `config.hpp`）
4–6. `tf-extract` / `tf-inject` / `tf-clean` 三个别名已安装
7. extract 输出含 `[tf-block:N-<hash>]` 块标记（xxhash）
8. extract 输出把 `<b>` 内联 span 还原成 `[[t:b:...]]HarmonyOS[[/]]`（ICU）
9. UTF-8 往返无损（`Ünïcödé` / `中文字符`）
10. 与 `data/test-ohos.expect` **逐字节** diff 一致
11. `clean` 模式能回注出含原文的文档

因为全部断言都经由 `bin/` 里的真实二进制，CI L1e 把 `bin/` 移走后本测试必然
失败 —— 这正是「测试真依赖被测包」的判据。

## 3.3 golden 文件不能含 NUL 字节（CI worker 的 PR diff 应用失败）

transfuse 用 NUL 字节作块分隔符，所以它的输出（含上游 `.expect`）里带 NUL。
上游 `.expect` 只存在于源码 tarball 里，不进 git，因此本仓库没有暴露这个问题；
但本包需要把一份期望输出作为 **golden 文件提交进 git**。

第一次 PR（#14148，build #66179）就在这里红了，**不是**网络问题（机器人初判为
「网络问题/源码下载超时」是误判）：

```
error: missing binary patch data for 'archives/t/transfuse/0.7.6/test_package/data/test-ohos.expect'
error: binary patch does not apply to '.../test-ohos.expect'
[ERROR] PR 14148 diff 无法应用——PR 与 main 分支存在冲突
```

CI 的 `checkout-pr` 步骤是下载 PR diff 再 `git apply`。含 NUL 的文件被 Git 判为
二进制，diff 变成 `GIT binary patch`，而 worker 侧拿到的那份 diff 缺少二进制
载荷，`git apply` / `git apply --3way` / `patch -p1` 三条兜底路径全部失败
（worker 的 `patch` 还不认 `-fuzz=3`），于是整个构建在 checkout 阶段就挂了。

**修法**：golden 文件入库前 `tr -d '\000'` 去掉 NUL，`test.sh` 对实际输出做
**同样的**归一化后再比对：

```bash
grep -aEv '^\[transfuse:' out.tmp | grep -aEv '^<STREAMCMD:TRANSFUSE:' \
  | tr -d '\000' > out.txt
diff -u data/test-ohos.expect out.txt
```

断言强度不变：被去掉的只是块分隔符，`[tf-block:N-<hash>]` 标识（xxhash）、
`[[t:b:...]]` 内联标记（ICU）与 UTF-8 正文全部逐字节保留。修复后
`git diff --numstat` 从 `-  -`（二进制）变为 `17 0`（文本）。

**推广**：任何需要把「工具输出」当期望文件提交进本仓库的适配，都要先确认该输出
不含 NUL；含 NUL 就按同样方式归一化，或改用结构化断言（只 grep 关键标记）。

### 3.4 ctest 驱动脚本的解释器行（第二个源码补丁）

**症状**（CI build #66190，真机 worker `OpenHarmonyPCDeveloper-CI-033`）：

```
Start  7: clean-html-apertium
Process not started
 /storage/.../conan2/p/b/trans632c69c06cbea/b/tests/clean.sh
[no such file or directory]
14/14 Test #14: clean-html-visl ... ***Not Run   0.00 sec
0% tests passed, 14 tests failed out of 14   （全部 BAD_COMMAND）
```

注意是 `Not Run` / `BAD_COMMAND` 而不是 `Failed`，且脚本路径本身是对的 ——
说明不是断言不通过，而是 **CTest 根本没把进程拉起来**。

**根因**：`tests/CMakeLists.txt` 把两个脚本**路径直接**注册成 `add_test()` 的
COMMAND，CTest 于是按 shebang `execve()` 它们。而两个脚本首行是 `#!/bin/bash`，
鸿蒙上 bash 不在 `/bin/bash`（它在 `/data/service/hnp/bin/bash`，CI profile 靠
`PATH=+(path)/data/service/hnp/bin` 把它找出来）。解释器不存在 ⇒ `execve` 返回
ENOENT ⇒ 14 个用例全部「Process not started」。

**补丁**：`patches/0002-portable-interpreter-shebang.patch`，把两行
`#!/bin/bash` 改成 `#!/usr/bin/env bash`，让 bash 走 PATH 解析，从而用到 CI
profile 提供的 HNP bash。只改解释器行，**不动任何测试逻辑、不动任何 `.expect`**。

**先例**：`archives/p/pax-utils/1.3.10`（`0001-use-portable-interpreter-shebangs.patch`，
10 个脚本同改法）、`archives/y/yacas/1.9.1`（补丁 0001，同改法，改完 82/82 全过）。
知识库 `E037`（shebang-fix）与 `DRAFT-date-3.0.3-ohos-bash-shebang`（CTest 侧
BAD_COMMAND）即此机制；`/usr/bin/env` 在真机是 toybox 软链，实测可用。

## 4. 签名

产物含可执行文件，鸿蒙 PC XPM 要求签名。签名器
（`binary-sign-tool`）只存在于 CI worker 的 HNP 镜像
（`/data/service/hnp/bin`），交叉编译工作区没有，因此 `_sign_binaries()`
是 best-effort：签名器在就签，不在就跳过，不让本地 `conan create` 因此失败。
签名时跳过软链（只签真实 ELF），先 `llvm-objcopy --remove-section .codesign`
再 `binary-sign-tool sign -selfSign 1`。

## 5. 已知限制 / 风险

### 5.1 `libzip` 的 `arc4random` 与本地运行时

`libzip/1.11.4`（制品仓发布的共享库）有未定义符号
`arc4random` / `arc4random_buf`（`readelf -d` 显示 `NEEDED libc.so`）。

- **OHOS 侧有这两个符号**：构建 sysroot 的 OHOS libc 导出了它们
  （`nm -D <sysroot>/usr/lib/aarch64-linux-ohos/libc.so` 同时列出
  `arc4random`、`arc4random_buf`、`arc4random_uniform`）。
  真机 / CI worker 用的就是这套 libc，所以链接 libzip 的产物在 CI 上可正常运行。
- **本机 WSL 容器侧没有**：`/opt/ohos-guest/lib/libc.so` 是 stock musl
  （`strings` 显示 `musl libc (aarch64)`，1648 个动态符号，只有
  `getrandom`/`random`/`srandom`，没有 `arc4random`），早于 musl 引入
  `arc4random` 的版本。直接跑本机构建出的 `transfuse` 会得到
  `Error relocating .../libzip.so.5: arc4random: symbol not found`（exit 127）。

结论：**这是本机运行时镜像的版本问题，不是 transfuse 的适配缺陷**。
验证方式：用 `LD_PRELOAD` 让加载器换用 OHOS libc 后，同一个二进制的 14 个
上游用例全部通过（见 §3.1）。

**CI 侧佐证**：真机 worker（build #66190）的 compile + link **全部成功**，
最终只挂在 ctest 的「进程拉不起来」（§3.4 的 shebang 问题），从未出现
`undefined symbol: arc4random_buf`。真机能链接通过，说明 CI worker 的 OHOS libc
确实提供 `arc4random`/`arc4random_buf` —— 与本节开头对 sysroot 的实测一致。

因此本包**未**对 `libzip` 做任何改写，也**未**
在配方里塞任何运行期 shim —— 那会把容器问题掩盖成产品行为。

### 5.2 `-flto` 与 `CMAKE_AR=gcc-ar`

上游在 `-flto` 被支持时会把 `CMAKE_AR` 硬编码成 `gcc-ar`。本包
`BUNDLED_XXHASH=OFF` 时不构建任何静态归档，`CMAKE_AR` 不会被用到，
因此该分支对本包是 no-op；可执行文件由 clang 驱动 + lld 链接。

## 6. 用到的知识库条目

- `DRAFT-rdate-1.11-musl-builtin-arc4random-vestigial-bsd-header` — 确认
  「musl 内建 arc4random」这条结论**只在该条的设备环境成立**，不能迁移到本
  交叉编译容器；据此判定 §5.1 是环境问题而非配方问题
- E176 — ICU stubdata 动态库在鸿蒙加载器上受限；本包因此沿用 `icu/76.1`
  默认的静态构建（`--with-data-packaging=static`），规避该问题
- E355 — conan 制品 `.pc` 的 prefix 处理；本包实测 `.pc` 的 `prefix`/`libdir`
  正确，2.2 的问题是 CMake `pkg_search_module` 的变量拆分，不是 `.pc` 本身
- `archives/a/arg_router/1.3.0` — `CMAKE_PROJECT_INCLUDE` 钩子 + cppstd 覆盖
  的既有正解与逐字理由（2.1 照此办理）
- `archives/l/lib3mf/1.8.1`、`archives/m/minizip-ng/4.2.2` — `_sign_binaries()`
  只签真实 ELF、跳过软链的签名写法
- `archives/2/2048.c/1.0.3` — application 类包 `test_package` 用
  `${CONFIG_SHELL}` 跑测试脚本的写法（OHOS mksh 不能 exec ELF）