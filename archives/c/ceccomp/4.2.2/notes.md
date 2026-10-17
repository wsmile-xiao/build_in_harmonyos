# ceccomp 4.2.2 适配笔记

## 编译环境
- 构建系统: custom（上游 configure 为手写 Python 脚本（argparse），读 env CC/CFLAGS/LDFLAGS 生成 Makefile 后 make——非 autotools，无 config.guess/config.status）
- 编译日期: 2026-09-08
- 编译器: clang（OHOS，`/data/service/hnp/bin/clang`，经 profile `tools.build:compiler_executables` 注入 conanbuild env）
- 状态: built

## 编译步骤

1. `conan.tools.files.get` 下载官方 GitHub tag tarball（SHA-256 两端各自下载比对一致），`apply_conandata_patches` 应用补丁。
2. `generate` 阶段：AutotoolsToolchain 生成 conanbuild env（CC/CFLAGS/LDFLAGS 全部来自 Conan 依赖图，R33），硬化 flag 与设备原生探索一致（`-fpie -fstack-protector` / `-z now -z noexecstack -fpie -fstack-protector`）。
3. build 阶段把依赖（libseccomp/2.6.1 共享包 + argp-standalone/1.5.0 静态包）的 include/lib 合并进 build 目录两个目录——上游 configure 只接受**单一** `--includedir`/`--libdir`，且其编译/链接探测只认这两个目录。
4. `python3 ./configure --prefix=/ --without-doc --without-i18n --includedir=<合并include> --libdir=<合并lib>`（conanbuild env 下执行）。
5. `make -j1`（设备默认并行度）。
6. package 阶段手动 copy：`build/ceccomp` → `bin/`、`completions/_ceccomp` → `res/zsh/site-functions/`、LICENSE → `licenses/`。上游 `make install` 依赖 coreutils `install`（OHOS toybox 无此命令，实测 error 127），必须手动打包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure argp 回退探测必失败（`argp.h file not found`） | musl/OHOS 无 argp.h；上游第二段 `-largp` 探测不带 `-I/-L` sys 目录（libseccomp 探测有 `push_sys_dir=True`，argp 探测漏了），conan 包目录不在编译器默认搜索路径 | 补丁 0001：argp 探测补 `push_sys_dir=True`，与上游 libseccomp 探测写法一致 |
| 2 | i18n 编译失败（`ceccomp.c` 两处 int→const char* error） | OHOS SDK `libintl.h` 存在但无 gettext/bindtextdomain/textdomain 声明，`_()` 隐式 int | configure 选项 `--without-i18n`（上游支持选项，不改源码） |
| 3 | `struct prctl_mm_map` 重定义（SDK `sys/prctl.h:88` 与 `linux/prctl.h:96`） | 两头文件重复定义，read_source.c/str_pile.c/unit_test.c 同时包含两者 | 补丁 0001：删除 `#include <linux/prctl.h>`（SDK sys/prctl.h 已含 PR_SET_VMA 系常量与 prctl() 声明，源码用到的符号全在其内，且用法均有 #ifdef 保护） |
| 4 | probe/trace 运行时报 `Failed to request a temporary file: Permission denied` | `tmpfile()` 固定写 `/tmp`，OHOS 设备 `/tmp` 不可写（实测 EACCES） | 补丁 0002：probe.c 新增 `open_trace_tmpfile()`（getenv TMPDIR + mkstemp + unlink + fdopen，POSIX 通用实现、无平台条件编译；TMPDIR 未设回退 /tmp 保持原行为） |
| 5 | `make install` 失败（error 127） | OHOS toybox 无 coreutils `install` | 配方 package() 手动 copy（与上游 install 同清单：二进制 + zsh 补全；doc/i18n 已禁用） |
| 6 | make 期间大量 `flock: Unknown option 'c'` 噪音 | toybox flock 不支持上游使用的选项 | 噪音不影响构建结果，不处理 |
| 7 | CI worker 上 conan create 失败：`[ 1/13] Checking system platform... ohos` → `[ERR!] Ceccomp only support Linux!`（设备原生构建与清缓存验证均通过） | configure `check_platform` 白名单 `sys.platform == 'linux'`；两端 CPython 构建不同——设备 hnp python3.12.8 报 `'linux'`，CI worker OHOS CPython 报 `'ohos'`，设备验证暴露不了该差异 | 补丁 0003：白名单改为 `sys.platform in ('linux', 'ohos')`（OHOS 即 Linux 内核，seccomp BPF 行为一致），info 打印实际平台值；android/其他平台分支不变。已核实 configure 其余平台敏感点均不致命：`freedesktop_os_release` 有 try/except 回退且 `--prefix=/` 走 `'manual'` 分支，`check_architecture` 对未知架构仅告警 |

## 源码修改

- `patches/0001-ceccomp-4.2.2-ohos-portability.patch`：configure argp 探测补 `push_sys_dir=True`；删除 read_source.c/str_pile.c/unit_test.c 的 `#include <linux/prctl.h>`（M1/M3/M4）
- `patches/0002-ceccomp-4.2.2-probe-tmpdir.patch`：src/probe.c 临时文件 TMPDIR 感知（M5）
- `patches/0003-ceccomp-4.2.2-configure-platform-ohos.patch`：configure `check_platform` 平台白名单接受 `sys.platform='ohos'`（CI worker 实测值；设备 hnp python 报 `'linux'` 故原生探索未暴露，见问题 #7）（M6）
- 均为 portability 类，无平台条件编译（R8）；configure 选项 `--without-doc --without-i18n` 走上游支持选项（M2），不改源码

## 依赖版本

- libseccomp/2.6.1（ohpcd，共享包，运行时 NEEDED libseccomp.so.2）
- argp-standalone/1.5.0（ohpcd，静态包）
- W0 在设备以 `conan install --build=never --profile:host=ci/conan/profiles/ohos-aarch64` 验证 binary 可用

## 预检查说明

- **lang-preflight env_unsupported 为已知误判，不阻塞**：源码内 `py-temp/pyproject.toml` 被 manifest 扫描判为 python 打包清单，但该目录是 PyPI 分发 shim（`__init__.py` 仅 chmod+execv 编译好的 C 二进制，package-data 只含二进制），主体为 C（35 个源文件中 c:25，占 71%，构建系统 autotools 型 configure+make）。按 workflow 4.2「辅助脚本不决定主体语言」人工复核留证。
- **prescan critical（mremap）实证可用**：`src/utils/read_source.c:150` 的 mremap() 无特性宏守卫（非死代码），但 OHOS musl 实际提供该符号——设备原生构建链接成功且 87 项上游测试（含覆盖 read_source 的 emu/asm 路径）通过。
- **prescan medium（argp_）**：由 argp-standalone 依赖解决，见问题 #1。

## 验证结果

上游测试（设备原生，pytest 9.1.1，Python 3.12.8；HOME 沙箱 + PKG_CONFIG_PATH 指向 PkgConfigDeps 生成的 .pc）：

```text
collected 91 items
=================== 3 failed, 87 passed, 1 skipped in 13.56s ===================
TOTAL=91 = PASS 87 + FAIL 3 + SKIP 1 + NOT_RUN 0（统计单位：pytest 用例，取数命令
python3 -m pytest test/ --collect-only -q | tail -1）
```

FAIL 3 项均为动态测试 `test/test_dynamic.py::test_probe / test_trace / test_seize`，
根因为**平台安全策略拒绝 PTRACE_SEIZE**（对自身子进程也 EPERM，最小复现程序
ptrace-repro.c 实测 `PTRACE_SEIZE(...)=-1 errno=13(Permission denied)`），属
workflow 7.3「环境限制：安全策略」，有原始 stderr（`[ERROR]: Unknown error when
seizing process: Permission denied`）。影响范围：动态提取功能（probe/trace/seize
子命令）；替代验证：静态功能 asm/disasm/emu 87 项全部通过。

SKIP 1 项：`test_dynamic.py:140 trace_pid`（需 CAP_SYS_ADMIN，上游 README 载明
该能力要求，预期行为）。

ELF 安全属性（L4，设备 readelf 实测）：`Type: DYN (Position-Independent
Executable)`、`GNU_RELRO` 存在、`FLAGS BIND_NOW`（full RELRO）、NEEDED 仅
`libseccomp.so.2 + libc.so`。

test_package：`version` 输出断言 + `asm→raw→disasm→asm` 往返逐字节一致（命令
2026-09-08 设备实测通过）。

## 注意事项

- 上游 `ceccomp --help` 是全局选项形式，子命令为 `asm/disasm/emu/probe/trace/help/version`；无 `--version` 长选项。
- OHOS 无 BPF syscall（同 libbpf 适配结论），本包仅链 libseccomp 用户态 API，不依赖 BPF syscall；动态提取能力受 ptrace 安全策略限制。
- pytest 套件的 chromium 组依赖 pkg-config 找到 libseccomp.pc ≥2.5.6：验证环境用 `conan install -g PkgConfigDeps` 生成的 .pc 注入 `PKG_CONFIG_PATH`（禁止指向依赖包自带 .pc，其 prefix 固化打包机路径）。
- pytest 9.1.1 安装在设备用户 site：沙箱 HOME 下需 `PYTHONUSERBASE=/storage/Users/currentUser/.local`。
