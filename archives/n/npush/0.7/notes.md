# npush 0.7 适配笔记（HarmonyOS PC / aarch64-ohos）

## 编译环境
- 软件形态：ncurses 全屏逻辑游戏（CLI 工具 / application），上游发行 tar.gz 含单文件
  C++ 源码 npush.cpp + levels/ 关卡数据
- 官方源：https://npush.sourceforge.net/ （SourceForge 项目 npush）
  - 源码包: https://downloads.sourceforge.net/project/npush/npush/0.7/npush-0.7.tgz
  - sha256: f216d2b3279e8737784f77d4843c9e6f223fa131ce1ebddaf00ad802aba2bcd9
    （与 Homebrew formula、FreeBSD ports distinfo 记录一致）
- 构建系统：plain Makefile（无 configure；Makefile 硬编码 g++ / -lncurses，无 install 目标，
  上游无任何测试套件：无 make check / ctest / pytest）
- 依赖：ncurses/6.4（ohpcd 制品仓，含 aarch64-ohos 预编译制品）
- 编译器：clang/clang++ 15.0.4（aarch64-unknown-linux-ohos），Conan profile ohos-aarch64
- 日期：2026-09-04；状态：built

## 编译步骤（conan create 实际执行）
1. conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...（test_package 一并执行）
2. source(): conan get 从 conandata 官方 URL 下载 npush-0.7.tgz（sha256 校验），strip_root 解包
3. build(): 用 Conan conf 提供的编译器 tools.build:compiler_executables["cpp"] 直接编译单 TU：
   `clang++ -O2 -Wall -DNDEBUG -I<ncurses include> npush.cpp -L<ncurses lib> -lncursesw -o npush`
   - 不使用上游 Makefile 的原因：Makefile 链接行硬编码 `-lncurses`（本制品仓只有宽字符
     静态库 libncursesw.a），且无 install 目标；直接编译单文件与 alex4/nsnake 先例一致。
   - ncurses/6.4 为宽字符静态包，头文件含 ncurses.h，链接 -lncursesw（R26 系统同名库隔离）。
4. package(): 真实二进制 + levels/ + readme + COPYING 装到 share/npush/；bin/npush 为
   POSIX launcher（cd 到 share/npush 后 exec ./npush）。原因：npush 从 CWD 读 levels/
   （opendir("levels")），launcher 方式与 Homebrew npush formula 同构，保证包可重定位。
5. 上游测试：无（上游零测试，见 test_package/MANIFEST.yml 与 reports/test-report.md）
6. test_package：functional_test.py 用 python pty 起游戏，验证主菜单渲染 + Down/Down/Enter
   走 Quit 干净退出(exit 0)，真实调用被测二进制与 ncurses（R34/PF3）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游官方源仅在 SourceForge 分发；本机对 downloads.sourceforge.net 被 Cloudflare
  challenge 拦截（403，curl/python 均无法下载） | 源站风控/网络 | W3/本地 conan create 期间用
  **字节级一致**的本地镜像（sha256 与官方一致，已核对 Homebrew/FreeBSD 记录）替代；提交的
  conandata.yml 保持官方 URL（CI 环境可直连/有镜像）。本文件 conandata 官方 URL 为最终交付。 |
| 2 | 上游 Makefile 硬编码 g++/-lncurses 且无 install | 2008 年单文件小游戏 | conan build 直接
  单文件编译，链接 ncursesw（同 nsnake 先例） |
| 3 | headless（无 TTY）运行 initscr 失败退出码 1，无法做 --version 式冒烟 | 全屏 ncurses 程序 |
  test_package 改用 pty 交互测试：菜单渲染→Quit→exit 0（真实功能） |
| 4 | pty 内方向键无效 | 本 terminfo(xterm-256color) 应用光标键序列为 \EOB（非 \E[B） |
  functional_test.py 发送 \x1bOB |
| 5 | conan test 中 ncurses 的 TERMINFO runenv 未传递（test 包仅直连被测包） | conanrun 聚合仅覆盖
  直接依赖 | test_package 直接 requires ncurses/6.4，令 TERMINFO 进入 conanrun 环境 |
| 6 | W3 L0k：CLI 工具缺软件级 commands.json（commands_json_r38） | R38 要求 tool 包软件级
  commands.json，而 PF9 禁止功能分支 PR 含软件级文件（深度 4） | 磁盘上建
  archives/n/npush/commands.json 供本地 W3/PF8 通过；**不入 PR**，按 tlrc 惯例由主编合并后
  在 main 补挂。 |

## 依赖版本
- ncurses/6.4（ohpcd remote + 本地缓存；W0 已用 conan download --only-recipe 实测配方存在，
  conan list 实测含 armv8/clang15/Release 二进制）

## 验证结果
- conan create（本地 W3 同源）exit 0；conan-verify 8 门禁 G0-G4/L2/L4/L5 全 PASS；
  build_and_test.sh 本地 CI 模拟 PASS（.ci-result.json exit_code=0）
- test_package 实测输出：
  `OK: npush menu rendered and Quit exited cleanly (seen=True, rc=0)`
- 上游测试 0 项（源码无测试文件；Makefile 无 check 目标）；test_package 功能性断言 3 项。

## 交付物
- conanfile.py / conandata.yml / manifest.yaml / notes.md / test_package/（conanfile.py、
  functional_test.py、MANIFEST.yml）；patches/ 为空（无源码补丁，wrapper 方案不改源码）。
- .ci-result.json（W3 自动写入，exit_code=0 + log_sha256）
- 软件级 commands.json（磁盘存在，供 PF8/W3 L0k 检查；**不在本 PR**——PF9 分支路径闸，
  主编合并后 main 直推，同 tlrc 1.13.1 惯例 commit `4af85698b6`）

## 注意事项
- 本包为纯应用（ncurses 游戏），无库产物 → 不需要 cpp_info.libs。
- launcher 依赖 POSIX sh（OHOS 提供 /bin/sh）。
- 游戏需真实终端运行；commands.json 声明 type=tool/binary=true（运行 npush 需交互终端）。

---

**编译结束**: 2026-09-04 02:35
**最终状态**: built
