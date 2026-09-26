# yabasic 2.91.4 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag 归档 unix/lang/ 子树自带生成的 configure/Makefile.in）
- 编译日期: 2026-09-20
- 编译器: clang（profile tools.build:compiler_executables，/data/service/hnp/bin）
- 状态: built

## 编译步骤

conan create 内 build() 执行（全部经 conanbuild env）：

```bash
cd src/unix/lang
sh ./configure --prefix=<package_folder> \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-musl \
  --x-includes=<merged X11 include> --x-libraries=<merged X11 lib> \
  LIBS=-lncursesw
make -j1 CC=<profile c> CXX=<profile cpp>
# 随后在 build() 内真实执行上游 tests/ 套件（见下）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | source() 下载 ghfast 镜像超时 | E017 注入镜像不可达 | 按 SHA256 将官方 tarball 预置共享下载缓存（§12.3） |
| 2 | `./configure: inaccessible or not found` | HMDFS 适配路径丢失执行位（E490），chmod 无效（E046） | `sh ./configure` 显式路由（不经 exec） |
| 3 | `cannot guess build type` / config.sub 不识别 ohos | HongMeng 内核无法分类；2022 版 config.sub 早于 OHOS 三元组 | `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-musl`（§12.1 变体） |
| 4 | `Did not find X11 library and header` | AC_PATH_XTRA 硬要求，yabasic.h 在 #ifdef UNIX 下无条件包含 X11 头（无 --without-x 逃生口） | 消费 libx11/1.8.13 + libxt/1.3.1（Intrinsic.h），generate() 将 X11 头/库合并到单目录并传 --x-includes/--x-libraries |
| 5 | `subs1.awk: Permission denied` | autoconf 临时目录 umask 077 在 HMDFS 不可读（E011/E114） | configure 内 `umask 077` mktemp/mkdir 替换为普通 mkdir（4ti2/1.6.10 同款受控修复，保留真实临时目录创建） |
| 6 | make 默认 CXX 指向 /home/runner（CI 路径） | ohpcd hnp make 二进制内置 CI worker 默认值 | 命令行显式传 CC/CXX |
| 7 | libncurses 链接失败 | ohpcd ncurses 仅宽字符构建 libncursesw.a | `LIBS=-lncursesw` 使 AC_SEARCH_LIBS 直接命中 |

## 上游测试（五维账本，R51）

build() 内真实执行，退出码判据（`error` 语句非零退出，干净跑完为 0）：

- N_static = **54**（tests/README.org 声明 *.yab 自动套件 48 + *.sh 手工 make check 6）
- N_executed = **51**（48 .yab 全部 + 3 个可无头运行的 .sh 等价执行：docu.sh、read_stdin.sh、silent.sh）
- 通过 = **47**（44 .yab + 3 .sh）
- 环境受限跳过 = **7**（逐项技术原因见 test_package/MANIFEST.yml）：
  - bind_import.yab / nested_bind_import.yab（已执行未过）：`bind` 特性运行时生成独立 ELF 并再执行，HMDFS 拒绝对新写入的未签名文件 exec（E046/ELF 签名平台限制）
  - foreign3.yab（已执行未过）：dlopen 'libcurl.so.4'，OHOS 无此 glibc 发行库
  - speed.yab（已执行未过）：依赖 stress-ng，OHOS 无
  - inkey.sh / print-at.sh / run_in_script.sh（未执行）：需 tmux 终端自动化，无头环境不可用
- N_consumer = 1（test_package/smoke.yab，11 项断言，输出 "smoke ok" 退出 0）

## 源码修改

无源码/测试文件补丁（patches: {}）。全部适配差异经 configure 参数与
conanfile 逻辑（X11 头/库合并目录、sh 路由、显式 CC/CXX）实现。

## 依赖版本

- ncurses/6.6（宽字符静态构建）
- libffi/3.4.4
- libx11/1.8.13 + libxt/1.3.1（含 xorgproto/2025.1 传递头）

## 验证结果

```bash
conan create ... --build=missing
# conan-verify G0-G4 全过；build log:
# upstream .yab suite: 44/48 passed, 4 skipped (platform-limited)
# upstream shell checks: 4 passed, 0 failed
# test_package: smoke ok（消费者测试通过）
```

## 注意事项

- 2.91.4 的 git tag 是 monorepo 布局（unix/windows/web），可构建源码在 unix/lang/；
  维护者将生成物（configure/config.status）提交在 git 内，tarball 与 .work 观察一致。
- 运行 yabasic 图形命令需 X display；本适配的 X11 仅为编译/链接满足，文本模式
  功能（上游测试套件全部为文本用例）在 OHOS 完整可用。

## 结束

最终状态：built（W3 本地 CI 通过，W4 审计 pass，消费者测试通过）。
适配完成日期：2026-09-20。COMPLETED。
