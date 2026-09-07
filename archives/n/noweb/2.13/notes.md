# noweb 2.13 适配笔记

## 软件概述
noweb 是 Norman Ramsey 的文学编程工具集（C 语言 + shell/awk 管道）。命令：
`noweb` / `notangle` / `noweave` / `nountangle` / `noroots` / `nodefs` /
`nuweb2noweb` / `cpif` / `htmltoc` / `noroff` / `noindex`。
构建系统为纯 GNU Make（无 configure），在 `src/` 下 `make boot && make all`，
安装命令为 `make install-code BIN=… LIB=…`（bin 放公共 wrapper，lib/noweb 放
C 管道件与 shell/awk 碎片）。

## 编译环境
- 平台: HarmonyOS PC (aarch64 / OHOS), kernel HongMeng
- 编译器: clang 15.0.4（target aarch64-unknown-linux-ohos）
- 工具: GNU make 4.4.1, gawk 5.4.0, conan 2.29.1（OHOS 适配版）
- 上游源码: https://github.com/nrnrnr/noweb/archive/refs/tags/v2_13.tar.gz
  （sha256 7b32657128c8e2cb1114cca55023c58fa46789dcffcbe3dabde2c8a82fe57802）

## 编译步骤
```bash
# 1. 解压后在 src 下构建（boot 更新时间戳避免自举）
make CC=clang boot
make CC=clang all
# 2. 安装到 staging prefix（install-code 即可，避开 install-man 的 ln 硬链接）
make CC=clang install-code BIN=<prefix>/bin LIB=<prefix>/lib/noweb ELISP=/dev/null
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 安装后的 C 工具（nt/markup/mnt/finduses）执行报 `Operation not permitted`(126) | src/Makefile install-code 对 C 二进制执行 `strip`；本平台 strip 后的 ELF 无法执行（被 loader 拒绝，EPERM） | patch 0001：去掉 install-code 中的 strip 步骤，保留未裁剪二进制 |
| 2 | `noweb -t`/`noweave -index` 报 `Calling tmpfile() failed` | mnt.c / finduses.c 调用 libc tmpfile()，固定写 /tmp；OHOS 的 /tmp 是只读 erofs | patch 0006/0007：新增 TMPDIR 感知的 nw_tmpfile()（mkstemp+unlink+fdopen，$TMPDIR 缺失回落 cwd），替换两处 tmpfile() |
| 3 | 工具报 `nawk: inaccessible or not found` | 分发脚本引用 `nawk`，本平台只有 awk=gawk（无 nawk） | 按上游 INSTALL 运行 `./awkname awk`（patch 0002-0005, 0008-0012, 0015, 0024 固化改名结果） |
| 4 | conan L2 smoke 门禁要求 `--version`/`--help` | 上游 wrapper 只认 `-gitversion` | patch 0013-0023：给各 bin wrapper 增加标准 --version/--help 早退处理（htmltoc 为 perl 混排，须在 perl 段内处理） |
| 5 | install-man 中 `ln notangle.1 noweave.1` 报 Operation not permitted | HMDFS 文件系统不允许硬链接 | 不运行 install-man（仅 install-code 打包 bin+lib/noweb 功能件），不在归档结构内引入硬链接 |
| 6 | make check 不存在 | 上游 v2_13 GitHub tag 内 test/regression 目录为空，无 check/test 目标 | 用真实 .nw 文件做功能回归（notangle 展开 hello.nw→C、编译运行；noweb -t 展开命名根块；noweave/noroots/nodefs 织出结果），记录于 test_package/MANIFEST.yml |
| 7 | weave 管道 `awk: bad regex '{'`（toybox awk） | 本机非 GNU awk（toybox）不兼容 noweb 的 awk 正则；上游要求 GNU awk | 运行时需 GNU awk（同上游 INSTALL）；test_package 探测 `awk --version` 为 GNU 才跑 weave 类断言；纯 tangle 路径不依赖 awk |
| 8 | conan L2 冒烟 htmltoc --version 失败（non-blocking warn） | htmltoc 是上游无 shebang 的 sh+perl polyglot：subprocess execvp 直接执行报 ENOEXEC/127（无 shell 回退）；且运行依赖 perl（conan test 环境 PATH 无 perl） | 属上游工具限制，保留上游 polyglot 语义（shell 内调用正常）；patch 0014 已在 perl 段加 --version/--help（shell 调用路径生效），未再改动；L2 为 10/11 通过 + htmltoc warn，门禁 PASS |
| 9 | wrapper 内嵌绝对 LIB 路径 | 上游按系统安装设计（BIN/LIB 绝对路径），conan 包内不可重定位 | conanfile package() 把已安装 wrapper 的 `LIB=<绝对路径>` 改写成 `$0` 相对解析（bin→../lib/noweb，lib→自身目录） |

## 依赖版本
- 无外部 Conan 库依赖（C 部分仅标准 C 库；运行时 weave/index 需要 GNU awk，纯 tangle 不需要）。

## 验证结果
- 探索编译：make boot/all/install-code 全绿（clang, -ansi -pedantic -O -Wall -Werror 无告警）。
- 功能回归：notangle hello.nw 展开 C 并 clang 编译运行输出 “hello noweb”；noweb -t demo.nw 产出 demo.c；
  notangle -Rdemo.c 与 noweb -t 输出一致；noweave -t / -index 织出 TeX；noroots 列出根块；nodefs 通过。
- conan-verify：G0-G4 + L2/L4/L5 全 PASS；本地 W3 conan create 通过。
- **test_package 三级断言（口径说明）**：
  - C 核心断言 5 项（notangle --version / noweb --version / notangle hello.nw 展开含 main+printf /
    noweb -t demo.nw 产出 demo.c / notangle -Rdemo.c）——纯 C 管道（markup/nt/mnt），**conan 环境恒跑并通过**；
  - weave/xref 断言 3 项（noroots / noweave -t / nodefs）——依赖 GNU awk（上游 INSTALL 要求），
    仅当 PATH 存在 GNU awk 时执行。本机带 gawk（/data/service/hnp/bin/awk=gawk）验证 **8/8 全过**；
    conan create 环境 PATH 无 GNU awk，实际执行 5 项 C 核心断言并全部通过
    （conan-create.log 内可见 “GNU awk not found on PATH — skipping weave/xref checks”）。
  - **鸿蒙化消费者用例 1 项**（build_consumer.sh，由 test_package build() 以 conanrun+conanbuild 执行）：
    notangle tangle hello.nw → 鸿蒙工具链 clang 编译 hello_ohos → test.sh 在本机(OHOS)运行产物
    断言输出 “hello noweb”——覆盖鸿蒙开发者“noweb 产出 → 鸿蒙构建 → 鸿蒙运行”完整消费闭环。
    本机验证全量 **9/9** 通过。

## 交付物
- conanfile.py（Make 驱动，CC 取自 conan toolchain conf，staging prefix 私有化 + wrapper 可重定位改写）
- conandata.yml（官方 URL + sha256 + 24 个补丁）
- test_package/{conanfile.py,test.sh,build_consumer.sh,hello.nw,demo.nw,MANIFEST.yml}
- patches/0001~0024（strip 去除 / tmpfile→TMPDIR / nawk→awk / --version--help）
- commands.json（软件级，type=tool）

## 注意事项
- OHOS 平台不得对产物执行 strip（否则不可执行）；由 CI sign 流程负责签名。
- 本包为“命令行工具”型（R38），无库/头文件，package_info 只暴露 bin/ 到 PATH。
- wrapper 可重定位改写后，bin 与 lib/noweb 必须保持相对布局（package 内 bin/ + lib/noweb/）。
- weave/index 类命令（noweave -index、noindex 等）运行时需要 GNU awk（同上游 INSTALL）；
  纯 tangle（notangle / noweb -t）为 C 实现，不依赖 awk。
- htmltoc 为上游 sh+perl polyglot：运行时需要 perl，且无 shebang（直接 execvp 会 ENOEXEC，
  只能经 shell 调用，属上游设计）。已在 perl 段加 --version/--help；目标环境无 perl 时该工具不可用（上游工具限制）。
---

**编译结束**: 2026-09-04 13:37
**最终状态**: built
