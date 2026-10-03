# tayga 0.9.2 适配笔记

## 软件概况
- TAYGA：用户态无状态 NAT64 守护进程（RFC 6145），通过 TUN 设备与内核交换 v4/v6 报文
- 上游：http://www.litech.org/tayga/
- 源码归档：官方 `http://www.litech.org/tayga/tayga-0.9.2.tar.bz2`（README 自述下载地址；2026-10-01 下午曾从本机网络瞬时 404，同日恢复，CI Worker 实测可达；同 SHA256 副本亦在 Debian pool 镜像 `tayga_0.9.2.orig.tar.bz2`）
- 许可证：GPL-2.0-or-later（源文件头："either version 2 ... or (at your option) any later version"）
- 语言/构建：纯 C，autotools（configure + Makefile.am），产物为单二进制 `tayga`（sbin）

## W0 依赖结论
- 依赖数量：0（仅 libc + Linux 内核头文件 linux/if_tun.h 等）
- 已满足依赖：全部（OHOS sysroot 已包含所有所需头文件）
- 缺失依赖：无
- 是否需要拆分依赖适配：否
- 阻塞点：无

## W1 源码与构建分析
- 5 个 .c + tayga.h/list.h，configure.ac 极简（仅 AC_PROG_CC）
- 无 AC_CANONICAL_HOST、未附带 config.guess/config.sub → 无平台三元组识别问题（避开 E007/E122）
- 上游无测试套件（无 test/ 目录、无 check 目标）→ upstream_test_in_build: false
- 运行时需要 /dev/net/tun 与 root 权限（真机数据面测试超出 test_package 范围）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | error: redefinition of 'struct sockaddr_storage' | OHOS linux/socket.h 与 musl sys/socket.h 均定义该结构体，linux/if.h 间接引入 linux/socket.h（知识库 E091/E119） | 补丁：`#ifdef __OHOS__ #define _UAPI_LINUX_SOCKET_H` 跳过 linux/socket.h（linux/if.h、if_tun.h、if_ether.h 均不依赖其中符号） |
| 2 | warning: call to undeclared function 'writev' ×7 | glibc 下 sys/socket.h 间接引入 writev，musl 不会 | 补丁：`#ifdef __OHOS__ #include <sys/uio.h>` |
| 3 | L0c no_test_sources | CI 要求 test_package/ 有独立测试源文件（.c/.cpp/.sh/.py） | 新增 `test_package/test_tayga.sh`（3 断言冒烟脚本），conanfile.test() 改为执行它 |
| 4 | configure: Permission denied (exit 126) | HMDFS 上解压出的 configure 无执行位且 chmod 无效（E046/E087） | build() 改用 `sh configure` 显式执行（kelbt 0.16 真机先例） |
| 5 | config.status: ./confXXXXXX/subs1.awk: Permission denied | configure 临时目录 `umask 077 && mktemp -d` 在 HMDFS 上产出的目录带 setgid 且权限异常（E011/E052） | 补丁 0002：configure 去掉 umask 077 并 `chmod g-s`（tftp-hpa 5.2 同款方案；该段会传导进生成的 config.status） |
| 6 | conan create: Invalid setting 'OHOS' | conan settings 对象 `==` 比较会校验右值，本机 settings.yml 无 OHOS | 改用 `str(self.settings.os) == "OHOS"` |

另：真机环境 git wrapper 位于 HMDFS 无法执行（E087），job env.sh 前置 `/data/service/hnp/bin`（完整工具链）解决——job 运行环境调整，不进 PR。

未修改：nat64.c 中 12 个 packed-member 取地址警告（上游代码风格，glibc/Linux 同样存在，不影响正确性）。

## 本机验证（W4，Windows + DevEco OHOS SDK clang）

```
clang --target=aarch64-linux-ohos --sysroot=<OHOS sysroot> -g -Wall \
  -DTAYGA_CONF_PATH="/etc/tayga.conf" -c nat64.c addrmap.c dynamic.c tayga.c conffile.c
→ 全部编译通过（剩余 12 个警告均为上游 packed-member 风格警告）
→ 链接通过，llvm-readelf 确认 ELF64 / AArch64 / DYN
```

- 补丁在干净源码上 `git apply --check` 通过
- 源码 SHA256 复核：2b1f7927a9d2dcff9095aff3c271924b052ccfd2faca9588b277431a44f0009c ✓
- 上游测试：上游无测试套件（如实记录，非跳过）

## Test evidence

- Local OHOS cross-compile (clang, aarch64-linux-ohos): all 5 translation units OK, link OK, ELF64 AArch64.
- Local end-to-end `conan create` (Docker ubuntu:24.04, native gcc): source download + patch + configure + make + install + test_package all passed; `tayga --help` printed full usage, bogus-option rejection OK (exit 0).
- Upstream tests: none shipped with the tarball.
- L1e destructive self-test (R34, local Docker): after removing `bin/tayga` from the built package, `conan test test_package` fails with exit 1 (Error 127) — test genuinely depends on package artifacts, not a fake test.
- lang-preflight (R47): task=cpp, detected=c — matched, main flow continues.
- prescan: findings empty; build_system=autotools; has_tests=false (consistent with upstream shipping no test suite).
- HarmonyOS PC shadow CI (device job tayga-0.9.2-20261001, run 20261001-220834-54016, wait_seconds=1):
  - L0_RESULT=pass (all checks passed; R37 first publish, no version collision)
  - L1_RESULT=pass (test_package executed; `sh test_tayga.sh`: all assertions passed)
  - L2_RESULT=pass (`tayga --help` OK on device)
  - L4_RESULT=pass (patches clean)
  - L5_RESULT=pass (bin/ has content)
  - runner exit code: 0; pass rate 100% (1/1)
- Upstream tests: none shipped with the tarball (recorded as upstream_test_in_build=false).
- Generated CI reports are not committed.

## 下一步

真机 shadow CI 已全绿。真机数据面（TUN + NAT64 转发）验证需 root 与 /dev/net/tun 可用性确认后另行安排，不纳入本 PR。
后续：创建 issue → push 分支 → PR（一库一 issue、一分支、一 PR）。

## 最终状态
built + device shadow CI passed（L0/L1/L2/L4/L5 全 pass，exit 0）
