# libudns 0.6 适配笔记

## 编译环境
- 构建系统: autotools(自制 configure 脚本,非 autoconf 生成)
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4 (OHOS SDK aarch64, musl libc)
- 状态: built

## 编译步骤

```bash
# 在源码目录(上游 tarball 解压目录)内:
./configure                       # 探针: getopt/socket/inet_pton/socklen_t/IPv6/poll 全 yes
make                              # 生成 libudns.a + dnsget/rblcheck/ex-rdns
# 上游无 install 目标,手动 staging 到 TEST_PREFIX:
#   include/udns.h + lib/libudns.a
```

- configure 不接受 --prefix(仅 ipv6 开关),CC/CFLAGS 由环境注入
- 库静态编译 libudns.a,CLI 工具 dnsget/rblcheck/ex-rdns 动态链接

## 上游测试枚举台账(全量,2026-09-10)

**结论: source_declared_total = 0(上游无独立测试用例)**

tarball udns-0.6.tar.gz 共 30 个文件,无 tests/ 目录、无测试框架、无 ctest/pytest 注册、无 make check 目标(`make check` 报 "No rule to make target 'check'")。

| 项 | 文件 | 分类 | 是否独立上游用例 | 是否实际运行 | 结果/原因 |
|----|------|------|-----------------|-------------|----------|
| 库源码 | udns_dn.c udns_parse.c udns_resolver.c udns_init.c udns_misc.c udns_XtoX.c udns_rr_*.c udns_bl.c udns_codes.c udns_jran.c udns_dntosp.c (15 个) | 库实现 | 否(非测试) | 编译 | make 通过 |
| 用户工具/示例 | dnsget.c (762 行) | dig 类 CLI 工具 | 否(工具非用例) | 运行 | `./dnsget -t A -n 223.5.5.5 example.com` → 返回 2 条 A 记录(172.66.147.243, 104.20.23.154),exit 0 |
| 用户工具/示例 | rblcheck.c (379 行) | RBL 查询 CLI 工具 | 否(工具非用例) | 运行 | 无参数输出 usage 提示(no service list specified),exit 0 |
| 用户工具/示例 | ex-rdns.c (114 行) | 并行 rDNS 示例 | 否(示例非用例) | 运行 | `echo 223.5.5.5 | ./ex-rdns` → `223.5.5.5 public1.alidns.com`,exit 0 |
| 辅助源码 | getopt.c (165 行) | 内嵌 getopt 实现 | 否(辅助) | 编译 | 随工具编译通过 |
| 辅助源码 | inet_XtoX.c | 地址转换辅助 | 否(辅助) | 编译 | 随库编译通过 |
| 测试框架 | 无 | - | - | - | 上游无测试框架 |
| fixture/样例/基准 | 无 | - | - | - | 上游无 |
| 测试脚本 | 无 | - | - | - | 上游无(.sh/.py 测试脚本) |
| 构建目标 | libudns.a / dnsget / rblcheck / ex-rdns | 库+工具 | 否 | 构建+运行 | make exit 0,三工具均实际运行 |

**统计口径**: source_declared_total=0(上游 tarball 内无独立 TEST_CASE/测试框架用户用例);configured_executable_total=0(无测试可执行);executed_passed_total=0;通过率 0/0(无测试可运行,非失败)。CLI 工具 dnsget/rblcheck/ex-rdns 为库的使用示例与工具,实际运行验证库功能正常(DNS A/PTR 查询真实返回)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 拒绝 --prefix | udns 自制 configure 只认 ipv6 开关 | 不传 --prefix,prefix 通过 conanfile generate() 环境注入 |
| 2 | 上游无 install/check 目标 | 上游 Makefile 仅 static/shared/dist | conanfile package() 手动拷贝 udns.h+libudns.a;测试无入口 |

## 源码修改

无(纯配方级适配,无源码补丁)

## 依赖版本

- 无第三方运行时依赖(仅 libc/musl + socket,configure 探针 getopt/socket/inet_pton/socklen_t/IPv6/poll 全部系统自带)

## 验证结果

```bash
./dnsget -t A -n 223.5.5.5 example.com   # → 2 条 A 记录,exit 0
echo 223.5.5.5 | ./ex-rdns               # → public1.alidns.com,exit 0
```

## 知识候选台账 (knowledge_candidate_ledger)

**路径决定: path_a_no_knowledge(【积分赛】路径 A,不建草稿)**

本轮适配无真实现块错误,非噪声候选 2 项,均被既有知识部分覆盖,无实质新增可跨库复用差异:

### 候选 1: 手写 configure 脚本拒绝未知选项(含 --prefix/--enable-static)
- 真实错误: `configure: unknown option '--prefix=...'`(udns configure 仅接受 ipv6 开关)
- 根因: udns 自制 configure(非 autoconf 生成)只解析白名单选项,不接受通用 autotools 参数
- 修复: 配方不改 configure,generate() 不注入 --prefix/--enable-static,-- 直接 `./configure && make -j1`,package() 手动拷贝产物
- 验证: conan-verify G1-G4 通过(static-library 类型修正后 G2 干净构建成功)
- 适用范围: 自写 configure 且拒绝未知选项的库
- 四范围查重:
  - 正式图谱: **E384**(自写 configure 探测第三方库需 env 覆盖)→ trigger_overlap(同为"自写 configure"),根因不同(第三方探测 vs 选项拒绝),solution 思路相近(绕开默认 configure 参数)
  - 文档: E384 文档覆盖 configure 特殊处理,无新增
  - 草稿: 无 DRAFT 命中(未知选项拒绝类)
  - 索引: index.tsv 仅 E384 命中
- 判定: trigger_overlap + solution_overlap → **部分覆盖,不构成 path B**(库无依赖、无跨库复用的实质新增,处理即"不传多余参数",已隐含在 E384 家族)

### 候选 2: 上游零测试入口(无 tests/ 目录、无 make check 目标)
- 真实事实: `make check` → "No rule to make target 'check'";tarball 无测试框架/用例
- 根因: 上游 udns 0.6 未携带测试套件(库+CLI 工具形态)
- 修复: 双口径台账 source_declared_total=0;真实运行 CLI 工具与鸿蒙专项消费者测试替代验证
- 验证: dnsget/rblcheck/ex-rdns 实际运行 exit 0;test_libudns_ohos 真实解析 A 记录 PASSED;test_package CTest 1/1
- 适用范围: 无测试入口的 autotools C 库
- 四范围查重:
  - 正式图谱: **E241**(数据/规则清单型库无测试套件台账)→ trigger_overlap(上游无测试);**E530/E535**(make check 相关)
  - 草稿: **DRAFT-cute_files-1.0.0-upstream-zero-test-ohos-validation**(上游零测试审计方法)→ solution_overlap(零测试计数/替代验证方法论一致)
  - 文档/索引: 无独立新增
- 判定: trigger_overlap + solution_overlap → **方法论已被 DRAFT-cute_files 与 E241 覆盖,本轮为同一方法在 autotools C 库的应用,无跨库创新差异,path A 复用**

### 候选 3: library 类型配方需声明 shared 选项(conan 报错)
- 真实错误: `Package type is 'library', but no 'shared' option declared`
- 修复: 纯静态库配方声明 `package_type = "static-library"`
- 查重: 常规 conan 配方细节,已有大量先例(E123/E221/E255 family),非知识候选,不入台账

四范围查重合计: 正式图谱 E384/E241/E530/E535 trigger 命中;草稿 DRAFT-cute_files solution 命中;均属部分覆盖/方法论复用 → **reuse_existing = true,new_draft = none,path = A**。
## R02 返工查重台账 (task_id: libudns-0.6-r02-pc2-1-20260910T133501Z)

围绕"来源 SHA-256 审计记录与交付状态不一致"及前序两候选执行 formal/graph/drafts/index 四范围七轴查重:

### 候选 A: source_audit 落盘日志 sha256 为空 vs 终态声称已填(审计与交付不一致)
- 真实矛盾: R01 gate_source_audit.log [5] 核验的是 manifest.yaml 模板占位(sha256: "")且当时 conandata.yml 尚未生成;终态报告声称 conandata sha256 已填并一致 → 审计记录与交付声明表面矛盾
- 根因: 门禁日志核验对象(manifest 模板)与交付事实来源(conandata.yml 生成后)不同步;evidence_logs 内嵌 content 与 log_sha256 指向的磁盘文件不同步(1060B vs 1068B)
- 修复(本轮): 全新下载官方归档 sha256=696a2d0d...c6e8,与 conandata.yml/修复后 manifest.yaml 三方一致;evidence_logs content 按磁盘原始字节内嵌,log_sha256 与上传字节一致
- 四范围查重: 正式图谱 E231(官方来源声明绑定已验证字节, trigger/solution overlap)、E299(来源下载失败分类含 sha256 比对)、E271(单文件资源 SHA256 验证)均覆盖"官方来源必须绑定已校验 SHA-256"纪律;无条目专门覆盖"报告声明的日志哈希必须与上传字节一致"(属执行端运输纪律,非库适配知识);草稿/索引无新增命中
- 七轴: exact_duplicate=否; causal_duplicate=否; trigger_overlap=E231/E299; solution_overlap=E231(先校验官方压缩包 SHA256 再绑定消费字节); combination_novelty=否; boundary_novelty=否; test_migration_novelty=否
- 判定: 本质是执行端审计/运输纪律问题,修复即应用 E231 已确立的"官方来源校验绑定"纪律;无跨库可复用的库适配新知识 → 不建草稿

### 候选 B(前序): 手写 configure 拒绝未知选项
- 四范围: E384(自写 configure 需 env 覆盖)trigger_overlap;无草稿/索引新增
- 七轴同 R01: 部分覆盖,无新增差异 → 复用

### 候选 C(前序): 上游零测试入口
- 四范围: DRAFT-cute_files(上游零测试审计方法)+ E241(无测试套件台账)solution_overlap;无新增差异 → 复用

### 结论: 全部候选部分覆盖既有知识(E231/E299/E271/E384/E241/DRAFT-cute_files),无经真实修复验证且未命中/部分覆盖之外的跨库新增差异 → **path_a_no_knowledge,禁止伪造草稿**
---

**编译结束**: 2026-09-10 23:09
**最终状态**: built

## R03 返工查重台账 (task_id: libudns-0.6-r03-pc2-1-20260910T145819Z)

四范围(formal/graph/drafts/index)七轴查重证据见 r03_dedup.log 摘要, 关键结论:

- 候选 A (manifest.yaml 与 conandata.yml/官方归档 SHA-256 三方一致性审计): trigger_overlap=E231/E299/E271/E406; solution_overlap=是(E231/E299/E406 的"官方来源必须绑定已校验 SHA-256"纪律覆盖三方一致核验做法); combination/boundary/test_migration novelty=否; 关系 similar_to=E231/E299 → 修复即应用既有纪律, 无新增差异
- 候选 B (自写 configure 选项白名单): trigger_overlap=E384(同为自写 configure 需特殊处理), 根因机制不同(探针不读 env vs 选项白名单拒绝), 无新增差异
- 候选 C (上游零测试): solution_overlap=DRAFT-cute_files+E241, 方法论已覆盖, 无新增差异

**路径决定: path_a_no_knowledge** —— 三候选均部分覆盖既有知识, 无经真实修复验证的跨库新增组合/边界/测试迁移差异; 禁止伪造草稿, 未创建 DRAFT-libudns-0.6-* 配对草稿, PR #9445 标题保持【积分赛】不变。
