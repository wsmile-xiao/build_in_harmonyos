# pax-utils 1.3.10 适配笔记（任务 #9337）

## 上游坐标

- 仓库：`gentoo/pax-utils`，tag **`v1.3.10`**（tag 名带 `v`；不带 v 的 `1.3.10` 实测 404）。
- 制品：GitHub tag archive 即官方制品（上游没有独立 release 附件），
  `.../archive/refs/tags/v1.3.10.tar.gz` 与 `codeload.../tar.gz/refs/tags/v1.3.10`
  两种端点各下载一次，**字节一致**：148315 B，
  sha256 `4ee86899b0cb8b702f443908dc4e9e5e19a2bd870d0520cbae4066658c89df14`。
- 配方里的 `sources.url` 取 codeload 单值：真机直连 `github.com/archive` 两次
  ConnectTimeout/ReadTimeout（conan 自带重试也失败），codeload 官方端点可达；
  写成 list 会关掉 CI 的镜像注入（`build_and_test.sh` 的 `replace_url()` 只重写
  单值带引号的 `url:`，openssl #11127 实测），所以保持单值 + `filename=` 显式命名
  （codeload 路径没有 `.tar.gz` 后缀，不显式命名 conan 会按 zip 解 → BadZipFile）。
- 依赖：**零外部依赖**。`use_libcap=disabled`（唯一可选依赖），`use_seccomp` 只需内核
  支持不需 libseccomp；构建工具 `meson/1.11.0`、`ninja/1.12.1`、`pkgconf/3.0.5` 全部
  以 tool_requires 引入，三者都在 ohpcd 远端有**预编译二进制**（真机日志
  `Download (ohpcd)`；CI 用 `--build=<pkg>/*` 只构建本包，所以必须是二进制）。

## 真机上撞到的两个独立阻断点（都实测，不是推断）

1. **`#!/bin/bash` shebang → meson 误报"测试脚本不存在"。**
   `tests/*/dotest*`、`lddtree.sh`、`symtree.sh` 的 shebang 硬编码 `/bin/bash`，
   OHOS 真机 `/bin/bash` 不存在（bash 在 `~/.harmonybrew/bin/bash`）。execve 的
   ENOENT 指向的是**解释器**，但 python 的 subprocess 把异常抛在脚本路径上，
   meson 打印 `FileNotFoundError: .../tests/lddtree/dotest-sh`，看起来像"文件丢了"。
   `meson test` 因此 `Ok: 0 / Fail: 0` —— 一个用例都没跑却零失败，正是 E363 警告的
   假绿形态。修法：`patches/0001-use-portable-interpreter-shebangs.patch` 把 10 个
   脚本改成 `#!/usr/bin/env bash`（`/usr/bin/env` 在真机是 toybox 的软链，实测可用）。
   同一机制在知识库已有：`DRAFT-date-3.0.3-ohos-bash-shebang`（CTest 侧 BAD_COMMAND）、
   E037（shebang-fix）、E363（不得把这类失败报成上游套件通过）→ 本条按路径 A 复用。

2. **`security_init()` 里的两条自沙箱路径在 OHOS 上会自杀。**
   - 2a `unshare(CLONE_NEW*)` 被**平台全局 seccomp 策略**直接 SIGSYS 杀掉。
     最小探针（SDK clang 编、真机跑）逐条测得：
     `prctl(PR_SET_NO_NEW_PRIVS,1)` → r=0；`prctl(PR_SET_SECUREBITS,...)` → r=-1
     errno=1 EPERM（活着）；`unshare(CLONE_NEWIPC|CLONE_NEWUTS)` → **Signal 31
     (core dumped)，run_rc=159**。上游 `ns_unshare()` 只对 EPERM 做逐位降级重试，
     拿不到 EPERM 而是被杀，于是每个工具在 `main()` 第一句 `security_init()` 就死，
     连 `scanelf -V` 都是 159。修法：`patches/0002-security-unshare-sigsys-guard.patch`
     给 `unshare()` 调用套一层**运行期** SIGSYS 守卫（`sigaction` 只在调用期间接管
     SIGSYS、`sigsetjmp/siglongjmp` 跳出、把 trap 翻译成 EPERM），交给上游原有的
     EPERM 降级路径去报告"无 namespace 可用"（这些工具只是读 ELF 文件，不需要
     CLONE_NEW*）。**不用平台条件编译宏**：仓规 R8 禁止源码/补丁引入 `__OHOS__`
     这类平台宏，且那种写法完全依赖工具链是否定义该宏——宏没定义时补丁整段失效，
     `unshare()` 照样被杀而编译/`meson test`/`conan create` 全都不报错（E363 假绿）。
     改成运行期探测后，判据来自内核实际投递的信号，任何平台同一套逻辑，不存在静默跳过。
     本条属于 E051/E246 记的"OHOS seccomp 拦截 Linux 私有 syscall → SIGSYS/exit 159"家族，
     按路径 A 复用。
   - 2b 打完 0002 之后 `meson test` 6/6 通过，但消费者测试里 `dumpelf` 与 `pspax`
     仍然 rc=159，而 `scanelf` 全绿。差别在调用参数：`dumpelf`/`pspax` 走
     `security_init(false)` → 装 `seccomp_bpf_program_base`；`scanelf` 走
     `security_init(true)` → 装 `seccomp_bpf_program_fork`。也就是说**上游自带的
     那份手写 BPF 白名单（按 Gentoo/glibc 的系统调用序列写）在 musl 上会杀掉自己
     进程的退出路径**，而 fork 变体恰好放过。修法：`-Duse_seccomp=false`
     （上游自带的开关），代价是打包出来的工具不再自我降权，功能不受影响。

## conan / 构建侧

- `conan.tools.meson` 在 conan 2.29.1 只导出 `Meson` 与 `MesonToolchain`：仓内模板
  `archives/u/unudhcpd/0.2.1-r2/conanfile.py` 的 `from conan.tools.meson import ...
  meson_layout` 直接 ImportError，`Meson` 也没有 `compile()`（真名 `build()`）。
  本配方用 `basic_layout` + `configure/build/test/install`。
- `meson.build` 的 `vcs_tag()` 没写 `fallback`，但 meson 在缺省时自动取
  `project_version`（`mesonbuild/interpreter/interpreter.py:2089`
  `fallback = kwargs['fallback'] or self.project_version`），所以无 `.git` 的
  tag tarball 不需要额外补丁；`-V` 打出的 `pax-utils-1.3.10: 1.3.10` 就是这个回落值。
- 真机 PATH 无 `meson`、无 `xmlto`（`readelf`/`ar`/`strip` 也不在 PATH，但本包用不到
  `ar`，`-Dbuild_manpages=disabled` 免掉 xmlto）；`/tmp` 只读，所以消费者测试的临时
  目录一律建在 `$PWD` 下。
- CI worker 侧 `python3` 一定存在（`build_and_test.sh` 自己就用 python3），
  所以 `meson test` 与 shell 用例在 CI 上同样可跑。

## 上游用例在本平台的有效性边界（不粉饰）

`meson test` 的 6 条里，真机上**只有 `scanelf-test` 与 `pspax-test` 真正检验了行为**：

| 用例 | 真机状态 | 是否有效 |
|---|---|---|
| scanelf-test | PASS | 有效：golden 逐字节比对 |
| pspax-test | PASS | 有效：真跑 /proc 且要求 stderr 为空 |
| lddtree-sh | PASS | **空跑**：输入 `/bin/bash` 在本机不存在，期望"无 none 输出"被空 stdout 满足 |
| lddtree-py | PASS | **空跑**：同上，且 python 侧缺 `elftools` 模块（`lddtree.py:64`） |
| lddtree-cmp | PASS | **弱**：比较 py/sh 两份输出，本机两份都为空 → 只证明"空==空" |
| source tests | PASS | **空跑**：脚本用未导出的 `top_srcdir`，`find ''` 报错后产出空文件 |

正因为这条边界，`lddtree_implementation` 选 `sh`（python 版在目标机没有 pyelftools），
并且补了 27 条消费者断言，把三个工具的 `-V`、符号解析、`EM_AARCH64=183`、
`/proc` 枚举、`libc.so` 依赖解析、递归扫描与 2 条负向对照全部实测覆盖。

## 已知限制

1. 打包件不含上游的运行期自沙箱（`use_seccomp=false`），原因见 2b；这是本机可用的
   前提，不是可选优化。
2. `symtree` 只断言安装性、不断言运行：它的输出取决于 `lddtree` + `scanelf` 对整棵依赖树
   的解析结果，任何 ELF 都可能合法地打印 `useless link`/`UNRESOLVED`，断言 rc=0 证伪不了
   任何东西。另外它只有 `-h/-x` 两个选项，所以 CI 的 L2 冒烟对 `symtree --version` 报
   `[warn]`（非阻断）。`lddtree.sh` 有 `-V`（打印 "lddtree by ..."），L2 对它可通过。
3. `tests/` 里 4 条用例在本平台空跑，见上表；未改动任何上游测试断言。
