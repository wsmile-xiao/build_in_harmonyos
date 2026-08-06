# coin-or 0.108.12 适配笔记

## 编译环境
- 构建系统: autotools（COIN-OR 递归 configure：顶层 + Osi/ 子目录）
- 编译日期: 2026-08-06
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build coin-or 0.108.12 --url=<官方 tarball>`（GitHub 直连失败时，将本地已下载 tarball 放入 `$HOME/tmp/builds/coin-or-0.108.12.tar.gz` 复用）
2. 修补 `config.guess`/`config.sub` 支持 HarmonyOS（`HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl`）
3. configure：
   ```
   ./configure --prefix=<prefix> \
     --with-coinutils-incdir=<coinutils>/include/coin \
     --with-coinutils-lib="-L<coinutils>/lib -lCoinUtils -lz -lm" \
     --build=aarch64-unknown-linux-musl --disable-dependency-tracking
   ```
4. 修补 `config.status`（顶层 + Osi/）修复 HMDFS umask/mktemp 临时目录问题后重跑
5. `make -j1` → `make install DESTDIR=<test-prefix>` → `make check`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 源码下载失败 | 网络限制 "Remote end closed connection" | 本地预下载 tarball 放入 `$HOME/tmp/builds/` 复用 |
| 2 | `config.status` 报 `confstat*/in: Permission denied` | HMDFS 下 `mktemp -d -q` + `umask 077` 创建临时目录失败 | sed 修补 config.status：`mktemp -d -q` → `mkdir -p ./conftmp`、`umask 077` → `umask 022`，并让 `$tmp` 实际赋值为 `./conftmp` 后重跑 |
| 3 | 顶层 configure 只生成顶层 Makefile，Osi/ 子目录 Makefile 缺失 | COIN-OR 递归 configure，子目录 config.status 同样受 HMDFS 临时目录问题影响 | 对顶层与 `Osi/config.status` 都做同样修补后重跑 |

## 依赖版本

- coinutils/2.11.13（制品仓已发布，OHOS armv8 clang15 预编译）
- zlib/1.3.1（制品仓已发布）

## 验证结果

- `make check`：Osi 上游测试位于 `Osi/src/OsiCommonTest`（8 个测试源）与 `Osi/test`（11 个求解器测试源），默认构建不生成可执行测试目标，`make check` 无测试运行
- test_package：消费者测试创建 OsiCuts 并插入 OsiRowCut（R34 实质性测试）

## 注意事项

- 依赖 coinutils 的 pkg-config 未自动传播 `-lz`，configure 需显式传 `--with-coinutils-lib` 含 `-lz -lm`
- 本库为 COIN-OR Osi（Open Solver Interface），EPL-2.0 许可证
---

**编译结束**: 2026-08-06 03:07
**最终状态**: built
