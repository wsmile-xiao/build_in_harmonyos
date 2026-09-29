# libservicelog 1.1.19 适配笔记

## 适配概览

- 任务 14401（依赖项活动），上游 power-ras/libservicelog git tag v1.1.19
  （GitHub codeload tarball 与 git 树逐字节一致，51 blobs）。
- 依赖拓扑：sqlite3 → 制品仓 `sqlite3/3.53.4`；librtas/librtasevent 不单独
  适配（librtas 为任务 8373 的独立包，冲突回避），改为内联编译官方
  librtasevent_src/ 14 个纯解析 .c 文件闭合链接。
- 修改点（补丁 0001）：`SERVICELOG_PATH` 硬编码增加 `SERVICELOG_DB` 环境变量
  覆盖，默认行为不变。

## 上游测试清点（R51 三步法：清点）

git tag v1.1.19 递归计数（== tarball 内容，无 tarball⊂git 差异）：

- 测试相关文件共 **16**：
  - shell 脚本 **9**：src/tests/run_tests + src/tests/tests/test-001..006
    （6 场景）+ libservicelog-ci/build-fedora-33.sh + build-ubuntu-20.04.sh
  - C 驱动 **1**：src/tests/test_libservicelog.c
  - 期望输出 **6**：src/tests/tests-results/test-00X-*.result.out
- 功能场景 **6**（log→dump 往返 ×5 事件类型 + 截断语义 ×1），上游
  .travis.yml 以 docker 容器运行 `libservicelog-ci/build-*.sh`
  （ppc64le，fedora-33/ubuntu-20.04 矩阵；bootstrap/configure/make 序列在
  CI 脚本内）。

## 上游测试实跑

**真机全绿（2026-09-27，鸿蒙真机通道2，conan 2.29.1）**

- 命令：`python3 scripts/ohc-run.py conan-verify libservicelog 1.1.19`
  （profile ci/conan/profiles/ohos-aarch64，clang 15 / libc++ / armv8，
  `conan create … --build=missing --user=ohpcd --channel=stable`）
- 环境：DB 路径由补丁 0001 的 `SERVICELOG_DB` 环境变量指向临时目录
  （无 /var 写权限亦可用）；E017 网络注入（ghfast.top 挂起）→ 本地
  http.server 镜像链绕过（conandata 临时 sed 镜像 URL，验证后已还原
  官方 URL）。
- 收敛史：共 11 次 verify 迭代，7 个修复点：
  1. G2 首挂 `sqlite3.h` 找不到 → cpp_info includedirs 为包相对路径，
     需与 dependency.package_folder 拼接（isabs 防护）。
  2. `slog_internal.h` 包含 `<servicelog-1/servicelog.h>` → 编译需加
     `-I src_root`。
  3. test_package 消费者编译缺 sqlite3.h（test_package 上下文不暴露
     传递依赖）→ 显式 `self.requires("sqlite3/3.53.4")`。
  4. conan 2.29 `run(env=list)` 不向子进程传播环境变量，
     `environment_append` 已移除 → `env.vars(self, scope="run").apply()`
     上下文管理器。
  5. probe：`SL_TYPE_OS` 事件必须携带 os addl_data 块
     （insert_addl_data_os 无 NULL 检查直接解引用，上游驱动同款要求）。
  6. probe：`servicelog_event_query` 拒绝 NULL 查询串 → 传 `""` 查全部。
  7. 比较器容差：上游 `cut -d ' ' -f1,2` 只比较行首字段名
     （"Platform:" 后接多空格时第二字段为空串的尾随空格陷阱）→ 改为
     字段名前缀匹配（`line.lstrip().startswith(IGNORE)`）。
- 结果：八门禁（G0-G4 + L2/L4/L5）全绿，**Verdict PASS**，可标记
  published；test_package：probe 逐字段断言全过 + 上游 6 场景
  **SUITE PASS: 6/6**（001-basic/002-os/003-rtas/004-encl/005-bmc
  log→dump 往返 + 006-truncate 截断语义）。
- 证据：reports/conan-verify-report.md（真机原样回传；conan-create.log 按
  rule 19 不随 PR，构建细节已蒸馏进本节）。

## 适配决策记录

1. **不跑 autotools**：设备无 autoconf/automake/libtool 全套；tarball 已带
   预生成 yacc/flex 产物（v29_notify_gram.c / v29_notify_lex.c），手写
   clang 直编 9 个库源文件 + 14 个 rtasevent 源文件即可。
2. **v1 打印路径不调 librtasevent**（源码审计）：`addl_data_fcns[SL_TYPE_RTAS].print`
   = addl_data.c 的 `print_addl_data_rtas`（v1），`parse_rtas_event` 等仅
   v29_print.c/v29_compat.c 引用 → 上游 6 场景不触碰 rtas 解析行为，内联
   编译只为闭合链接，行为风险为零。
3. **libtool 命名复刻**：`-release 1.1 -version-info 1` → 真名
   libservicelog-1.1.so.1.1.19、SONAME libservicelog-1.1.so.1；pkg-config
   广告 `-lservicelog` → 无版本别名一并物化（真实拷贝，HMDFS 无符号链接）。
4. **测试器移植**：上游 run_tests 为 bash + `diff -a -y --suppress-common-line`
   + `cut`；设备 toybox 无 `diff -y`，test_package 提供 POSIX 移植驱动
   （run_upstream_tests.sh）+ python 容差比较器（cmp_tolerant.py），比较语义
   逐条复刻 diff_with_result_without_timestamp（忽略 Log/Event/Update
   Timestamp、Platform、Node Name 行首字段名，其余逐行字节比对）。
5. **本地 MinGW 预验证**（Windows 侧，提交前）：同源文件同配置编译 + 上游
   6 场景全 PASS；MinGW 需要本地垫片（endian.h/sys/ipc.h/grp.h/dlfcn.h 空
   头、fork/strptime/pipe/ctime 桩）——均为 msvcrt 缺失项，设备 musl 原生
   具备，不进配方。

## 鸿蒙特有测试（rule12）

- probe.c：消费者 v1 API 全链路逐字段断言（open/log/query/print/truncate/
  close），SERVICELOG_DB 覆盖生效（无 /var 写权限）。
- run_upstream_tests.sh：上游 6 场景由消费者编译的上游驱动跑通，容差比较。

## 状态表

| 项 | 状态 |
|---|---|
| L0 本地门禁 | MinGW 本地同源预验证通过（决策记录5，6 场景全 PASS） |
| 真机 conan-verify 八门禁 | 通过（2026-09-27，Verdict PASS，11 次迭代收敛） |
| 真机 conan create + test_package（probe + 6 场景） | 通过（probe 全过 + SUITE PASS 6/6） |
| 路径B 知识草稿 | 已挂 2 草稿：conan29-run-env-injection / bash-gnu-diff-runner-port |
