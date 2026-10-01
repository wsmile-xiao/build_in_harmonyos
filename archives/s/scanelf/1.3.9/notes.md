# scanelf 1.3.9 适配笔记

## 编译环境
- 构建系统: meson（`meson.build` + `tests/*/meson.build`，MesonToolchain + Meson helper）
- 编译日期: 2026-09-30
- 编译器: clang/clang++ 15（OHOS SDK 26.0.0.18，aarch64-linux-ohos，libc++，cppstd 17）
- 构建工具: `tool_requires meson/1.11.0` + `ninja/1.12.1` + `pkgconf/3.0.5`
  （三者均在 ohpcd 制品仓有 OHOS 预编译二进制；W0 预检 `conan download … -r=ohpcd` 全部 rc=0）
- 状态: published

## 包定位（为什么是独立包）
scanelf 没有独立上游仓库：源码取 Gentoo **pax-utils v1.3.9** 的官方 tag 归档，本配方只交付
`bin/scanelf` 一个可执行文件。同一源码树的其他工具（dumpelf / pspax / scanmacho / lddtree /
symtree）属聚合包 `archives/p/pax-utils/1.3.10`，本配方在 `package()` 里 `rm` 掉；同时在
conanfile 里声明 `provides = "pax-utils"`，避免下游以为二者互斥。

## 编译步骤
一键复验（G0 预扫描 → G1 配方完整性 → G2 干净 `conan create` → G3 系统同名库隔离 → G4 产物
→ L2/L4/L5）：

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify scanelf 1.3.9
```

`G2` 等价手工链（profile `ci/conan/profiles/ohos-aarch64`）：

```bash
conan create . --user=ohpcd --channel=stable \
    -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
```

conanfile.py `build()` 内部实际执行：

```bash
meson setup --native-file <build>/conan/conan_meson_native.ini <build> <src> --prefix=/
meson compile -C <build> -j20
meson test -v -C <build>        # 上游官方套件（本次实跑）
meson install -C <build> --destdir <package_folder>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备 PATH 上没有 meson，构建无法启动 | 设备只带 ninja/python3/bash/git/pkg-config | 改 `tool_requires meson/1.11.0`（R18/R36：先查制品仓，已发布即不本地编译） |
| 2 | `meson setup` 在 `meson.build:1:0` 直接 ERROR: `Unknown linker(s): [['llvm-ar']]` | conan 的 Meson helper 不把 profile `buildenv` 注入 `meson setup` 子进程，meson 回退 PATH 找 clang 默认归档器 `llvm-ar`，CI worker 上不在 PATH | 由 `generate()` 显式 pin LLVM 工具（`clang/clang++/llvm-ar/llvm-nm/llvm-strip/ld.lld`，取 `realpath(/data/service/hnp/bin/clang)` 的目录），并加 `os.path.isdir` 守卫（同坑见 `archives/a/account-utils`，正例 `archives/j/jose/15`） |
| 3 | `meson test` 报 `tests/*/dotest` 脚本缺失 / `lddtree.sh: /bin/bash: file does not exist` | 上游 10 个 shell/python 脚本写死 shebang：`#!/bin/bash`（OHOS 无 `/bin/bash`，bash 在 harmonybrew 前缀下）、`#!/usr/bin/env python`（PATH 上只有 `python3`）；execve 直接 ENOENT，meson 把执行失败误报成脚本缺失 | `patches/0001-use-portable-interpreter-shebangs.patch`：`#!/usr/bin/env bash` + `#!/usr/bin/env python3` |
| 4 | 进程在 `security_init()` 内被杀（SIGSYS，exit 159），工具完全起不来 | `unshare(CLONE_NEW*)` 被平台 seccomp 以 `SECCOMP_RET_TRAP` 拦截：内核投递 SIGSYS（默认处置=杀进程），而不是返回 `-1/EPERM`；上游只处理 EPERM 的回退路径看不到失败 | `patches/0002-security-unshare-sigsys-guard.patch`：只在 `unshare()` 调用期间挂 `sigaction(SIGSYS)` + `sigsetjmp`，把陷入翻译成 EPERM（`ns_unshare()` 本来就会降级成的状态）。运行期探测，不绑任何工具链宏，`unshare()` 成功或返回自身 errno 时行为不变 |
| 5 | 修好 4 后 dumpelf / pspax 仍被 SIGSYS 杀死（本包不交付它们，但会影响同树套件） | 上游手写 BPF allowlist（`security_init(false)` → `seccomp_bpf_program_base`）按 Gentoo/glibc 的 syscall 用法编写，OHOS 上必然误杀 | `-Duse_seccomp=false`；scanelf 自身走 `security_init(true)` 的 fork 程序本可存活，关掉后只是不再自我降权 |
| 6 | `man/` 子目录构建失败 | 设备无 xmlto，`build_manpages` 默认 auto 会去构建 | `-Dbuild_manpages=disabled` |
| 7 | 不关会多出 2 条 libFuzzer 用例 | `-Duse_fuzzing=true` 编出并**执行** libFuzzer 探针 | `-Duse_fuzzing=false`（sanitizer 探针不是功能测试） |
| 8 | `lddtree.py` 报 `ModuleNotFoundError: No module named 'elftools'` | 目标环境无 pyelftools | `-Dlddtree_implementation=sh`（本包不交付 lddtree，仅为让上游套件在无 py 依赖下可跑） |
| 9 | 探测脚本自伤：`/tmp/o: Read-only file system` | 本机 `/tmp` 只读 | 临时文件落 `$TMPDIR` 或工作目录（平台事实，非配方问题，记账以免重复踩） |

## 源码修改
只打两枚补丁，**不改任何源文件本体、不引入平台条件编译宏**：

- `patches/0001-use-portable-interpreter-shebangs.patch`（portability）：10 个脚本的 shebang 可移植化。
- `patches/0002-security-unshare-sigsys-guard.patch`（portability）：`ns_unshare()` 的 SIGSYS 运行期守护。

两枚补丁沿用 `archives/p/pax-utils/1.3.10` 已验证版本，在 1.3.9 源码树上干净适用（`meson.build`
与 `security.c` 两版一致；已用 `git apply --check` + 实跑双向确认）。

## 依赖版本
无运行时 `requires`（`-Duse_libcap=disabled` 保持零依赖）。构建期：

| 依赖 | 版本 | 类型 | 来源 |
|------|------|------|------|
| meson | 1.11.0 | tool_requires | ohpcd 已发布预编译 |
| ninja | 1.12.1 | tool_requires | ohpcd 已发布预编译 |
| pkgconf | 3.0.5 | tool_requires | ohpcd 已发布预编译 |

## 验证结果

**上游官方套件**（`meson test -v -C <build>`，日志 `reports/conan-create.log`）：

```
Ok: 6   Fail: 0
```

13 条 PASS 明细中，**真实有效的 2 套**：`scanelf-test`（本包交付物的直接对应用例，
`scanelf -qsmain -F'%s %f'` 输出与 golden 逐字节比对）、`pspax-test`（读 OHOS procfs 枚举进程）；
其余 4 套（`lddtree-sh/py/cmp`、`source tests`）在本平台**空跑**——原因逐条写在
`test_package/MANIFEST.yml` 的 `upstream_tests` 里（上游把 `/bin/bash` 当固定输入、缺 pyelftools、
上游脚本用了未定义的 `top_srcdir`），不是本次移植引入。

**消费者用例**（`test_package/test_scanelf.sh`，15 条断言，含 4 条鸿蒙特有场景）：

```
PASS: 15  FAIL: 0  (total 15)
consumer test OK
```

**门禁**（`reports/conan-verify-report.md`，**Verdict: PASS**）：

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ✅ | 预构建风险扫描 |
| G1 | ✅ | 配方完整性（conanfile.py + conandata.yml + test_package/ + patches/） |
| G2 | ✅ | 干净 `conan create`（复核构建 6/6 + 消费者用例 15/15） |
| G3 | ✅ | 系统同名库隔离 |
| G4 | ✅ | 产物完整性（bin/scanelf） |
| L2 | ✅ | `--version` 自证：`pax-utils-1.3.9: 1.3.9` |
| L4 | ✅ | 安全扫描 |
| L5 | ✅ | 产物基线 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/scanelf` | 104896 B | ELF/PaX 信息扫描器；`ET_DYN`，`NEEDED = libc.so`（OHOS musl） |
| `licenses/COPYING` | — | GPL-2.0-only |

包内共 2 个文件。同树其余工具已在 `package()` 中剔除（见「包定位」）。

## 注意事项

1. **上游 6 套件里只有 2 套在本平台真实有效**，PR 里的通过率必须按「有效用例」口径读，
   不能把 4 套空跑的 PASS 当成覆盖（这也是本包要补 15 条消费者断言的原因）。
2. **OHOS 的 musl 把 libc 与动态加载器做成同一个文件**：`/system/lib/ld-musl-aarch64.so.1`。
   进程 `/proc/self/maps` 里没有 `libc.so` 条目——任何「按 libc.so 找系统 C 库」的探测在
   OHOS 上都会落空，要匹配 `ld-musl-*` 或 `libc.so*`（消费者用例第 5 条即按此写）。
3. 本包 `package_type = "application"`，消费者通过 `cpp_info.bindirs` 拿到 `bin/`；CLI 工具的
   声明在软件级 `archives/s/scanelf/commands.json`（R38）。
4. 两枚补丁都是**运行期能力探测**，不含 `__OHOS__` 之类平台宏（R8）。
5. 设备 `/tmp` 只读：任何脚本/测试的临时文件要用 `$TMPDIR` 或工作目录。
---

**编译结束**: 2026-09-30 22:48
**最终状态**: built
