# mcl 22-282 — HarmonyOS PC 适配说明

## 概况

`mcl` 是 Stijn van Dongen 开发的 Markov 聚类（MCL）算法套件：以图上
随机游走 + 膨胀模拟为核心的无监督聚类引擎，广泛用于蛋白质序列家族、
图谱与网络聚类，配套 clm/mcx/mcxload/mcxdump 等图与矩阵分析工具。

- 上游：https://micans.org/mcl/ （官网发布 tarball，自带预生成 configure）
- 形态：标准 automake 递归构建，in-source 构建
- 产物：`bin/{mcl,clm,mcx,mcxi,mcxsubs,mcxmap,mcxarray,mcxdump,mcxload}`
- 依赖：conan `cimfomfa/21-361`（Makefile.am 无条件 LDADD=-ltingea +
  ivp.h include <tingea/types.h>；核心聚类库随源码捆绑，
  libm/libpthread 系统提供）
- 许可证：GPL-3.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | tarball 无 config.guess（configure.ac 无 AC_CANONICAL），但运行期 build 类型探测仍执行 config.guess；CI worker 的 HOME/临时目录不可写即炸 cannot guess build type | configure 显式传 `--build/--host=aarch64-unknown-linux-musl` 跳过探测（随包 config.sub 2022-05-25 不识别 ohos 后缀，须用可识别的 musl；CI #63497 实测） |
| 2 | 上游无 test/check 目标（testing/ 为交互式人工观察 harness，硬编码 /usr/local/bin 路径） | 配方 build() 以确定性 5 节点两簇数据集跑 mcxload→mcl 真实聚类管线自检（断言两簇精确划分）；原因完整记录在 test_package/MANIFEST.yml |
| 3 | doc/ man 页依赖 zoem/troff | man 页与 .azm 源全部随 tarball 预生成分发，产物 mtime 均晚于源（实测逐对核验）→ 不触发重建，直接 install |
| 4 | automake 子目录 bin_PROGRAMS | 构建产物在各源子目录（src/shmcl/mcl 等），顶层无 bin/；安装后统一落 bin/ |
| 5 | CONFIG_SHELL 缺陷（§12.38①）；HMHDFS umask 077；jobserver EPERM | `env -u CONFIG_SHELL SHELL=/bin/sh` + 绝对路径；configure/config.status umask 077→022 替换；`make -j1` |
| 6 | CLI 工具门禁 | 软件级 `commands.json`（R38） |

## 测试

### 上游

无可自动化测试套件：标准 automake 但无任何 test/check 目标（grep
TESTS 实测零命中），testing/ 目录是交互式人工观察 harness。原因完整
记录在 test_package/MANIFEST.yml。配方 build() 阶段补做确定性自检。

### 消费者（test_package/test_mcl.sh，6 项断言）

mcl --version / mcx --version / mcxload abc→mci / tab 标签完整 /
mcl -I 1.4 真实 Markov 聚类（-use-tab 输出，断言 {a1,a2,a3} 与
{b1,b2} 两簇精确划分，顺序不敏感）/ mcxdump -tab 标签转储。全部离线
确定性，真实执行包内安装位二进制（R33/R34）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 22-282 | prepared | 首次适配，2026-09-28 真机构建/自检/消费者测试 6/6/finish 全绿（SHA 678c8c91 复验）；审计 3 项 P1（本 README 声明过期等）修复后待新 SHA 复验 |
