# mklibs 0.1.46 适配笔记

## 编译环境
- 构建系统: autotools（`configure.ac` + `Makefile.am`；源码树**不含**生成的 configure，需 autoreconf）
- 编译日期: 2026-09-29
- 编译器: clang / clang++ 15（OHOS SDK；conan profile `compiler.cppstd=17` → `-std=c++17`）
- 状态: published（本地 conan-verify 全门禁通过，未 upload）

## 三重身份
- 任务平台名称: mklibs
- 上游仓库: https://salsa.debian.org/installer-team/mklibs（Debian native 包，`Format: 3.0 (native)`，无独立上游 tarball）
- 归档: `archives/m/mklibs/0.1.46/`

## 语言判定（R47）
- `lang-preflight` → `detected=cpp`（`configure.ac`/`Makefile.am` 存在；源文件 11 个：cpp 7 / python 4，主体 64%）
- 产物：C++ 可执行 `mklibs-readelf`（自带 ELF 解析器，仅 libc/libstdc++）+ Python3 脚本 `mklibs`/`mklibs-copy` + Python 包 `lib/mklibs/python/mklibs`

## 上游测试入口清点（R51，无自动化测试）
- 源码树 33 个文件，**无 tests/ 目录**；`debian/` 无 `tests/`（无 autopkgtest）
- `Makefile.am` / `src/Makefile.am` / `lib/**/Makefile.am` 均无 `TESTS`/`check_PROGRAMS` → **`make check` 无目标**
- 上游真实入口 = man 页描述的三个 CLI；逐项执行记录见 `reports/test-report.md`（21 项：20 PASS / 1 环境限制）

## 编译步骤（真实命令）
1. `autoreconf -fi`（SDK autoconf 2.72 / m4 / perl + tool_requires `automake/1.18`、`libtool/2.5.4`）
2. `./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
3. `make -j2`（探索阶段）/ `-j1`（配方，R9）
4. `make install DESTDIR=$TEST_PREFIX`
5. `conan create`（含 `test_package`）

## 遇到的问题与解决方案（首个错误 → 根因 → 修复 → 复验）

| # | 首个错误 | 根因 | 修复 | 复验 |
|---|---------|------|------|------|
| 1 | `aclocal: Can't locate Automake/Config.pm in @INC (@INC entries checked: //share/automake-1.18 ...)` | conan automake 包内 datadir 前缀为相对路径，未通过 conan buildenv 提供 `PERL5LIB` | 使用 conan 生成的 `conanbuildenv-release-armv8.sh`（含 `PERL5LIB`/`ACLOCAL`/`AUTOMAKE`/`_lt_pkgdatadir`）；配方中由 `tool_requires` 自动生效 | `autoreconf -fi` exit=0，生成 configure/Makefile.in/config.h.in |
| 2 | `configure: error: cannot guess build type; you must specify one`（`uname -s = HarmonyOS`） | automake 1.18 的 `config.guess`（2024-07-27）不识别 HarmonyOS（E007 同族） | 显式 `--build/--host=aarch64-unknown-linux-gnu`（不修改 config.guess） | configure 通过 build/host 探测 |
| 3 | `config.status: error: could not setup config files machinery` / `./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 `mktemp -d` 产出的目录不可写（E002 同族） | 构建期 `mktemp` wrapper（`mkdir` 语义模拟 `mktemp -d`，非 `-d` 调用转发真实 mktemp），PATH 前置且仅作用于 build 子进程 | configure exit=0，6 个 Makefile 全部生成 |
| 4 | `FileNotFoundError: [Errno 2] No such file or directory: 'dpkg-architecture'`（`mklibs --help` 即崩） | `multiarch()` 未捕获命令缺失（`subprocess.Popen` 直接抛异常），Python3 下任何入口都会在模块级 `default_lib_path = multiarch([...])` 处崩溃 | 补丁 0003/0004：`try/except OSError` 回退到原 paths（与上游 returncode!=0 分支语义一致） | `mklibs --version` exit=0；默认库路径回退为 `/lib/:/usr/lib/:/usr/X11R6/lib/` |
| 5 | `AttributeError: module 'string' has no attribute 'split'` | 上游为 Python2 代码，`string.join/split/rfind` 在 Py3 已移除 | 补丁 0003：替换为标准 str 方法（6 处） | 主流程继续推进 |
| 6 | `AttributeError: 'dict' object has no attribute 'has_key'` | Py2 遗留 | 补丁 0003/0004：`has_key` → `in`（4 处）、`itervalues()` → `values()` | 主流程继续推进 |
| 7 | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb7` | Py3 文本模式 `open(prog).read(256)` 读取二进制 ELF（`script_pattern` 探针） | 补丁 0003：改二进制读 + latin-1 解码；0004：改 `rb` + `b'ELF'` 比较 | 主流程继续推进 |
| 8 | `TypeError: can't concat str to bytes`（`os.popen(...).read()`） | **本机 OHOS Python 3.12.9 的 `os.popen()` 文本模式 `read()` 本身不可用**（最小复现 `python3 -c "import os;print(os.popen('echo hi','r').read())"` 即失败），与 mklibs 无关 | 补丁 0003/0004：`command()` 改用 `subprocess.Popen(..., shell=True, stdout=PIPE, universal_newlines=True)` + `communicate()`，退出码改用 `returncode` | `mklibs -d` 端到端 exit=0 |
| 9 | `TypeError: level must be an integer`（`logging.log(VERBOSE,...)`） | `VERBOSE = (INFO + DEBUG) / 2` 在 Py3 为 float | 补丁 0001：改为 `//`（整除） | `mklibs-copy` 启动正常 |
| 10 | `TypeError: '>=' not supported between instances of 'NoneType' and 'int'` | optparse `action='count'` 默认 None，Py2 允许与 int 比较 | 补丁 0002：`-v/--verbose` 增加 `default=0` | `mklibs-copy --help` exit=0 |
| 11 | `cp: bad '/system/lib64/libc.so': Permission denied`（mklibs-copy 端到端） | 平台 SELinux 限制：该文件 `head` 可读但 `cp` 被拒 | 测试改用可读的 `/lib/ld-musl-aarch64.so.1` 副本作为 libc.so（仅测试环境准备，不改源码） | `mklibs-copy -d` 端到端 exit=0 |
| 12 | `error: unknown type name 'typeof'`（`elf.cpp`，conan 构建） | 上游使用 GNU 关键字 `typeof`；手工构建默认 `gnu++17` 可用，但 conan profile 的 `-std=c++17` 禁用该扩展 | 补丁 0005：`typeof` → `__typeof__`（44 处，GCC/Clang 在两种 -std 模式下均支持） | conan create 编译通过 |
| 13 | `apply_conandata_patches: source/target file does not exist: a/lib/...` | conan `patch()` 默认 `strip=0`，而 refresh-patch 生成的补丁使用 `a/`、`b/` 前缀 | conandata.yml 每个 patch 显式 `strip: 1` | 5 个补丁全部应用成功 |
| 14 | `source/target file does not exist: lib/mklibs/utils/logging.py`（strip 修正后） | 源码 tarball 顶层有 `mklibs-0.1.46/` 目录（init-build 曾自动剥离，导致误判为无顶层目录） | `source()` 改 `strip_root=True` | source() 正确解压 |
| 15 | `replace_in_file didn't find pattern '#!/usr/bin/python3' in .../bin/mklibs` | 上游两个脚本 shebang 不一致（`mklibs` 为 `#! /usr/bin/env python3`，`mklibs-copy` 为 `#!/usr/bin/python3`） | package() 中 `replace_in_file(..., strict=False)`，仅规范化硬编码绝对路径的那个 | conan create 全流程通过 |

## 源码修改（5 个补丁）
| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | `lib/mklibs/utils/logging.py` | VERBOSE 常量整除（+1/-1） |
| 0002 | `lib/mklibs/utils/main.py` | `-v/--verbose` 默认值 0（+1/-0） |
| 0003 | `src/mklibs` | Py3 移植（string.*、os.popen、has_key、二进制读取）+ multiarch 容错（+26/-18） |
| 0004 | `src/mklibs-copy` | Py3 移植（os.popen、has_key、itervalues、二进制读取）+ multiarch 容错（+20/-12） |
| 0005 | `src/mklibs-readelf/elf.cpp` | `typeof` → `__typeof__`（44 处） |

> 补丁均为通用可移植性修复，**不含任何平台宏**（未使用 `__OHOS__`，R8/PF5 通过）。

## 依赖版本（构建期）
- tool_requires: `automake/1.18`、`libtool/2.5.4`（ohpcd）；SDK: autoconf 2.72 / m4 / perl 5.42.0 / clang 15
- 运行期（不声明为 conan requires，属系统/环境工具）：`binutils`（objcopy）、`gcc`（重链接）、`dpkg-architecture`（可选，缺失时已容错）、python3
- 本库**无第三方 C/C++ 库依赖**（`mklibs-readelf` 自带 ELF 解析器）

## 验证结果
```bash
# conan-verify（G0-G4 / L2 / L4 / L5 全部 PASS）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify mklibs 0.1.46   # exit=0
# test_package（conan create 内）8 条断言全部 PASS
#   PASS: mklibs-readelf --version -> 0.1.46
#   PASS: mklibs-readelf --help lists all documented options
#   PASS: -i -> /lib/ld-musl-aarch64.so.1 / -n reports libc / -R / -p / -u
#   PASS: python entry points (mklibs / mklibs-copy)
#   test_package: all assertions passed
```

## 注意事项
- 上游 usage 文本中残留 `", file=outfd)"`（上游把 `file=outfd` 批量注入 print 时的字符串污染），仅影响帮助文本可读性，不影响功能；未修改以免扩大补丁面。
- `mklibs`/`mklibs-copy` 主流程需要目标环境提供 `objcopy`/`gcc`（可通过 `--target` 前缀替换）；`dpkg-architecture` 缺失时回退为普通路径（`/lib:/usr/lib:/usr/X11R6/lib`）。
- DEST 目录需由调用方预先创建（上游约定，非缺陷）。
- 本机 python3 的 `os.popen()` 不可用属平台特性，配方已通过补丁改用 `subprocess`，无运行期依赖。
---

**编译结束**: 2026-09-29 08:26
**最终状态**: published
