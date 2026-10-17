# ivar 1.4.4 — HarmonyOS PC 适配说明

## 概况

`ivar` 是 Andersen Lab 开发的病毒扩增子测序（amplicon sequencing）分析
CLI 工具：引物修剪（trim）、共识序列生成（consensus）、变异检测
（variants/filtervariants）、引物错配掩蔽（getmasked/removereads）。

- 上游：https://github.com/andersen-lab/ivar （官方 tag tarball）
- 形态：Autotools（tarball 不含 configure，需 bootstrap 生成）
- 产物：`bin/ivar` 单一可执行文件
- 依赖：htslib/1.24-r0（BAM/CRAM 读写）、zlib/1.3.1（与 htslib 钉同版本）
- 许可证：GPL-3.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | tarball 无 configure，`autogen.sh` = autoreconf；CI worker 无系统 automake/autoconf | tool_requires autoconf/2.72 + automake/1.18，手动执行同序 bootstrap（无 LT_INIT，不需要 libtool；zzuf/0.15 先例） |
| 2 | configure.ac 无条件 `LIBS="-lhts -lp -lpthread"`（-lp 不存在）→ AC_CHECK_LIB 全报 no | 上游怪癖，无害：Makefile.am 的 `LIBS = -lhts -lz -lpthread` 覆盖实际链接；不传 --with-hts，依赖路径经 CPPFLAGS/LDFLAGS 注入 |
| 3 | Makefile.am 硬编码 CXXFLAGS 含 -Werror | 环境变量覆盖 makefile 赋值：导出 -O2 -std=c++11 -Wall -Wextra（保留警告级别，仅去 -Werror 适配 OHOS clang） |
| 4 | config.guess 不识别 OHOS；HMHDFS umask 077；jobserver EPERM | `--build=aarch64-unknown-linux-ohos`；生成脚本 umask 077→022 替换；`make -j1`（zzuf/0.15 先例） |
| 5 | tests 经 `../data/` 相对路径取数据 | in-source 构建（`folders.build="."`） |
| 6 | CLI 工具门禁 | 软件级 `commands.json`（R38） |

## 测试

### 上游（make check，21 项）

tests/Makefile.am TESTS：21 个单元测试程序（plain assert，无外部框架），
覆盖引物修剪、共识阈值/最小深度/seq_id、变异检测（正/反链）、引物 BED、
interval tree、amplicon search 等；数据文件取自顶层 `data/`。

### 消费者（test_package/test_ivar.sh，7 项断言）

version 子命令 / -v 短选项 / 无参数用法+退出码 / 未知命令提示 /
consensus -h / trim 缺参非零退出 / 功能调用（fixtures/sample.mpileup
真实生成共识序列并校验），全部离线、真实执行包内 ivar（R34）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.4.4 | prepared | 首次适配，待真机验证（Windows 阶段 2026-09-26 完成） |
