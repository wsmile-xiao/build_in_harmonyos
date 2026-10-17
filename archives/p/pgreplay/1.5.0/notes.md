# pgreplay 1.5.0 适配笔记

## 编译环境
- 构建系统: autotools（configure 为 autoconf 2.62 生成版，in-source 构建）
- 编译日期: 2026-09-20
- 编译器: OHOS clang/clang++ 15（AutotoolsToolchain 注入）
- 状态: built

## 编译步骤

1. 依赖：postgresql/16.10（提供 libpq/libpq-fe.h/pg_config/psql，binary 已发布并实测可拉）。
2. build()：
   - 构建系统级改写：sed umask 077→022 于 configure（E011：HMDFS uid 映射使 077 临时目录不可写，subs1.awk Permission denied）；
   - env -u CONFIG_SHELL SHELL=/bin/sh sh configure --prefix=… --build=aarch64-unknown-linux-gnu 加 ac_cv 钉值（§12.38 shell 路由；--build 跳过 2013 年 config.guess 的 OHOS 误判；TRY_RUN 探针因未签名 ELF 不可执行返回 0，按 ac_cv_sizeof_unsigned_int=4/unsigned_long=8/unsigned_short=2、ac_cv_func_strtod=yes 钉为平台事实值）；
   - make -j1（链接期 LDFLAGS 指向 postgresql 包 lib）；
   - 上游套件：见下节。
3. 消费者测试 test_package/test_pgreplay.sh：对打包后 pgreplay 二进制做日志解析(-f)、
   重放文件产物校验、离线 dry-run(-r -n) 统计断言（PWD 种子防 E386 变体）。

## 上游测试执行（build() 内真实执行）

- 入口 make test → test/runtest.sh 共 4 节：
  1. stderr 日志解析：**通过**；2. CSV 日志解析：**通过**；
  3. replay（需 psql -U postgres 连活动实例）：**跳过**——技术原因：HMDFS 不支持
     Unix-domain socket，本机 postgresql 包实例 initdb 成功但 postmaster 因
     "could not create any Unix-domain sockets" 退出（pg-server.log 实证），构建环境
     无法提供活动 PostgreSQL；
  4. dry run（-r -n 离线）：**通过**。
- 无服务器时的执行载体：runtest_offline.sh = runtest.sh 原样拷贝、仅将第 3 节替换为
  显式跳过说明（上游测试修改，已逐项申报；其余 3 节断言字节级原样）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status can't create subs1.awk: Permission denied | E011 HMDFS uid 映射 + umask 077 | sed umask 077→022（构建系统级改写，配方内执行） |
| 2 | SIZEOF 检查返回 0、strtod 判 no | TRY_RUN 探针需执行未签名 ELF，OHOS 拒载 | ac_cv_* 钉值（4/8/2、strtod=yes），musl aarch64 事实值 |
| 3 | ../pgreplay: inaccessible or not found | 新机 HMDFS 新文件默认 660 无执行位 | 执行前 chmod +x（E543，mrboom 同型） |
| 4 | 运行期 libpq.so.5 找不到 | musl 忽略 DT_RUNPATH | 运行套件时显式 LD_LIBRARY_PATH=postgresql 包 lib |
| 5 | configure working directory cannot be determined | CONFIG_SHELL 路由 hnp bash（E386 家族） | env -u CONFIG_SHELL SHELL=/bin/sh + PWD 种子 |

## 源码修改

无补丁（patches 为空）。configure 的 umask 修改为构建系统级改写，配方 build() 内执行（§12.50⑤ 交付口径：构建系统级改写放配方内，不进补丁集）。

## 依赖版本

- postgresql/16.10（ohpcd 制品仓，binary 已发布，2026-09-18 revision）

## 验证结果

    python3 scripts/ohc-run.py conan-verify pgreplay 1.5.0
    # G0-G4 全 PASS；上游套件 3/4 节通过（replay 节跳过，证据 pg-server.log）；
    # test_package 消费者断言全过

## 测试账本（五维）

- N_static = 4（口径：test/runtest.sh 的 4 个测试节，每节含多条 diff/cmp 断言；
  语料/期望文件 errlog、csvlog、replayfile、*.exp 共 9 个）
- N_registered = 4；N_executed = 3；未执行 = 1（replay 节：需活动 PostgreSQL 实例，
  构建环境无法提供，技术原因见上，pg-server.log 为证）
- N_consumer = 1（test_pgreplay.sh，3 组行为断言）

## 路径 B 判断（2026-09-20，GLM-65）

判定：**纯 A**。PG 服务器无法在 HMDFS 构建目录启动属 HMDFS 平台限制家族
（E011/E114/E386 同族），不构成可跨仓库复用的新适配方法；唯一候选知识点
（AF_UNIX socket 创建被拒）已并入 manifest knowledge_gained 与本笔记，查重属
HMDFS 家族既有条目覆盖范围，不再单开路径 B 草稿。

## 注意事项

- pgreplay 是可执行文件包：commands.json 位于软件级目录 archives/p/pgreplay/commands.json。
- 如需跑 replay 节：须在支持 AF_UNIX 的文件系统上提供活动 PostgreSQL 实例（本机 HMDFS 不支持）。
---

**编译结束**: 2026-09-20 03:29
**最终状态**: built
