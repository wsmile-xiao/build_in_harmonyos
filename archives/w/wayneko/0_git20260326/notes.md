# wayneko 0_git20260326 适配笔记

- 软件：wayneko（Wayland layer-shell 动画 Neko 猫客户端）
- 上游：<https://git.sr.ht/~leon_plickat/wayneko>
- 版本：`0_git20260326` = commit `437a8a708ea68f0288becb047b582e84ef3e412c`
  （author date 2026-03-26，subject `fix incompatible-pointer-types errors with GCC 14`）
- 构建系统：纯 GNU Makefile（targets：wayneko / install / uninstall / clean）
- 结论状态：`built`（conan create 全绿，test_package 全绿）

---

## W0 — 依赖发布检查（适配前）

```
$ bash ci/scripts/preflight_check.sh wayneko/0_git20260326
[OK] 已发布: pixman/0.46.4.3
[OK] 已发布: wayland/1.22.0.1
[OK] 版本号未被占用: wayneko/0_git20260326
[OK] 所有依赖均已发布到制品仓，可以安全开始适配 wayneko/0_git20260326
```

R35 二次核验（`conan download --only-recipe`，禁用 `conan list`）：

```
$ conan download wayland/1.22.0.1 -r=ohpcd --only-recipe
    wayland/1.22.0.1 / revisions / 35e87d485ba1da47c7aed110c0ec8186 (2026-09-09 ...)
$ conan download pixman/0.46.4.3 -r=ohpcd --only-recipe
    pixman/0.46.4.3  / revisions / a31abd1c6388fde1ace5ca4523ac025d (2026-08-21 ...)
```

两个依赖均已发布 → 正常继续。

## W0b / R47 — 语言预检

```
$ python3 scripts/ohc-run.py lang-preflight wayneko 0_git20260326 --src <src>
  ✅ 语言匹配: task=cpp, detected=c — 继续适配主流程
  {"expected":"cpp",
   "detected_language":"c",
   "language_evidence":{"build_system":"make",
                        "manifest":"顶层 Makefile（无更强 manifest）",
                        "source_stats":"源文件 1 个（c:1），主体占比 100%"}}
```

c↔cpp 同兼容族（R47 边界规则），通过，继续。

---

## 源码与提交出处

- 官方源（R39，https 官方）：`https://git.sr.ht/~leon_plickat/wayneko/archive/437a8a708ea68f0288becb047b582e84ef3e412c.tar.gz`
- sha256（两次独立下载一致）：
  `d398b017c6ec0fab435f225a3fa907211011fee92115d6bf1bfc10ec68eec2c3`
- 补丁：无（`patches: {}`，未修改任何上游源码）。

---

## 关键决策：wayland-scanner 无法在 OHOS 执行（复用仓库内先例 a）

### 现象（实测）

```
$ /storage/Users/currentUser/.conan2/p/waylaede4fc0cdc6af/p/bin/wayland-scanner --version
sh: .../wayland-scanner: Operation not permitted
exit=126
```

wayland/1.22.0.1 包内 `bin/wayland-scanner`（从 Conan 缓存中取出 / 甚至 `cp` 到 $TMPDIR 后）
都无法 `execve`。但**在 Conan 构建目录里新编译出来的二进制可以执行**（实测）：

```
$ clang -o .../exectest/hello hello.c
$ .../exectest/hello
hello-from-conan-build-dir            # exit 0
```

### 选型

采用先例 **(a)**（`archives/w/wayland-protocols/1.36.1/conanfile.py::_build_static_scanner`）：
在 `build()` 内从 wayland 1.22.0 源码编译一个**静态链接**（仅依赖 libc）的
`wayland-scanner`，再用它生成三个协议绑定。

关于 expat：任务要求“优先用 Conan expat 依赖里的静态 `libexpat.a`，否则退回先例的
设备路径并给出明确失败信息”。实测 **Conan expat/2.8.2 包内没有 `libexpat.a`**
（只有 `libexpat.so`）：

```
$ find <expat pkg>/ ... -> lib/libexpat.so  lib/libexpat.so.1  lib/libexpat.so.1.12.2   (无 .a)
```

因此退回先例的设备路径 `/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`
（该文件实测存在），并包裹清晰失败信息（`_expat_static()` 两处都没有时抛
`ConanException` 说明原因）。构建日志实测确认为该路径：

```
wayneko/0_git20260326: wayneko: static expat from /data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a
```

### 证据：静态 scanner 在本设备可执行并可用

独立实测（编译静态 scanner 后直接运行 + 生成 wayneko 的三个协议）：

```
$ clang -o wayland-scanner -include config.h -I<wayland-src>/src scanner.c wayland-util.c \
       -I<expat>/include <expat>/lib/libexpat.a -lm -lpthread -static
$ ./wayland-scanner --version
wayland-scanner 1.22.0                # exit 0
$ wayland-scanner client-header < xdg-shell.xml > xdg-shell.h     # 2128 行
$ wayland-scanner private-code  < xdg-shell.xml > xdg-shell.c     # 181 行
（wlr-layer-shell-unstable-v1 / ext-idle-notify-v1 同样成功）
```

`build()` 中同样的步骤在 conan create 内复现成功（见下方日志）。

---

## 构建 / 安装决策

1. **不依赖 pkg-config**：上游 Makefile 用 `pkg-config --cflags/--libs pixman-1`。
   recipe 改为从解析出的 Conan 依赖 package 路径显式构造
   `CC/CFLAGS/LDFLAGS/LIBS` 传给 make（命令行变量覆盖 Makefile 赋值），
   **不裸用 `${CC}` 等 shell 变量**（R33），也不受 wayland/pixman `.pc` 中
   `prefix=/` 的错误影响。
2. **严格按上游编译**：保留上游的 `-Wall -Werror -Wextra -Wpedantic
   -Wconversion -Wsign-conversion -Wfloat-conversion ...`。clang 15 下实测零告警通过。
3. **构建目录隔离**：将 `Makefile / wayneko.c / neko-bitmap.xbm` 复制到
   `build_folder/work/`，协议 `.c/.h` 也生成到该目录，再在该目录运行 make；
   不修改 `source_folder`（R6）。
4. **不注入共享 /usr/local**（R49）：`package()` 用 Python `shutil.copyfile`
   只把产物装进 Conan package 目录。
5. **RPATH**：链接时加 `-Wl,-rpath,<wayland_lib> -Wl,-rpath,<pixman_lib>`，
   使安装后的二进制在 `conanrun` 之外也能直接运行（CI L2 冒烟测试直接执行
   `--help`，见下）。
6. **安装产物**：`bin/wayneko`、`share/man/man1/wayneko.1`、
   `share/bash-completion/completions/wayneko`、
   `share/zsh/vendor-completions/_wayneko`、`licenses/LICENSE`。
   `package_info()` 设 `bindirs=["bin"]`；软件级 `commands.json` 已声明（R38）。

---

## 上游测试清点（R51：上游确无测试，附证据）

清点命令（对下载的发布 tarball 运行）：

```
$ tar tzf wayneko-437a8a708ea68f0288becb047b582e84ef3e412c.tar.gz | sed 's:^[^/]*/::' | sort
LICENSE
Makefile
README
bash-completion
ext-idle-notify-v1.xml
neko-bitmap.xbm
wayneko.1
wayneko.c
wlr-layer-shell-unstable-v1.xml
xdg-shell.xml
zsh-completion
```

核查结论 —— **上游 0 个测试**：

1. tarball 文件清单：**无 `tests/` 目录**，无 `*_test.*` / `test_*.c`。
2. `Makefile` 目标仅有 `wayneko`、`install`、`uninstall`、`clean`，
   **无 `check` / `test` 目标**（`.PHONY: clean install`）：
   `make -n check` → `make: *** No rule to make target 'check'`。
3. **无任何 CI 配置**（无 `.gitlab-ci.yml` / `.github/` / `.build.yml` / `.builds`）。

因此 `test_package/MANIFEST.yml` 中 `upstream_tests: []`，并由本仓库**补充**测试。

---

## 补充测试（两层，均实测）

### 层 1 —— `tests/test_wayneko.c`（`build()` 内，经 `make check` 驱动）

设计：以 `#define main wayneko_cli_main` 把**真实上游 `wayneko.c`** 纳入测试 TU
（未编辑上游源码），直接调用其真实静态函数，断言真实数值/行为：

- `colour_from_hex()`：接受 `0xRRGGBB` / `0xRRGGBBAA`（与独立重算的
  premultiplied 期望 `memcmp` 比较），拒绝长度错误（`0x12345`/`0xFFFFFFF`/…）
  与非 hex（`0xGGGGGG`/`zzzzzzzz`）。
- `get_argument()`：越界返回 NULL 且不推进索引；正常返回后继 token 并推进。
- `colour_from_flag()`：合法 / 缺参 / 畸形 三种返回。
- `atlas_init()`：返回 true，`neko_atlas` 非 NULL，尺寸 == `neko_bitmap_width/height`
  (512×128)，stride == width/8，`atlas_deinit()` 全部释放。
- 动画状态机：`do_stare/yawn/think/shock/sleep/scratch/run_left/run_right` 的
  状态与帧计数、`advance_left/right` 位移、`can_run_left/right` 边界、
  `animation_next_state_with_idle/hotspot` 转换、`animation_next_state` 的
  ticks 递减与 idle 优先级、`timespec_diff`、`animtation_neko_wants_sleep`、
  `buffer_randomize_string` 字符范围、`usage` 文本、默认常量。

实现细节：`tests/Makefile.check` 提供 `check` 目标，编译真实 `wayneko.c`(重命名入口)
+ 3 个生成的协议 `.c`，运行断言驱动；失败非零退出 → `make check` 失败 → conan create 失败。

**实测结果（conan create 日志原文）：**

```
[wayneko] RUN: make -f .../tests/Makefile.check check CC=/data/service/hnp/bin/clang ...
[layer-1] running supplemented wayneko behaviour suite
wayneko layer-1 behaviour suite: 117 passed, 0 failed
wayneko layer-1 behaviour suite OK
[layer-1] make check target completed
```

→ **117 条断言，117 通过，0 失败**（`make ... check` 痕迹亦满足 CI L1c 正则 `make.*check`）。

### 层 2 —— `test_package/`（消费者视角，执行已安装二进制）

`test_package/test.sh` 在 `conanrun` 环境执行**已安装**的 `wayneko`，断言真实退出码
与错误文本：`--help`=0 且列出全部 9 个 flag；未知 flag / `--type bogus` /
缺参数 / 畸形颜色 均非零且给出对应错误；未设 `WAYLAND_DISPLAY` → `WAYLAND_DISPLAY
is not set`；`WAYLAND_DISPLAY=nonexistent` → `Can not connect to wayland display`。

**实测结果（conan create 日志原文）：**

```
wayneko/0_git20260326 (test package): RUN: /data/service/hnp/bin/bash ".../test_package/test.sh"
[test] wayneko binary: /storage/Users/currentUser/.conan2/p/b/wayne0d075f1b99c36/p/bin/wayneko
... (23 行 [ok]) ...
[test] test_package assertions: 23 passed, 0 failed
[test] test_package PASS
```

→ **23 条断言，23 通过，0 失败**。

### R34 / CI L1e 反向验证（实测）

把 package 的 `bin/` 移走后重跑 `conan test`：

```
$ mv <pkg>/bin <pkg>/bin.bak
$ conan test .../test_package wayneko/0_git20260326 -pr <profile> --build=missing
[test] test_package assertions: 6 passed, 17 failed     # 17 条因缺二进制而失败
exit=1                                                  # → 证明 test 真实依赖被测包
$ mv <pkg>/bin.bak <pkg>/bin                            # 恢复
```

---

## 鸿蒙特有测试（层 3 —— `test_package/test_wayneko_ohos.c`，规则 12 要求）

为满足赛事规则「鸿蒙特有测试至少一项」，新增 OHOS 平台级消费者测试：

- **编译守卫**：`#ifndef __OHOS__ #error` —— 仅在 OHOS 目标构建（OHOS SDK clang
  预定义 `__OHOS__`，非 OHOS 编译直接 #error，防止误用）。
- **测试内容（12 断言，对已安装的 `bin/wayneko` 做 ELF 级平台断言）**：
  - 合法 ELF64 / 小端 / `EM_AARCH64` / `ET_DYN`（PIE）—— 验证 OHOS armv8 产物形态；
  - `PT_INTERP`（动态链接）、NX（非可执行栈）、RELRO —— OHOS 安全基线；
  - `DT_NEEDED` 含 `libwayland-client` 与 `libpixman-1` —— 验证 Conan 依赖链已嵌入产物
    （R26 系统同名库隔离的产物级佐证）；
  - **无 glibc 专属 `backtrace` / `backtrace_symbols_fd` 未定义符号** —— 直接验证
    wayneko.c 中 `#ifdef __GLIBC__` 鸿蒙移植守卫真实生效（OHOS 为 musl 系，不提供 execinfo）。
- **接入**：`test_package/conanfile.py` 在 `os==OHOS` 时用 Conan 工具链 clang 编译，
  `binary-sign-tool` 自签名（cubature 先例），`test()` 中以安装后的真实二进制路径运行。

**实测结果（conan create 日志原文）：**

```
[wayneko] RUN: /data/service/hnp/bin/clang -O2 -std=c11 -o .../test_wayneko_ohos .../test_wayneko_ohos.c
wayneko: built OHOS-specific consumer test
[wayneko] RUN: ".../test_wayneko_ohos" ".../p/bin/wayneko"
  [ok]   ELF header fits in file
  ... (12 行 [ok]) ...
wayneko OHOS-specific consumer test: 12 passed, 0 failed
```

→ **12 条断言，12 通过，0 失败**（真实函数/真实产物，非空壳）。

---

## 精确执行命令与结果

```
# 预检 / 语言预检
bash ci/scripts/preflight_check.sh wayneko/0_git20260326
python3 scripts/ohc-run.py lang-preflight wayneko 0_git20260326 --src <src>

# 编译验证（CI 同源：host=build=ci/conan/profiles/ohos-aarch64）
conan create archives/w/wayneko/0_git20260326 \
     -pr:h=$REPO/ci/conan/profiles/ohos-aarch64 \
     -pr:b=$REPO/ci/conan/profiles/ohos-aarch64 \
     --build=missing
# -> exit 0

# 关键日志行
wayneko layer-1 behaviour suite: 117 passed, 0 failed
[test] test_package assertions: 23 passed, 0 failed
wayneko/0_git20260326: Package folder /storage/Users/currentUser/.conan2/p/b/wayne0d075f1b99c36/p

# 安装产物直接运行（RPATH 生效，无需 LD_LIBRARY_PATH）
$ /storage/Users/currentUser/.conan2/p/b/wayne0d075f1b99c36/p/bin/wayneko --help
Usage: wayneko [options...] ...      # exit 0
```

---

## 已知限制

- wayneko 是图形客户端，需运行中的、实现了 `zwlr-layer-shell-unstable-v1` 的
  Wayland 合成器才能实际绘制；CI/无头环境无法验证真实画面，测试只覆盖 CLI 行为、
  颜色解析、图集创建与动画状态机（真实函数、真实断言）。
- `wayland-scanner` 静态编译依赖设备提供的
  `/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`（Conan expat 包无静态库）。
  若该路径在未来 CI worker 上不存在，`_expat_static()` 会以明确信息失败，需改回
  用 expat 源码自行编译静态库（不影响依赖链完整性，仅 scanner 工具构建）。
---

**编译结束**: 2026-09-14 02:37
**最终状态**: built
