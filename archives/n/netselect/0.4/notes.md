# netselect 0.4 适配笔记

## W0 依赖结论

- 上游: https://github.com/apenwarr/netselect （Avery Pennarun，改编自
  4.4BSD traceroute，tag `netselect-0.4`）
- 许可证: BSD-3-Clause（license 文本位于 netselect.c 头部；FreeBSD ports
  同样登记 BSD3CLAUSE）
- 语言/构建: 单文件 C（netselect.c，约 1100 行），纯 Makefile，无
  configure/cmake/meson
- 依赖数量: 0（仅 libc；raw socket 为运行时内核能力，非链接依赖）
- 已满足依赖: 无需任何 Conan 依赖
- 缺失依赖: 无
- 是否需要拆分依赖适配: 否
- 运行时约束: 需要 raw ICMP/UDP socket（root 或 setuid）。上游 Makefile
  install 即 chown root + chmod u+s；Conan 包不设 setuid（E087：HMDFS 上
  chmod 语义不可靠），由部署侧自行授权。

## 源码与构建分析（W1）

- Makefile 极简：`netselect: netselect.o`，`CC = gcc` 硬编码但可被命令行
  `CC=` 覆盖；CFLAGS 默认 `-O2 -Wall -I. -g`。
- 平台相关点审计:
  - 仅 Linux 路径（作者自述 "I expect this to only compile on Linux"）。
  - `#if !defined(__GLIBC__)` 分支在 musl/OHOS 下走 `int fromlen`（与
    glibc 的 socklen_t 等宽，aarch64 上 ABI 兼容，仅 -Wall 警告，无需补丁）。
  - 头文件均为 musl 提供的标准 BSD 网络头；自带 netinet/{ip,ip_icmp,udp}.h
    仅在系统头缺失时经 `-I.` 兜底。
  - setuid(getuid()) 主动降权、getopt、gettimeofday、select 均为 musl
    支持的 POSIX 接口。
  - 无 32 位假设、无 glibc 专有扩展（getpass/secure_getenv 等均未使用）。
- 上游测试: 无自动测试（无 tests/、无 make check、无框架）。手工验证方式
  为 root 运行 `./netselect -vv host...`。
- 打包口径（与 FreeBSD ports net/netselect 一致）: bin/netselect +
  share/man/man1/netselect.1。netselect-apt 为 perl 脚本且硬编码 Debian
  mirrors 列表，不随包分发。

## 源码归档

- URL: https://github.com/apenwarr/netselect/archive/refs/tags/netselect-0.4.tar.gz
- SHA256: ae343991c94b1fdeb5e7896bb11d357c1dd9297f5d842c507953f57935e15e19
- 本机下载经 ghfast.top 镜像与 macports distfiles 双通道，哈希一致（E017）。
- 归档含 Makefile、netselect.c、man 页、netselect-apt（perl）、HISTORY/README。

## test_package 设计

上游无自动测试，test_package 以确定性"pre-socket 代码路径"为消费者验证：
main() 中 getopt 与 `argc < 1` 校验发生在 socket 错误检查之前，故无需
root/网络即有稳定输出与退出码：

1. 无参数 -> stderr `Usage: netselect ...` + exit 1
2. `-t 0` -> "number of tries must be >1." + exit 1
3. `-m 1` -> "max ttl must be >1." + exit 1
4. 未知选项 `-Z` -> usage + exit 1
5. `netselect -I 127.0.0.1`（未授权）-> "netselect: socket: ..." + exit 5
   （root 环境下允许真实探测的任意正常退出码，测试中降级放行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | worktree 创建失败 `unable to create file ...patch?? Invalid argument` | origin/main 历史中存在文件名带 CR 的非法文件（archives/g/gama/2.29/patches），Windows 无法创建 | `git worktree add --no-checkout` + sparse-checkout 排除该路径后再检出 |
| 2 | GitHub 直连下载超时 | 网络环境限制（E017） | ghfast.top 镜像下载，与 macports distfiles 双通道核验 SHA256 一致 |
| 3 | 上游 Makefile install 带 chown root/setuid | 上游以 setuid 二进制方式分发 | package() 手动 copy 二进制与 man 页，不做 setuid（E087 HMDFS chmod 不可靠） |
| 4 | 真机 r1: `build_and_test.sh:980: permission denied: bash` → KC 全灭 | 设备 `/data/service/hnp/bin/` 下所有符号链接失效（目标不可解析，HMDFS symlink 故障），bash/make 等全断 | job env.sh PATH 前置真实二进制目录 `/data/service/hnp/bash.org/bash_5.3/bin`（原位二进制有签名可执行；复制到 HMDFS/haps 分区会丢 ELF 签名被拒 E077） |
| 5 | 真机 r1: netselect.c 编译 20 errors `unknown type name 'u_char'/'u_short'` | Makefile `-I.` 使源码自带旧 BSD netinet/{ip,ip_icmp,udp}.h 遮蔽 musl/OHOS sysroot 头（E113 族） | build() 覆盖 `CFLAGS` 去掉 `-I.`，改用系统头（零补丁） |
| 6 | 真机 r2: netselect.c 自身 9 处 u_char / 4 处 u_short 未定义 | musl 不提供遗留 BSD typedef（E113） | CFLAGS 追加 `-Du_char=uint8_t -Du_short=uint16_t`（add-cflags，零补丁） |
| 7 | 真机 r3 后 test_ohos T2 FAIL：二进制含构建目录绝对路径 | 上游 CFLAGS `-g` 的 DWARF 嵌入 comp_dir 路径 | CFLAGS 改 `-g0`，泄漏清零 |
| 8 | test_ohos T1 FAIL：readelf 不可用 | 设备 hnp/bin symlink 故障致 readelf 失效 | run_ohos_test.sh T1 加 `file` 兜底判 arm64 |

## 验证结果（真机 shadow CI，W5）

设备: HarmonyOS PC (HongMeng Kernel 1.12.0, aarch64)，job
`netselect-0.4-20260929`，共 4 轮迭代（r1 KC 设备故障 / r1 编译失败 /
r2 编译失败 / r3-r4 通过）：

```text
run: codex-0.4-netselect-0.4-20260929-conan-20260929-103749-44005
exit code: 0
G0_RESULT=pass  G0e=pass  KC_RESULT=pass  JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed   (含 L1e 破坏性反向验证通过)
L2_RESULT=skip: netselect version/help failed  (上游无 --version/--help 选项，非阻塞)
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Pass rate: 100.0% (1/1)
```

- test_package: 5/5 checks PASS（usage / -t 0 / -m 1 / -Z / 未授权 socket exit 5）
- test_ohos 专项: 4/4 ALL PASS（T1 arm64 ELF / T2 无路径泄漏 / T3 usage /
  T4 未授权 raw socket → exit 5，符合预期降权路径）
- 排队等待: r1 15 秒（后续轮次锁竞争下 <1 分钟）

## 验证结果（本机前置 W4）

- Python 语法检查: 通过（conanfile.py × 2）
- YAML 结构检查: 通过（conandata.yml / manifest.yaml / MANIFEST.yml）
- JSON 结构检查: 通过（commands.json）
- git diff --check: 通过
- 上游构建/测试: 本机 Windows 无 make/OHOS 工具链未执行；已在真机 shadow CI
  完成（见上节，r4 exit 0 全 pass）

## 下一步

- 真机 shadow CI 已完成（r4 全 pass）；下一步：推送分支并按 `ohc-run.py submit`
  建单库 PR（issue 编号待补）。

## 注意事项

- 一库一 issue/分支/PR: feat/netselect-0.4-codex；issue 编号待补
  （本轮指示 issue 已废弃，先行本机前置适配）。
- 分支基于 origin/main (317e16ed) sparse-checkout 建立，已排除主仓库历史
  中一个 Windows 非法文件名路径（archives/g/gama/2.29/patches/*），
  不影响本包目录的完整性。
- 提交前清理 conandata.yml.ghfast-bak 等镜像注入残留（DRAFT-E323）。

---

**状态**: built（真机 shadow CI r4 全 pass，2026-09-29）
