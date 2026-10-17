# lrcalc 1.2 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 2014 年生成的 configure）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18）
- 状态: built

## 上游测试清点（R51）
| 项 | 值 |
| --- | --- |
| 上游测试入口 | `make check`（`Makefile.am` 中 `TESTS = testsuite`） |
| 注册测试数 | 1（`testsuite` 脚本） |
| 断言/检查数 | 8（lrcoef 1 + skew 2 + mult 3 + coprod 1 + schubmult 1） |
| 运行环境 | HarmonyOS PC（aarch64 设备）与 CI clean worker（同一 conan create 流程） |
| 修改上游测试 | 无 |
| 实测结果 | 8/8 通过（`PASS: testsuite`） |

## 编译步骤
1. `conan create archives/l/lrcalc/1.2`（profile 与 CI 相同）
2. build() 内部：
   - `apply_conandata_patches` 应用 0001-config.guess / 0002-config.sub / 0003-configure 三个补丁
   - `CONFIG_SHELL=/bin/sh SHELL=/bin/sh ./configure --prefix=<package_folder> --enable-shared --disable-static`
   - `make -j1`
   - `make -j1 check`（上游 testsuite）
   - `make -j1 install`（直接安装到 package_folder）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | native 构建（build==host）时 conan 不生成 `--host/--build` 三元组，configure 转而运行 2012 年的 config.guess，而它不认识 `uname -s=HarmonyOS` | 补丁 0001：config.guess 在 case 顶部增加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`（E007 既定方案，不用三元组绕过） |
| 2 | `config.sub: Invalid configuration 'linux-ohos': system 'ohos' not recognized` | 上游 config.sub 不认识 ohos OS token | 补丁 0002：maybe_os 列表加入 `linux-ohos*`，OS 接受列表加入 `-ohos*` 与 `-linux-ohos*`（POSIX 修复，无平台宏） |
| 3 | `config.status[...]: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 新建目录自动 setgid，`umask 077` 目录连属主也不可写（E011/E129） | 补丁 0003：configure 临时目录 `umask 077` → `022`（两处回退路径都改） |
| 4 | `libtool: line 353: syntax error near unexpected token '}'`、config.status 报 `print: command not found` | profile buildenv 把 harmonybrew bash 注入为 SHELL，configure 将其写入 Makefile；该 bash 在 HMDFS 上不稳（E386 同族），libtool/config.status 随之崩坏 | configure 命令行强制 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`，Makefile 内置 `SHELL=/bin/sh`（tslib 先例） |
| 5 | `make: jobserver mkfifo: ... Operation not permitted` | HMDFS 不允许 make -j 的 jobserver FIFO | `make -j1`（13 个源文件，串行即可） |
| 6 | CI clean worker 上 configure 找不到 C 编译器 | Autotools 只搜索 gcc/cc，CI PATH 仅提供 clang/clang++ | conanfile.py 在 profile 未设置 `tools.build:compiler_executables` 时回退 `CC=clang`/`CXX=clang++`（tslib/adplay 先例） |

## 源码修改
- `patches/0001-config.guess.patch`：config.guess 识别 HarmonyOS（+3 行）
- `patches/0002-config.sub.patch`：config.sub 识别 ohos 三元组（3 处新增模式）
- `patches/0003-configure.patch`：configure 临时目录 umask 077→022（2 处）

## 依赖版本
无外部依赖（configure.ac 无 `AC_CHECK_LIB`；仅 libc）。

## 验证结果
```bash
# 上游测试（conan create build() 内）
make -j1 check
# → PASS: testsuite（8/8 检查通过）

# test_package C 消费者（链接 liblrcalc，导出 API）
c^{321}_{21,21} = 2 / c^{321}_{3,21} = 1 / c^{4321}_{32,21} = 0

# test_package CLI 功能（打包二进制，逐字节比对）
lrcalc coef / skew / mult -q、schubmult 共 4 项全部通过

# 本地 CI 门禁（ci/conan/build_and_test.sh，与平台 CI 同脚本）
# → L0 pass / L1 pass / L1e 反向验证通过 / L5 pass；L2 skip、L4 warn（均为已知非阻塞）
```

## 注意事项
- 上游把所有头文件装到 `include/lrcalc/`，头文件之间用 `#include <hashtab.h>` 形式互相引用；
  因此 package_info 同时导出 `include` 与 `include/lrcalc` 两个 include 根。
- `share/lrcalc/lrcalc.maple` 会写入构建期 prefix 路径，仅影响 Maple 接口脚本内路径，
  不影响库与命令行行为。
- 上游 `configure` 是随包分发的生成文件，补丁 0003 直接修改它（知识 E011/E129 既定做法，tslib 同款）。

## 对话记录

### 对话 #1 [2026-09-18]

- 问题: `conan create` G2 首轮失败：`configure: error: cannot guess build type; you must specify one`
- 处理: 确认 native 构建时 AutotoolsToolchain 不传 `--host/--build`，configure 必然运行 config.guess；按 E007 方案为 config.guess 补 HarmonyOS 分支、为 config.sub 补 `linux-ohos*` 模式，不使用三元组绕过
- 结果: G2 通过，configure/编译/链接/安装全流程成功

### 对话 #2 [2026-09-18]

- 问题: 首轮 conan 构建中 config.status 写 `subs1.awk` 被拒（HMDFS `umask 077` 目录不可写，E011/E129）
- 处理: 补丁 0003 将 configure 两处临时目录创建的 umask 放宽为 022
- 结果: config.status 正常生成 Makefile/config.h/libtool

### 对话 #3 [2026-09-18]

- 问题: profile 注入的 harmonybrew bash 被 configure 写为 Makefile SHELL，导致 libtool 语法错误与 config.status `print: command not found`（E386 同族）
- 处理: configure 命令行强制 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`；make 用 `-j1` 规避 HMDFS jobserver FIFO 限制（tslib 先例）
- 结果: libtool 编译/链接正常，上游 testsuite 8/8 通过，安装产物完整

### 对话 #4 [2026-09-18]

- 问题: test_package 首轮因 `cmake_layout` 使 cwd 落在 build 目录，`test_lrcalc.sh` 找不到
- 处理: test() 中显式 `cwd=self.source_folder` 并用 `/bin/sh` 运行脚本
- 结果: C 消费者 3/3、CLI 4/4、CI L1e 破坏性反向验证全部通过

---

**编译结束**: 2026-09-18 13:19
**最终状态**: built
状态: built
