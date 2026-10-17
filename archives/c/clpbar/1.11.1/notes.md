# clpbar 1.11.1 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，2001 年生成的 configure，无外部依赖）
- 编译日期: 2026-09-07
- 编译器: clang 15（HarmonyOS PC aarch64 真机预检）
- 状态: built（待真机预检与 CI upload 后更新）

## 上游信息
- 上游仓库/主页: http://clpbar.sourceforge.net
- 源码包: bar_1.11.1.tar.gz（187144 字节）
- sha256: fa0f5ec5c8400316c2f4debdc6cdcb80e186e668c2e4471df4fec7bfcd626503
- 产物: 仅 `bar` 可执行文件，无库、无外部依赖（W0：零依赖，直接适配）

## 上游测试审计（Makefile.am）
| 测试 | 类型 | 说明 | 状态 |
|------|------|------|------|
| test-types | C 断言程序 | uint8/16/32/64 位宽 assert（4 个断言） | TESTS 注册，make check 运行 |
| test-001 | shell 管道测试 | test-001-pre \| bar \| test-001-post，两次 Hello World 字符串比对 | TESTS 注册，make check 运行 |
| test-002 | shell 回环测试 | tar 打包后经 `bar -if/-of` 与管道两种路径复制，cmp 比对 | TESTS 注册，make check 运行 |
| test-003 | shell（已注释） | Makefile.am 中 `# TESTS += test-003`，仅 EXTRA_DIST | 不运行 |
| test-004 | shell（已注释） | Makefile.am 中 `# TESTS += test-004`，仅 EXTRA_DIST | 不运行 |

结论：上游有效测试 3 项，`make check` 即全部。

## 编译步骤
```bash
./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --disable-dependency-tracking ac_cv_prog_cc_works=yes ac_cv_prog_cc_cross=yes
make -j1
make check -j1
make install
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | 2001 版无 HarmonyOS 分支，`uname -s` 返回 HarmonyOS | build() 内联补丁：`*:HarmonyOS:*:*` 返回 `${UNAME_MACHINE}-unknown-linux-ohos`（E007） |
| 2 | config.sub 拒绝 triplet | 旧版不认识 linux-ohos 与 aarch64 CPU | build() 内联补丁：kernel-os 列表加 `linux-ohos*`、OS 白名单加 `-linux-ohos*`、CPU 表加 aarch64/aarch64le |
| 3 | configure 报 cannot run C compiled programs | 沙箱禁运行 conftest | cross.cache + 命令行 `ac_cv_prog_cc_works/cross=yes` 双保险（cadaver/speex 先例） |
| 4 | config.status 临时目录不可写 | HMDFS + umask 077（E011） | configure 内 `umask 077` 替换为 `umask 022`（adcli 先例） |
| 5 | 2001 depcomp 不认识 clang | 年代久远的依赖跟踪脚本 | `--disable-dependency-tracking` |

## 证伪说明（测试非空跑）
- test-types：4 个 `assert(c == 8/16/32/64)`，位宽错误即 abort，非空断言。
- test-001：test-001-post 中 2 次 `strcmp` 比对 Hello World，错一个字节即 exit 1。
- test-002：2 次 `cmp` 二进制比对；若 bar 透传损坏则失败。test_package 的 test.sh 同理用 `cmp` 比对。
- 若 harness 静默跳过，`make check` 的 PASS 行缺失即被发现；conan 侧以 exit code 兜底（失败即抛异常，无 marker）。

## 验证结果（待真机预检回填）
- `conan create`（含 make check + test_package）：待 HMBS 预检日志
- 上游测试：3 项（test-types、test-001、test-002），以预检 `HMBS_UPSTREAM_TEST_RESULT` 为准
- 新增测试：test.sh 3 项（--version、管道回环、文件回环），以预检 `HMBS_TEST_PACKAGE_RESULT` 为准

## 使用知识
- E007: config.guess 识别 OHOS + 非 HMDFS work 权限放开（同 neon 0.34 / cadaver 0.24）
- E011: umask 077 导致临时目录不可写（同 adcli 0.9.2）
- E074: make -j1（HMDFS jobserver FIFO 限制）
- R32: `self.settings.os not in ("Linux", "OHOS")` 平台判断
