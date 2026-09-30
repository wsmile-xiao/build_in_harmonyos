# ndppd 0.2.6 适配笔记

## 上游信息

- 上游: https://github.com/DanielAdolfsson/ndppd
- 版本/Tag: 0.2.6 (2015)
- 许可证: GPL-3.0-or-later（主源码头 "or any later version"；LICENSE 为 GPLv3 全文）
- 源码归档: `https://github.com/DanielAdolfsson/ndppd/archive/refs/tags/0.2.6.tar.gz`
- SHA256: `969d438462e0c65a8c9060d8d263c5c47ba8145fb9aaa663864bbad11ad7eb7a`
- 语言: C++ (C++98 风格, .cc/.h)
- 构建系统: plain Makefile（无 configure）
- 上游测试: 无（无 test 目录，Makefile 无 check/test target）

## W0 依赖结论

| 依赖 | 类型 | 状态 |
|------|------|------|
| libnl-3.0 / libnl-route-3.0 / glib-2.0 | 可选构建依赖（仅 WITH_ND_NETLINK） | 不启用，无需适配 |
| pthread | 可选运行时（仅 netlink 监视线程） | 默认路径不引用 |

- 默认构建路径零外部依赖：仅标准 C++ 库 + POSIX/libc。
- 无需拆分依赖适配任务。

## W1 源码/构建分析

- 产物为单个守护进程二进制 `ndppd`，无库文件。
- `ndppd.cc` 的 `netlink_setup()/netlink_teardown()` 调用被 `#ifdef WITH_ND_NETLINK` 保护；
  `rule.cc`/`proxy.cc` 同样有条件编译 → 默认路径完全不碰 libnl/pthread。
- `nd-netlink.cc`（不编译）含 `pthread_cancel`，musl/OHOS 不可用（知识库 E085/E127）——不启用即规避。
- 默认路径 `route.cc` 解析 `/proc/net/ipv6_route` 文本，`iface.cc` 使用标准 ioctl/setsockopt/poll，musl 均可用。
- `logger.cc` 有 `DISABLE_SYSLOG` 开关；syslog 在 OHOS musl 存在（可能为 stub），保留默认。
- Makefile `all` 目标构建 man 页，`GZIP ?= /bin/gzip` 硬编码 → OHOS 无此路径；配方只构建 `ndppd` 目标。
- **注意**: 上游 0.2.6 tag 中 `src/ndppd.h` 的 `NDPPD_VERSION` 仍为 `"0.2.4"`（上游疏忽），
  运行时版本输出为 `version 0.2.4`。测试断言必须匹配 0.2.4，已在 notes/manifest/test 中记录。

## 构建命令

```bash
make -j1 ndppd CXX=clang++ CXXFLAGS="-O2 -fPIC -Wall"
```

## 打包

- `bin/ndppd`、`licenses/LICENSE`、`res/ndppd.conf-dist`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `logger.cc:92 error: no viable conversion from returned ... strerror_r` | OHOS musl 的 `strerror_r` 恒为 POSIX `int` 签名（即使 `_GNU_SOURCE`，OHOS sysroot 默认开启该宏），源码按 glibc `char*` 语义使用 | 补丁 0001：改按 `__GLIBC__` 分支，musl 走 POSIX 调用 |
| 2 | Makefile `all` 需 `/bin/gzip` 压缩 man 页 | OHOS 无该路径 | 配方只构建 `ndppd` 目标，man 页不打包 |
| 3 | （规避）`pthread_cancel` musl 不可用（E085/E127） | 仅存在于 `nd-netlink.cc`（WITH_ND_NETLINK 可选路径） | 不启用 WITH_ND_NETLINK，默认路径不编译该文件 |

## 源码修改

| 补丁文件 | 修改内容 |
|---------|---------|
| 0001-logger.cc-strerror_r-musl.patch | `logger::err()` 按 `__GLIBC__` 区分 `strerror_r` 语义（glibc `char*` / musl POSIX `int`） |

## 本机验证（W4）

- 本机 OHOS SDK: `C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\native`
- 交叉编译命令（与 conanfile build 等价）:

```
clang++ --target=aarch64-linux-ohos --sysroot=<sdk>\sysroot -O2 -fPIC -Wall -I src \
  -c src/<m>.cc   (m = logger, ndppd, iface, proxy, address, rule, session, conf, route)
clang++ <同参数> -o ndppd <9 个 .o>
```

- 结果: 9/9 编译通过（仅警告: `-Wparentheses` 于 ptr.h、`sys/poll.h→poll.h` 重定向），链接成功，
  产物 `ndppd` ≈ 202KB，llvm-readelf 确认 `Machine: AArch64`、`Type: DYN`（PIE）。
- 补丁 `git apply --check` 对官方 tarball 干净应用。
- Python/YAML/JSON 语法检查通过。

**真机 shadow CI 结果（2026-09-30，job ndppd-0.2.6-20260929）**：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: ndppd version/help failed   # 无 --version/--help 退出路径，非阻塞
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Build Summary: Total 1 / Success 1 / Failed 0 (100%)
exit-code=0
```

- L1e 破坏性反向验证：`[sabotage] bin/ moved away` → `test genuinely depends on ndppd` ✅
- 上游测试：0/0（无上游测试套件，daemon 项目，与 npd6 同情况）
- test_package：3 断言全过（版本横幅 0.2.4、`-c` 选项、缺配置非零退出）
- conan create：编译+打包成功（package: bin/ndppd, licenses/LICENSE, res/ndppd.conf-dist）

### 迭代记录

| 轮次 | 报错原文 | 根因 | 解法 |
|---|---|---|---|
| r1-r3 | runner 无输出死亡 | 设备多次断联/重启，nohup 进程被带走 | 设备恢复后重启 runner；清理 stale 锁 |
| r4 | `zsh: can't open input file: ci/conan/build_and_test.sh` (127) | prepare 脚本从 repo-source 复制时缺 ci/ 等基础设施目录 | 从 repo-source 补齐 ci/config/docs/references/scripts/templates |
| r5 | `build_and_test.sh:980: permission denied: bash` → KC fail | bash 装在 `/data/service/hnp/bash.org/bash_5.3/bin`，env.sh 默认 PATH 无此路径 | env.sh PATH 前缀加 bash_5.3/bin（对照 netselect 成功 job） |
| r6 | `test.sh: line 18: /tmp/ndppd-test.out: Read-only file system` (E002) | test.sh 硬编码 /tmp（OHOS 只读 erofs） | 改用 `${TMPDIR:-/data/local/tmp}`（commit 15efb5706a） |
| r7 | — | — | ✅ 全门禁通过 |

## 注意事项

- ndppd 需要 root 与 raw/ICMPv6 socket 能力才能实际运行代理；测试仅做启动冒烟（版本输出 + 配置加载失败路径）。
- 功能性验证（真实 NDP 代理）需要多接口/命名空间环境，超出本适配范围。

## 状态

- 前置适配（W0–W3）完成于本机
- issue 编号：待补（交接说明已标记）
