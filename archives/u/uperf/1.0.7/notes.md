# uperf 1.0.7 适配笔记（DS-5，接手 Q-5m 交接行）

## 编译环境
- 构建系统: autotools（tarball 自带生成好的 configure，免 autoreconf）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（设备 native，OHOS 目标）
- 状态: built
- worktree: `~/qzy/Q-5m-uperf-1.0.7`｜分支 `feat/uperf-1.0.7`｜CONAN_HOME `~/tmp/ch/home-ds5-uperf`

## 编译步骤

1. `conandata.yml` 官方 URL（github tag 1.0.7 tarball）+ sha256 预置 dlcache 命中。
2. build()：E011 补丁去掉 configure 的 umask 077 包裹 → `CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh ./configure
   --prefix=/ --disable-ssl --disable-sctp --disable-netstat`（native 构建，不传 --host/--build）→
   `make -j2`。
3. 上游测试：先拉起 `./src/uperf -s`（slave，监听 20000）再 `make -C tests check`，finally 杀 slave——
   1.0.7 tarball 的 tests/test.sh 不自启 slave（上游 master 分支已修复）。
4. test_package：消费者回环测试（slave + master 计划，3 断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报 confXXXXXX/subs1.awk Permission denied | E011/HMDFS：configure 安全临时目录用 `umask 077 &&` 包裹 | 补丁去除 umask 包裹、保留临时目录创建（Q-5m 探索期实证） |
| 2 | make check 0/21 PASS，全部 `Cannot connect to localhost:20000` | 上游 1.0.7 tarball 的 tests/test.sh 不自启 slave（与 master 分支行为不一致）；uperf master 需要外部 slave 监听 20000 | build() 编排 slave 生命周期：拉起 → sleep 2 → make check → kill |
| 3 | `--host=aarch64-unknown-linux-ohos` 报 no acceptable C compiler | 设备 clang 即 OHOS 目标，交叉三元组触发带前缀编译器探测（Q-5m 已排除方向） | native 构建不传 --host/--build |
| 4 | tc.generate(env=env) 只传 CONFIG_SHELL/SHELL 后 CC/CFLAGS 全丢 | 本机 conan 2.29 的 env 参数是整体替换而非合并（实测 conanautotoolstoolchain.sh 只含传入变量） | `env = tc.environment()` 取工具链环境组合后再传回 |
| 5 | E386 working directory cannot be determined（GLM-67 pullseq 同族教训） | profile [buildenv] CONFIG_SHELL 指向 hnp bash，HMDFS 上 getcwd() 挂 | generate() 组合环境 + 命令内联双保险压成 /bin/sh（§12.38①） |
| 6 | dlcache 命中失败反复重下 ghfast（不可达） | 失败重下会把缓存文件删掉并留 `.dirty` 标记 | 重拷官方 tarball 入缓存 + 删 `.dirty`；sidecar 需同时登记官方与 ghfast URL |

## 源码修改

- `patches/0001-e011-drop-umask077-wrapper.patch`：仅去除 configure 两处 `umask 077 && ` 前缀
  （mktemp -d 与 mkdir 各一处），保留临时目录创建逻辑本身。补丁已用 orig/work configure 对拍验证。

## 依赖版本

无第三方依赖（SSL/SCTP/netstat 显式关闭；RDS 未编译）。

## 验证结果

```bash
# conan-verify 全门禁通过（第 5 轮，VERIFY_RC=0）：G0/G1/G2/G3/G4/L2/L4/L5 ✅
# G2 conan create（干净构建）内 make check 真实执行：
#   TOTAL 23 = PASS 21 + XFAIL 2（unknown_proto/parse_err 为上游 XFAIL_TESTS，预期失败）
#   未注册 10 项 = SCTP 8（--disable-sctp，musl 无 netinet/sctp.h）+ SSL 1（--disable-ssl，
#   未声明 openssl 依赖）+ RDS 1（HAVE_RDS 未定义），按条件未启用申报
```

五维账本：`N_static=33`（tests/Makefile.am：TESTS 无条件 17 + 条件注册 16 = SCTP8/PROC4/SSL1/UDP2/RDS1，
XFAIL_TESTS=2）｜`N_registered=23`｜`N_executed=23`（21 PASS + 2 XFAIL，0 FAIL）｜未执行分类 10（条件未启用，
逐项如上）｜`N_consumer=1`（test_package 消费者回环测试，3 断言全过）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/uperf | ~261KB | 命令行网络基准测试工具（已 OHOS 自签，E077） |

## 注意事项

- `commands.json` 声明 type=tool（R38：产物是 CLI 工具 src/uperf）。
- test_package 消费者测试占 20000 端口，串行执行无冲突；CI worker 并行多 PR 构建时各自命名空间隔离。
- 上游 test.sh 的版本差异（master 分支带 slave 生命周期管理）：如未来升级版本，1.0.7 之后的 tag
  可能不再需要本配方手工编排 slave，届时移除 build() 中的 slave 逻辑即可。

## 最终状态

- 状态：`built`（conan-verify 全门禁通过）
- 下一步：W4 审计 → 精确提交 → `$P run` 一条龙（触发 CI 后自动 stage【CI中】让渡 CIW）
- 证据：`reports/conan-verify-report.md`、`~/tmp/uc2/ds5-uperf/`（探索日志 check1/check2、verify1-5）
---

**编译结束**: 2026-09-21 11:10
**最终状态**: built
