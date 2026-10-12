# ptunnel 0.72 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure / autotools）
- 编译日期: 2026-10-07（前置适配阶段，本机未编译，待真机预检）
- 编译器: clang（配方从 `tools.build:compiler_executables` 获取）
- 状态: built（待真机 conan create + test_package 全绿后由 finish 更新 published）

## 上游信息

- 官方主页: https://www.cs.uit.no/~daniels/PingTunnel/
- 源码归档: https://www.cs.uit.no/~daniels/PingTunnel/PingTunnel-0.72.tar.gz
  sha256 `b318f7aa7d88918b6269d054a7e26f04f97d8870f47bd49a76cb2c99c73407a4`
  （2026-10-07 计算；tar 顶层目录 PingTunnel/）
- 许可证: BSD-3-Clause（LICENSE 为 3-clause BSD）
- 功能: 利用 ICMP echo request/reply（ping）报文把 TCP 连接可靠隧穿到远端主机的
  命令行工具（客户端 `-p/-lp/-da/-dp` 与代理双模式，单二进制 `ptunnel`）
- 语言: C（ptunnel.c + md5.c/md5.h，RFC 参考 MD5 实现；含 selinux/redhat/web 打包支持）
- 版本: 0.72（man 页 "Version 0.72"，usage 打印 "ptunnel v 0.72."）

## 依赖关系（W0 依赖发布检查）

ptunnel 需要 libpcap（抓包核心，`-lpcap`）与 pthread（系统 libc 提供）。
- 制品仓已有 `libpcap/1.10.6`（archives/l/libpcap/1.10.6，status=published，
  cpp_info.libs=["pcap"]）。配方 `requires("libpcap/1.10.6")`。
- pthread：OHOS 由 libc 提供，`-lpthread` 直接可用。
- selinux：仅当系统中存在 `/usr/include/selinux/selinux.h` 时上游才加
  `-lselinux`/`-DHAVE_SELINUX`；OHOS 无 selinux 头，该分支自然不启用。

## 上游测试清点（R51 / 硬门禁）

上游 0.72 发布包 Makefile 仅定义 `all/dist/ptunnel/ptunnel.exe/clean/depend/install`
目标及 `%.o:%.c` 模式规则，**无 check/test/TESTS/check_PROGRAMS 目标，无 tests/ 目录，
无任何测试框架/CI 配置**。md5.c 头部注释的 "test program" 仅为 RFC 源码注释，非可运行
测试。结论：上游确实没有任何自动化测试（`upstream_tests_exist: false`，
`upstream_test_total: 0`），test_package 以 -h 冒烟验证替代（consumer 视角）。

## 编译步骤（配方设计）

```sh
# 纯 Makefile，无 configure；CC 命令行变量优先覆盖 Makefile 内 "CC = gcc"
# 关键：ptunnel Makefile 的编译规则用 $(CFLAGS)、链接规则用 $(LDOPTS)，
# 从不引用 CPPFLAGS/LDFLAGS —— 因此 pcap 头路径注入 CFLAGS、库路径注入 LDOPTS：
make CC="<conan conf 编译器>" \
     CFLAGS="-Wall -g -I<pcap_include> -I<pcap_include>/pcap" \
     LDOPTS="-L<pcap_lib> -lpthread -lpcap" -j1
# 不调用 make install（依赖 coreutils install），package() 手动复制
# ptunnel → bin/，ptunnel.8 → share/man/man8/，LICENSE → licenses/
```

两处 make 规则内 `[ -e /usr/include/selinux/selinux.h ] && echo ...` 命令替换在
OHOS 上为 false 分支，不影响构建。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CC = gcc` | 纯 Makefile 工具无 configure 可注入 CC | make 命令行变量 `CC=clang`（优先于 Makefile 内赋值），编译器取 self.conf |
| 2 | ptunnel.h `#include <pcap.h>` | libpcap 头安装于 include/pcap/pcap.h | CFLAGS 加 `-Iinclude` 与 `-Iinclude/pcap`，令 `<pcap.h>` 解析 |
| 3 | `-lpcap` 定位 | conan 缓存 libpcap | LDOPTS 前加 `-L<pcap_lib>`（其前保留 -lpthread -lpcap） |
| 4 | 上游 `make install` 用 coreutils `install` | 明文 install 在 OHOS 上可移植性不确定 | package() 手动 copy2 + chmod 755，附带 man 页与 BSD 许可文本 |

> 待真机预检补充：musl/OHOS 头文件兼容性（如 `<net/ethernet.h>`、`<sys/unistd.h>`、
> 旧的 BSD 类型 u_char 等）以真机 clang 首编实际报错为准，必要时以 POSIX 兼容方式
> 在 patches/ 修复（不会走 `__OHOS__` 平台宏，遵循 R8/PF5）。

## 依赖版本

- libpcap/1.10.6（制品仓已发布，static）

## 验证结果

```text
本机（前置阶段，2026-10-07）：
- sha256 计算与 tar 内容核对 ✅
- conanfile.py / test_package 语法静态检查 ✅（py_compile + yaml 解析）
- 上游构建/测试源码级走查（Makefile 目标、-h usage 路径、pcap 依赖）✅

待真机（HMBS 预检，HarmonyOS aarch64）：
- conan create（ohos-aarch64 profile，clang）＋ test_package 冒烟 2/2
- 完成后回填真实日志与通过率
```

## 下一步真机/CI 命令

由 HMBS 后台在真机执行 conan create + rule4 门禁；通过后由 HMBS 统一提交推送。

## 注意事项

- 本包为 application 类型（CLI 工具）：软件级 `commands.json` 已按 R38 声明
  （type=tool，commands=["ptunnel"]）。
- 完整隧穿需 root + 抓包设备 + 实时 ICMP 网络，构建沙箱无法覆盖；功能验证限于
  -h usage 冒烟（proves 二进制可执行、动态依赖可解析、为真实 ptunnel）。
- 预计构建耗时 <1 分钟（2 个 .c），无需 timeout set。

## 轮次日志（HMBS 真机预检）

### 2026-10-10 轮：编译失败 `sys/unistd.h` not found（配方新增补丁修复）
- 真机失败：`./ptunnel.h:48:13: fatal error: 'sys/unistd.h' file not found`，阶段=compile。
- 根因：ptunnel.h 第 48 行 `#include <sys/unistd.h>` 是非可移植头文件路径——该头既不存在于
  OHOS(musl) 也不存在于 Linux glibc；unistd.h 的标准路径是 `<unistd.h>`，且同文件更下方已经
  `#include <unistd.h>`。此 include 对编译完全冗余，故移除。
- 修复：新增 `patches/0001-ptunnel.h-sys-unistd.patch`，删除该冗余 include；conandata.yml
  声明该 patch（portability 类），配方 build() 已有 apply_conandata_patches 生效。非 OHOS
  平台宏，遵循 R8/PF5。
- 核对：全树仅 ptunnel.h 引用 sys/unistd.h（ptunnel.c/md5.c 无），补丁 git apply --check 通过。

### 2026-10-08 轮：瞬时资源告警（非配方缺陷，未改配方）
- 真机失败：`preflight.sh[319]: /usr/local/bin/head: Out of memory` /
  `preflight.sh[319]: can't fork - try again`，阶段=compile。
- 证据定位：失败在 HMBS 预检编排脚本 preflight.sh 的 319 行 fork 系统工具
  `/usr/local/bin/head` 时报 OOM / can't fork；属编排层瞬时进程/内存耗尽。
  stdout 仅到 preflight 初始化（PKG_DIR/CONAN_HOME/锁槽/平台能力），后无任何
  conan create / 编译器输出，ptunnel 编译根本未启动。
- 配方侧核对：ptunnel 配方全树不调用 `head`/`/usr/local/bin/head`（仅注释提及
  "headers under include/pcap/"），无进程膨胀点：-j1 串行、/bin/sh 直驱 make、
  依赖钉 libpcap/1.10.6 预编译制品避免源码重编。
- 结论：按共享真机瞬时资源/会话/基础设施告警处理，不做伪造配方改动，保持已
  验证配方不变，等待环境恢复由 hmbs 自动复跑。

### 2026-10-10 轮：test_package 缺少 HMBS 机器证据标记（incomplete）
- 真机失败：HMBS 判定 test_package 阶段 incomplete——"缺少 test_package 真实用例计数和
  机器测试证据"；preflight stdout 已真实运行 test_ptunnel.sh，输出 "RESULT: 2 passed,
  0 failed"，但脚本未输出任何 `HMBS_TEST_PACKAGE_RESULT={...}` 单行 JSON，上游侧也未
  复发行 `HMBS_UPSTREAM_TEST_RESULT=no_tests` 标记。
- 根因：test_ptunnel.sh 只打印人类可读的 `RESULT:` 行，没有门禁要求的机器证据标记；
  test_package/conanfile.py 的 test() 在跑完脚本后也未按 no_tests 口径复发行上游标记。
- 修复：
  1. test_ptunnel.sh 末尾新增单行独立 `HMBS_TEST_PACKAGE_RESULT={"executed":true,
     "passed":<bool>,"command":"test_ptunnel.sh <pkg_bin>","discovered":<run_count>,
     "passedCount":<pass_count>}`——discovered 取脚本内 check_pass/check_fail 的
     run_count（确定性计数，非硬编码），passedCount 取 pass_count，两值同源，满足
     passed+failed==executed==discovered 恒等式；不再包外层复合 JSON（避免门禁解析失败）。
  2. test_package/conanfile.py 增加 `import json`，在真实运行 test_ptunnel.sh 之后用
     json.dumps 复发行 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",
     "command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":...}`
     ，reason 引用 MANIFEST.yml 的 upstream_test_audit 审计结论。
- 本地实测：假 ptunnel 二进制（-h 打印 Usage: + ptunnel v 0.72. 并 exit 1）运行脚本输出
  `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":2,"passedCount":2}`
  ；缺失二进制时输出 passed=false/discovered=1/passedCount=0（恒等式成立）；conanfile
  py_compile 通过。
- 经验关联：对标 kicad-packages3d/10.0.3 的 test_package 标记一致性修复（经验 1/2）。


### 2026-10-10 轮：no_tests/0 被证据门禁拒绝（清单误判上游存在测试 → 结构化审计修复）
- 真机失败：evidence 阶段 incomplete，理由「清单表明上游存在测试，no_tests/0 不允许通过」；
  HMBS_UPSTREAM_TEST_RESULT 已如实输出 status=no_tests、discovered=0/executed=0/passed=0，
  test_package 冒烟 2/2 PASS。
- 根因：test_package/MANIFEST.yml 的 `upstream_check_command` 为非空字符串
  `"none (upstream Makefile has no check/test target)"`，且 `upstream_test_audit` 是扁平
  path/finding 列表。hmbs 清单器把「非空 check/test 命令」判为「上游存在测试」，于是
  no_tests/0（零证据）被拒。ptunnel 上游确实无测试（Makefile 仅 all/dist/ptunnel/
  ptunnel.exe/clean/depend/.depend，无 check/test/TESTS/check_PROGRAMS/check-local；
  无 tests/ 目录、find *test* 零命中；无 demo/）——属 paperjam/sipcalc/audacious 型
  真·no_tests 误判，非 ccrtp 型 demo 提升。
- 修复（对标 osmctools/sipcalc 结构化 no_tests 审计）：
  1. MANIFEST.yml `upstream_check_command: ""`、`upstream_test_command: ""` 置空串，
     消除清单器「上游存在测试」误判。
  2. `upstream_test_audit` 改写为结构化机器可解析映射：source_tarball /
     source_sha256(b318f7...) / top_level_files / scanned_for / scan_result /
     make_check_output(No rule to make target 'check') / reason。
  3. 保留 `upstream_tests_exist: false`、`upstream_test_total: 0`、
     `upstream_test_count_method: none`（真·无测试，非子集）。
  4. conanfile.py 上游标记已为 framework:none、command:""（无需改）；test_package
     冒烟 2/2 为新增消费者验证，不属于上游计数。
- 经验关联：DRAFT-paperjam（非空 check 命令致 no_tests 误判 → 空串 + 结构化审计）；
  DRAFT-sipcalc/osmctools（结构化审计同款格式）；DRAFT-ccrtp（demo 提升）不适用——
  ptunnel 无 demo 目录，走结构化 no_tests 路径。
