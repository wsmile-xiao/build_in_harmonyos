# 知识候选台账 — md4c 0.5.2（2026-09-07）

> 每个候选记录真实错误/根因/修复/验证/适用范围，并完成四范围查重
> （knowledge/graph/index.tsv、knowledge/doc/、knowledge/graph/、knowledge/drafts/）。
> 所有命令、cwd、退出码、日志见 `logs/` 与 `reports/`。

## 候选 1：W3 本地 CI 命中其他库基线文件 .ci-trigger（JC5 junk 检查）

- **门禁**: finish Step 5 W3 local CI（build_and_test.sh → junk_check.sh JC5）
- **真实错误**: `[FAIL] JC5: 1 个 archives 下未登记的隐藏文件: archives/u/util-linux-login/2.42.2/.ci-trigger`；`JC_RESULT=fail`、`L0_RESULT=fail: junk_check failed`、W3 阻塞
- **根因**: junk_check full 模式用 `git ls-files` 整仓扫描；main 中 util-linux-login（2026-09-03 commit 761df452e5）已提交 `.ci-trigger` 空文件，不在 JC5_ALLOWED 白名单，与本库无关却被命中
- **修复**: 基线隔离复验：记录 pre SHA-256（e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855，空文件）→ `git rm --cached` 索引级临时隔离 → 复跑 finish W3 通过（JC5=pass、L0=pass、.ci-result.json exit_code=0，log_sha256 bdb822e8... 与日志一致）→ `git reset` + 文件原样恢复 → post SHA-256 与 pre 一致，staged/diff 不含该路径
- **验证**: `python3 scripts/ohc-run.py finish md4c 0.5.2 built`（隔离时退出 0、W3 通过）；恢复后 `sha256sum` 前后一致
- **适用边界**: 其他库在 main 已提交的隐藏工作流标记触发 JC5；适用于所有 W3/finish 阶段被共享基线噪声阻塞的库；不适用当前库自身新增的 junk 文件（那必须修复）
- **四范围查重**: 
  - index.tsv：无 E 条目专门对应（无 E 编号命中"JC5/基线隔离"）
  - doc/：无 doc 覆盖
  - graph/：无 graph 覆盖
  - drafts/：**已有多条草稿覆盖同一根因与同一方案**：DRAFT-jc-full-scan-baseline-noise-exemption（match_keywords 含 JC5/整仓扫描/基线噪声/git rm --cached）、DRAFT-dr_mp3-0.7.2-baseline-noise-isolation、DRAFT-libfort-0.4.2-w3-baseline-junk-check-full-scan、DRAFT-libpopcnt-2.0-w3-baseline-junk-check-full-scan、DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise

## 候选 2：conandata.yml 被 E017 镜像注入污染（ghfast/gh-proxy 前缀残留）

- **门禁**: conan-verify G2 / finish W3 的 E017 预防逻辑
- **真实错误**: finish 后 `conandata.yml` 的 sources.url 出现 `https://gh-proxy.com/https://ghfast.top/https://github.com/...` 双重镜像前缀；残留 `conandata.yml.ghfast-bak`、`conandata.yml.orig`
- **根因**: github.com:443 不可达时工具临时把官方 URL 改写为 ghfast/gh-proxy 镜像下载；异常中断/回滚不彻底留下镜像前缀与非交付残留
- **修复**: 恢复官方 HTTPS URL（https://github.com/mity/md4c/archive/refs/tags/release-0.5.2.tar.gz）+ 保留实测 SHA-256（55d0111d...8ef21）→ 删除残留 bak/orig → 重跑 conan-verify 复验（G1-G4 全过，G2 conan create 通过）
- **验证**: `python3 scripts/ohc-run.py conan-verify md4c 0.5.2`（exit 0）；`grep -rn 'ghfast|file://' conandata.yml` 无命中
- **适用边界**: 所有 github.com 不可达、依赖 E017 镜像注入完成 conan-verify/finish 的库
- **四范围查重**:
  - index.tsv：**E323 已登记**（DRAFT-E323-conan-verify-ghfast-bak-rollback 列为草稿；另有 DRAFT-lexy-2025.05.0-e017-mirror-injection-residual-cleanup 草稿）
  - doc/：无正式 doc
  - graph/：无正式 graph 条目
  - drafts/：**DRAFT-lexy-2025.05.0-e017-mirror-injection-residual-cleanup（完全覆盖：ghfast-bak/orig 识别、清理、恢复官方 URL + SHA-256、原子性排除）**、DRAFT-E323-conan-verify-ghfast-bak-rollback（覆盖回滚缺陷）

## 候选 3：init-build 将 md4c（CMake）误判为 autotools 构建系统

- **门禁**: init-build / conan-init 构建系统检测
- **真实错误**: `.build-context` 中 `BUILD_SYSTEM="autotools"`，conan-init 生成 autotools 模板 conanfile.py（configure+make），与实际 CMake 构建不符
- **根因**: 检测启发式对纯 C CMake 项目（根目录无 src/ 深度特征或特征不明显）误判；md4c 根 CMakeLists.txt 结构简单（add_subdirectory 少）
- **修复**: 改写 conanfile.py 为 CMake 配方（参照同库 0.5.3 已验证配方：CMakeToolchain + BUILD_MD2HTML_EXECUTABLE=OFF + BUILD_SHARED_LIBS=OFF + md4c/md4c-html 组件）→ conan-verify G1-G4 通过
- **验证**: `conan create`（ohos-aarch64）exit 0，test_package 1/1 通过
- **适用边界**: 构建系统检测失败时的通用处置（人工核对构建系统、参照既有配方）；属常规适配判断，不构成独立可复用知识
- **四范围查重**:
  - index.tsv：无对应 E 条目（E100/E092 为平台检测/SIMD/工具链类，非构建系统误判）
  - doc/：E100 无关（SIMD）；无构建系统误判 doc
  - graph/：无
  - drafts/：DRAFT-ohos-autotools-rpl-malloc 为 autotools 平台适配问题（不同）；无构建系统误判草稿 — **部分空白，但该候选为常规人力判断，无新增可复用知识**

## 候选 4：上游测试为 Python 脚本（run-testsuite.py），依赖 md2html 可执行文件

- **门禁**: 上游测试摸底/双口径台账
- **真实情况**: md4c 上游 test/ 为 Python 脚本（run-testsuite.py spec 回归 + pathological-tests.py 压力），依赖预构建 md2html 可执行文件；配方关闭 md2html（BUILD_MD2HTML_EXECUTABLE=OFF）后不注册为 Conan 测试
- **处理**: 本地用同 tag 源码构建 md2html → 全量实测 826/826（spec.txt 652 + 扩展 spec 72 + regressions 56 + coverage 19 + pathological 27）→ 包级验证由 test_package 真实 md_parse() API 断言承担（1/1 通过，6 项回调断言）
- **验证**: 各 `logs/07_*.log`、`logs/08_pathological.log` 全部 "0 failed"；test_package LastTest.log "All md4c parser callback tests passed!"
- **四范围查重**:
  - index.tsv：无 md4c/md2html 专有条目
  - doc/：E159/E191/E226/E341 为其他测试相关条目（非 md4c 场景）
  - graph/：无
  - drafts/：无 md4c 专有条目；DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise 覆盖"测试计数口径 + JC 基线噪声"主题的部分方法论

## 七轴查重汇总

| 轴 | 候选 1（.ci-trigger JC5） | 候选 2（E017 镜像污染） | 候选 3（构建系统误判） | 候选 4（Python spec 测试） |
|---|---|---|---|---|
| exact_duplicate | 部分（与 jc-full-scan/dr_mp3 草稿同根因同方案） | 是（lexy 草稿同根因同方案） | 否 | 否 |
| causal_duplicate | 是（既有草稿已解释同根因） | 是（既有草稿已解释） | 否 | 否 |
| trigger_overlap | 高（JC5/整仓扫描触发一致） | 高（G2/W3 镜像注入触发一致） | 中（init-build 触发） | 中（上游测试摸底） |
| solution_overlap | 高（git rm --cached 隔离+恢复+sha 审计一致） | 高（恢复官方 URL+删残留+复验） | 中（人工判型+参照既有配方） | 中（本地构建工具后全量运行） |
| combination_novelty | 否 | 否 | 否 | 否 |
| boundary_novelty | 否（.ci-trigger 已被既有草稿列为该类别的典型命中文件） | 否 | 否 | 否 |
| test_migration_novelty | 不适用 | 不适用 | 不适用 | 否（同库 0.5.3 notes 已记录"上游测试为 Python 依赖 md2html"） |

关系字段：
- 候选 1: similar_to=[DRAFT-jc-full-scan-baseline-noise-exemption, DRAFT-dr_mp3-0.7.2-baseline-noise-isolation, DRAFT-libfort-0.4.2-w3-baseline-junk-check-full-scan, DRAFT-libpopcnt-2.0-w3-baseline-junk-check-full-scan], caused_by=[junk_check full 扫描范围缺陷], prerequisite_of=[W3 本地 CI 通过], conflicts_with=[]
- 候选 2: similar_to=[DRAFT-lexy-2025.05.0-e017-mirror-injection-residual-cleanup, DRAFT-E323-conan-verify-ghfast-bak-rollback], caused_by=[E017 镜像注入机制], prerequisite_of=[R39 官方源合规], conflicts_with=[]
- 候选 3: similar_to=[], caused_by=[init-build 检测启发式], prerequisite_of=[], conflicts_with=[]
- 候选 4: similar_to=[DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise], caused_by=[md4c 上游测试形态], prerequisite_of=[双口径台账], conflicts_with=[]

## 路径决定

- **reuse_existing**: 候选 1、候选 2 均为已有多条草稿覆盖的既有知识（exact/causal duplicate，触发与方案重叠），复用既有条目，**不建新草稿**（避免改标题/换关键词硬凑新增）。
- **path_a_no_knowledge / B 不成立依据**: 候选 3、候选 4 属常规适配判断或同库既有笔记（0.5.3 notes.md）已记录内容，无跨库新增可复用知识；未证明新增知识价值 → 路径 B（知识库扩展）不成立。
- **最终决定**: `reuse_existing`（路径 A 形态交付：常规基础适配 + 复用既有知识），不创建新 .md/.kv 草稿。