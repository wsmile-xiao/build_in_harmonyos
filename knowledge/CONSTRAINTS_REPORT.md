# 流程遵从性报告
> 自动生成时间：2026-03-30 22:24
> 数据来源：SKILL.md v2.2.0 + KNOW_YOUR_WHY.md v2.2

---

## 📊 统计概览

| 指标 | 数值 |
|------|------|
| **约束总数** | **47** |
| 💀 致命级约束 | 19 |
| 🔴 严重级约束 | 12 |
| 🟡 重要级约束 | 10 |
| 🟢 建议级约束 | 6 |
| Phase 总数 | 6（Phase 0, 1, 1.5, 2, 3, 4） |
| Phase 3 子步骤数 | 7（含 3.1.5 嵌套子项） |
| 知识文件数量 | 24（knowledge/ 目录） |
| 脚本工具数量 | 11（scripts/ 目录） |
| 模板文件数量 | 8（templates/ 目录） |
| 已编译软件版本 | 28（26 款 / 28 个版本） |
| 错误模式数量 | 53（E001-E053） |

### 约束等级分布

| 等级 | 数量 | 占比 |
|------|------|------|
| 💀 致命级 | 19 | 40.4% |
| 🔴 严重级 | 12 | 25.5% |
| 🟡 重要级 | 10 | 21.3% |
| 🟢 建议级 | 6 | 12.8% |
| **合计** | **47** | **100%** |

---

## 💀 致命级约束（违反一次造成不可逆损失）

| # | 约束描述 | 来源 | 触发阶段 |
|---|---------|------|---------|
| D1 | **补丁完整性校验**：生成补丁前必须用 `diff -ruN original/ modified/` 比对原始源码和修改后的源码，逐条确认每个修改都生成补丁。不能仅凭对话回忆。 | KNOW_YOUR_WHY D1, SKILL §Phase4-3 | Phase 4 Step 3 |
| D2 | **知识库校验与补充**：Phase 4 Step 6 是校验+补充模式（非全量复盘）。必须扫描 PROGRESS.md 每个错误条目的知识库更新状态，补充遗漏的 L1/L2 知识。 | KNOW_YOUR_WHY D2, SKILL §Phase4-6 | Phase 4 Step 6 |
| D3 | **索引同步**：归档后立即运行 `python3 scripts/gen_summary.py` 更新 SUMMARY.md，并同步 _index.yaml status。SUMMARY.md 落后 = 检索体系崩塌。 | KNOW_YOUR_WHY D3, SKILL §Phase4-5 | Phase 4 Step 5 |
| D4 | **Phase 1.5 必须使用 templates/PROGRESS.md**：init-archive.sh 必须复制模板并填充变量，禁止脚本中硬编码模板。历史上三套不一致模板导致会话恢复时格式不可预测。 | KNOW_YOUR_WHY D4 | Phase 1.5 |
| D5 | **测试前置准备三步骤（强制）**：`make check` 前必须完成：(1) 预确认弹窗 `find $PREFIX/bin -exec {} --version` (2) 禁止并行 `MAKEFLAGS="-j1"` (3) 设置超时 `timeout 1800`。 | KNOW_YOUR_WHY D5, SKILL §Phase4-1 | Phase 3→4 转换 |
| D6 | **补丁校验在测试之前执行**：Phase 4 正确顺序为 补丁校验 → 测试 → 归档。测试可能修改编译目录状态导致 diff 不准确。 | KNOW_YOUR_WHY D6 | Phase 4 |
| D7 | **任务完成度评分卡（四维度全达标）**：编译产出 + 补丁完整性 + 知识提取 + 索引同步。四个维度全部必须达标才算完成。 | KNOW_YOUR_WHY D7 | Phase 4 完成判定 |
| D8 | **源码必须从官方一手源下载**：禁止使用第三方镜像或非官方源。确保代码与常规理解的功能匹配，避免安全风险。 | SKILL 强制规范, KNOW_YOUR_WHY I4 | Phase 0 |
| D9 | **执行官方测试套件（强制要求）**：必须运行 `make check` / `make test` 并记录结果。即使因环境限制失败也需明确记录原因，不是可选项。 | SKILL 强制规范 | Phase 4 Step 2 |
| D10 | **编译后必须验证核心功能**：不能只测试 `--version`。如 htop 需测进程显示，strace 需测实际追踪，rsync 需测文件同步。核心功能异常必须记录原因和解决方案。 | SKILL 强制规范 | Phase 4 Step 1 |
| D11 | **依赖软件独立归档**：编译依赖库（如 libpipeline 之于 man-db）必须作为独立项目创建归档（manifest.yaml + README.md），不能仅作为主软件归档章节。 | SKILL 强制规范 | Phase 3 |
| D12 | **打包验证完整性**：制作可移植包时必须对所有 ELF 文件（含 lib-dynload/ 扩展模块）设置 RPATH 并重新签名。不能仅处理主程序和主共享库。 | SKILL 强制规范 | Phase 4 |
| D13 | **Shell 脚本 POSIX 兼容**：所有 shell 脚本必须使用 POSIX 兼容语法（`#!/bin/sh` + toybox ash）。禁止 `${BASH_SOURCE}`、`[[ ]]`、数组等 bash 特性。 | SKILL 强制规范 | 全流程 |
| D14 | **Phase 1.5 不可跳过**：绝对不能等到 Phase 4 才创建档案目录。Phase 1.5 是会话中断后的恢复入口和"边做边记"机制的基础。 | SKILL §Phase1.5 | Phase 1.5 |
| D15 | **每解决编译问题必须立即更新 PROGRESS.md**：必须写入错误信息、阶段、根因分析、解决方案，并将每个源码修改记录到"源码修改清单"。 | SKILL §Phase3-5 | Phase 3 |
| D16 | **实时知识提取（Phase 3 Step 6）**：解决新问题后必须立即判断知识层级（L1/L2/L3），L1/L2 写入 knowledge/，L3 写入 manifest.yaml。禁止批量补记。 | SKILL §Phase3-6, KNOW_YOUR_WHY | Phase 3 |
| D17 | **configure 失败回退必须先清理环境**：不能直接重跑 configure。必须先 `make distclean` 或 `rm -rf config.cache config.status`。 | SKILL §Phase3-1.5 | Phase 3 |
| D18 | **KNOW_YOUR_WHY.md 必须在每次编译任务开始前读取**：回答"你为什么存在"和"绝对不能忘什么"。Phase 3→4 转换时再读一遍。 | SKILL 文件头, KNOW_YOUR_WHY | 任务启动 / Phase 3→4 |
| D19 | **Phase 3→4 转换是关键检查点**：编译成功的兴奋感会导致跳过 Phase 4。Phase 4 是知识增长的唯一途径，90% 知识提取在 Phase 3 完成，Phase 4 是质检+收尾。 | KNOW_YOUR_WHY | Phase 3→4 转换 |

---

## 🔴 严重级约束（违反导致编译失败或产物不可用）

| # | 约束描述 | 来源 | 触发阶段 |
|---|---------|------|---------|
| S1 | **软链接验证**：不能仅检查软链接是否存在，必须验证是否可执行。鸿蒙 SELinux 策略限制软链接，`ln -s` 创建的链接存在但执行报错。 | KNOW_YOUR_WHY S1, SKILL §6.4 | Phase 2/3/4 |
| S2 | **禁止使用 `ln -sf`**：会创建带随机后缀的文件。必须用 `rm -f link && ln -s target link` 方式。共享库 .so 必须用 `cp -p` 替代 `ln -s`。 | KNOW_YOUR_WHY S1, SKILL §6.4 | Phase 3/4 |
| S3 | **ELF 签名四步流程**：修改 ELF → 移除旧签名 → patchelf → 重新签名 → chmod +x。顺序不可变。范围：所有 ELF 文件（含 lib-dynload/）。 | KNOW_YOUR_WHY S2 | Phase 3.4/4 |
| S4 | **构建系统不欺骗**：永远不要伪造三元组来欺骗 configure。会导致构建系统对平台特性判断错误，二进制可能有隐藏问题。 | KNOW_YOUR_WHY S3 | Phase 3 |
| S5 | **知识证伪流程**：发现 L1/L2 知识与实际行为矛盾时，必须在 knowledge/ 文件中立即标注 `⚠️ DEPRECATED` 并指向正确方案。 | KNOW_YOUR_WHY S4 | Phase 3/4 |
| S6 | **manifest.yaml 禁止零值归档**：test_results、compile_date 等字段必须用实际数据填充。compile_date 用 `date +%Y-%m-%d` 自动获取，test_results 从测试日志解析。 | KNOW_YOUR_WHY S5 | Phase 4 |
| S7 | **依赖编译必须作为独立子任务**：Phase 3 发现缺少依赖时，创建独立子任务编译依赖。必需依赖失败→终止主任务；可选依赖失败→禁用功能继续。 | KNOW_YOUR_WHY S6 | Phase 3 |
| S8 | **子任务失败三级响应**：Level 1 自动重试 → Level 2 缩小范围 → Level 3 升级为父任务同步执行。 | KNOW_YOUR_WHY S7 | 多 Agent 编排 |
| S9 | **长任务中期盘点**：编译消息超过 30 条时，强制运行 `scripts/check-knowledge-gap.sh` 执行中期知识盘点，防止遗漏累积。 | KNOW_YOUR_WHY S8 | Phase 3 |
| S10 | **临时文件清理**：Phase 4 完成前必须删除 `DIAGNOSIS_*.md`、`MISSING_*.md`、`WORKFLOW_*.md`、`WORKPLAN_*.md`、`SCAN_*.md` 等临时文件。有价值内容整合进正式文件后再删除。 | KNOW_YOUR_WHY S9 | Phase 4 收尾 |
| S11 | **协作规范**：工作分支只修改自己负责的文件。禁止在分支上修改 `_index.yaml`、`SUMMARY.md`（只在 main 由主编生成）。索引用 `_meta.yaml`。 | KNOW_YOUR_WHY S10 | 多 Agent 协作 |
| S12 | **每个错误条目必须包含"跨软件通用性评估"**：PROGRESS.md 中每个错误必须标记 ✅ 是（通用）/ ❌ 否（仅本软件）/ ⏳ 待评估。 | SKILL §Phase1.5 | Phase 3 |

---

## 🟡 重要级约束（违反影响质量但不致命）

| # | 约束描述 | 来源 | 触发阶段 |
|---|---------|------|---------|
| I1 | **官方测试结果记录**：运行 `make check` 后需分析失败原因，区分"编译问题"vs"环境兼容性问题"，创建 `reports/test-report.md`。 | KNOW_YOUR_WHY I1, SKILL §Phase4-2 | Phase 4 Step 2 |
| I2 | **核心功能具体验证**：不能只测 `--version`。htop 测进程显示和 F 键，strace 测实际系统调用追踪，rsync 测文件同步功能。 | KNOW_YOUR_WHY I2 | Phase 4 Step 1 |
| I3 | **源码完整性校验（SHA256）**：下载后推荐执行 SHA256 校验。如果官方提供 checksum 则必须校验，无法校验时需明确记录。 | SKILL §Phase0-4 | Phase 0 |
| I4 | **编译目录使用 TMPDIR**：编译目录统一使用 `${TMPDIR:-$HOME/tmp}/builds/`，避免鸿蒙 /tmp 限制。 | SKILL §Phase0-3 | Phase 0 |
| I5 | **编译完成后不删除源码**：归档时记录 `source_dir` 路径。如需重新编译，从原始 tarball 重新解压（不用 `make distclean`）。 | SKILL §Phase0-存储规范 | Phase 0/归档 |
| I6 | **知识分层原则遵循**：L1 平台真理→knowledge/、L2 类别模式→knowledge/、L3 版本笔记→manifest.yaml。不确定时先标记"⏳ 待评估"。宁可多写 L1/L2，不降级。 | KNOW_YOUR_WHY, SKILL §3.5 | Phase 3/4 |
| I7 | **双向追溯**：L1/L2 知识写入 knowledge/ 后，必须在 manifest.yaml 中加 `knowledge_ref: knowledge/xxx.md#EXXX`。 | KNOW_YOUR_WHY | Phase 3/4 |
| I8 | **测试失败分类处理**：Permission denied（SELinux）→非功能问题；Symlink 相关→非功能问题；Assertion/Crash→必须修复；Timeout→检查 -j1。 | SKILL §Phase4-1 | Phase 4 |
| I9 | **补丁可干净应用验证**：生成补丁后必须 `patch --dry-run -p1 < patches/NNNN-xxx.patch` 验证。 | SKILL §Phase4-4 | Phase 4 |
| I10 | **configure 回退规范**：如果 configure 参数有误，不要直接重跑，必须先 `make distclean 2>/dev/null \|\| rm -rf config.cache config.status`。 | SKILL §Phase3-1.5 | Phase 3 |

---

## 🟢 建议级约束（最佳实践）

| # | 约束描述 | 来源 | 触发阶段 |
|---|---------|------|---------|
| A1 | **优先选择最新稳定版（LTS）**：如果用户指定了版本则用用户指定的；如果历史档案有版本记录则参考。 | SKILL §Phase0-1 | Phase 0 |
| A2 | **推荐使用工具脚本**：AI 应优先调用 scripts/ 封装脚本，而不是手动执行多步命令。节省 token 且减少出错。 | SKILL §5 | 全流程 |
| A3 | **编译失败增量修复**：修复源码后 `make -j1` 只编译修改过的文件。如不确定哪些文件受影响则 `make clean && make -j1`。 | SKILL §Phase3-1.5 | Phase 3 |
| A4 | **档案命名规范**：补丁文件 `NNNN-description.patch`（四位序号+描述）；报告文件 `{type}-report.md`；脚本小写+连字符。 | SKILL §6.2 | Phase 4 |
| A5 | **版本兼容性评估**：检索到相似版本时评估补丁可复用性——补丁版本（高）/ 小版本（中）/ 大版本（低）。 | SKILL §6.3 | Phase 1 |
| A6 | **init-archive.sh 一键创建**：推荐一条命令完成 Phase 1.5 全部工作（目录结构+manifest+PROGRESS.md+_index.yaml），而非手动执行多步。 | SKILL §Phase1.5 | Phase 1.5 |

---

## 🔄 Phase 流程遵从性清单

### Phase 0: 源码获取
```
Phase 0:
  进入条件: 无（任务启动即执行）
  必须执行:
    1. 确定版本（优先 LTS/最新稳定版/用户指定/历史记录）
    2. 确定下载地址（官方网站 Release 页面，GNU/PyPI 等）
    3. 下载源码（curl -fSL，保存到 ${TMPDIR:-$HOME/tmp}/builds/）
    4. 完整性校验（SHA256，如果官方提供 checksum）
    5. 解压源码（tar -xf）
    6. 记录 SOURCE_DIR=$(pwd)
  输出物: SOURCE_DIR 变量（源码根目录路径）
  验证点: ls SOURCE_DIR 存在且内容正确
  关联约束: D8（官方源下载）
```

### Phase 1: 检索历史知识
```
Phase 1:
  进入条件: 无（紧接 Phase 0）
  必须执行:
    1. 检查 archives/{首字母}/{软件名}/{版本}/manifest.yaml（精确匹配）
    2. 检查 archives/{首字母}/{软件名}/*/manifest.yaml（相似版本）
    3. 检索 knowledge/build-systems.md（构建系统知识）
  输出物: 编译方案（构建系统类型、关键参数、可复用补丁）
  验证点: 已确定构建系统类型和关键编译参数
```

### Phase 1.5: 创建骨架与进度文件
```
Phase 1.5:
  进入条件: Phase 1 完成，编译方案已确定
  必须执行:
    1. 创建目录 archives/{首字母}/{软件名}/{版本}/{patches,reports,scripts,logs}/
    2. 使用 templates/PROGRESS.md 创建 PROGRESS.md（禁止硬编码模板）
    3. 创建 manifest.yaml 骨架（status=compiling, build_system=确认后的类型）
    4. 创建 _meta.yaml（工作分支）/ 更新 _index.yaml（main 分支）
  输出物:
    - archives/{首字母}/{软件名}/{版本}/ 目录结构
    - manifest.yaml（骨架）
    - PROGRESS.md（从模板）
    - _index.yaml 更新（status=compiling）
  验证点:
    - manifest.yaml 文件存在且 status=compiling
    - PROGRESS.md 存在且格式与模板一致
    - _index.yaml 包含新条目
  关联约束: D4, D14（不可跳过）
```

### Phase 2: 环境准备
```
Phase 2:
  进入条件: Phase 1.5 完成
  必须执行:
    1. 检查环境变量（TMPDIR, CC, CFLAGS, DEFAULT_PREFIX）— 运行 scripts/check-env.sh
    2. 检查依赖工具（cc, make, ar）可用性
    3. 验证软链接可用性（scripts/verify-symlinks.sh）
    4. 准备编译目录结构
  输出物: 环境就绪确认
  验证点:
    - check-env.sh 通过
    - 所有必需工具可用
    - CC/CFLAGS/LDFLAGS 正确设置
  关联约束: S1（软链接验证）
```

### Phase 3: 编译执行（带实时记录）
```
Phase 3:
  进入条件: Phase 2 完成（环境就绪）
  必须执行:
    Step 1:   识别构建系统类型（scripts/detect-build-system.sh）
    Step 1.5: 错误分类与处理策略
              - configure 失败 → 先清理环境再重配（D17）
              - 编译失败 → 增量修复 make -j1
              - 链接失败 → llvm-readelf 分析依赖链
              - 安装失败 → wrapper 脚本替代软链接
    Step 2:   应用补丁（如有历史档案）
    Step 3:   执行编译命令
    Step 4:   执行 make install 并检查软链接（scripts/verify-symlinks.sh）
    Step 5:   更新 PROGRESS.md（每解决一个问题后立即执行）
    Step 6:   实时知识提取（判断 L1/L2/L3，立即写入对应位置）
  输出物:
    - 编译产物（$HOME/usr/local/ 下）
    - PROGRESS.md（实时更新）
    - knowledge/ 更新（如发现 L1/L2 知识）
  验证点:
    - make install 成功
    - 软链接验证通过（verify-symlinks.sh）
    - PROGRESS.md 每个错误条目已填写
    - 新发现的 L1/L2 知识已写入 knowledge/
  关联约束: D15, D16, D17, S7, S9, S12
```

### Phase 4: 验证与归档
```
Phase 4:
  进入条件: Phase 3 完成（编译成功或部分成功）
  必须执行:
    Step 1:   测试前置准备（D5）+ 验证编译产物
              - 预确认弹窗
              - 禁止并行 MAKEFLAGS="-j1"
              - 设置超时 timeout 1800
              - 验证可执行文件存在且可执行
    Step 2:   执行官方测试套件（make check）
              - 记录结果到 reports/test-report.md
              - 失败时区分编译问题 vs 环境兼容性问题
    Step 3:   补丁完整性校验（D1, D6）
              - diff -ruN original/ modified/ 比对
              - 确认每个源码修改都有对应补丁
    Step 4:   完善软件档案
              - 生成补丁文件
              - 验证补丁可干净应用（patch --dry-run）
              - 完善 manifest.yaml（实际数据填充）
              - 编写 README.md
    Step 5:   更新 SUMMARY.md（D3）
              - 运行 scripts/close-archive.sh
              - 运行 python3 scripts/gen_summary.py
              - 同步 _index.yaml status
    Step 6:   知识库校验与补充（D2）
              - 扫描 PROGRESS.md 中"⏳ 待评估"条目
              - 检查遗漏的 knowledge/ 更新
              - 补漏：回顾所有错误条目的知识库更新状态
              - 运行 scripts/check-knowledge-gap.sh
    Step 7:   临时文件清理（S10）
              - 删除 DIAGNOSIS_*.md, MISSING_*.md, WORKFLOW_*.md 等
  输出物:
    - patches/（完整补丁集，可干净应用）
    - reports/test-report.md
    - manifest.yaml（字段完整，status 更新）
    - README.md
    - SUMMARY.md（已更新）
    - _index.yaml（status 更新为 success/partial/failed）
    - PROGRESS.md（末尾追加了"编译结束"时间戳）
  验证点:
    - 所有补丁 patch --dry-run 通过（D1）
    - 测试结果已记录（D9）
    - manifest.yaml 无零值字段（S6）
    - SUMMARY.md 已由 gen_summary.py 重新生成（D3）
    - PROGRESS.md 无"⏳ 待评估"条目（D2）
    - 无临时 .md 文件残留（S10）
    - 四维度评分全达标（D7）
  关联约束: D1-D7, D9-D13, S2-S6, S10-S11, I1, I2, I8, I9
```

---

## 🔀 Phase 转换自检清单

### Phase 1 → Phase 1.5 转换前
- [ ] 已检索 archives/ 和 knowledge/？
- [ ] 已确定编译方案（编译系统、关键参数）？
- [ ] 准备好创建档案骨架？

### Phase 1.5 完成确认
- [ ] 创建了 archives/{首字母}/{软件名}/{版本}/ 目录？
- [ ] 创建了 manifest.yaml（software, version, status=compiling）？
- [ ] 从 templates/PROGRESS.md 创建了 PROGRESS.md？
- [ ] 更新了 _index.yaml（status=compiling）？

### Phase 2 → Phase 3 转换前
- [ ] TMPDIR 设置了？
- [ ] CC/CFLAGS/LDFLAGS 设置了？
- [ ] 依赖工具（cc、make、ar）可用？
- [ ] 已检索 archives/ 和 knowledge/？

### Phase 3 过程中（每个子步骤完成后）
- [ ] →Xa 实时记录：关键发现写入了 PROGRESS.md？
- [ ] →Xb 知识提取：判断了知识层级（L1/L2/L3）？
- [ ] L1/L2 知识已写入 knowledge/ 并添加 knowledge_ref？

### Phase 3 → Phase 4 转换前（⚠️ 最危险转换点）
- [ ] 编译成功了？还是部分成功？
- [ ] make install 产物的软链接都验证了？
- [ ] PROGRESS.md 的每个检查点都已填写？
- [ ] 准备好做"校验+收尾"工作？

### Phase 4 完成前
- [ ] 每个源码修改都有对应的补丁文件？（diff 校验确认）
- [ ] 补丁能干净应用？（patch --dry-run 验证）
- [ ] manifest.yaml 字段完整？knowledge_gained 和 knowledge_ref 都填了？
- [ ] PROGRESS.md 所有「知识库更新状态」已确认？
- [ ] SUMMARY.md 运行 gen_summary.py 更新了？
- [ ] _index.yaml status 已更新？
- [ ] 无临时文件残留？

---

## 🧠 遗忘风险评估

> 基于约束数量（47条）、Phase 复杂度（6个Phase、Phase 3 含7个子步骤）和实际失败教训评估。上下文压缩后，以下约束最可能被遗忘：

### 🔴 高遗忘概率（上下文压缩后几乎必然遗漏）

| 排名 | 约束 | 遗忘原因 | 补救措施 |
|------|------|---------|---------|
| 1 | **D1 补丁完整性校验**（diff 比对） | 编译完成后"感觉大功告成"，diff 步骤繁琐易跳过；需要保持原始源码目录（额外操作） | Phase 4 Step 3 强制在测试前执行；close-archive.sh 内置校验 |
| 2 | **D6 补丁校验在测试之前** | 顺序违反不易发现，测试修改编译目录后才暴露 | Phase 4 清单明确顺序 |
| 3 | **D16 实时知识提取**（Phase 3 Step 6） | 编译调试过程中专注于解决问题，知识提取"等做完再说" | KNOW_YOUR_WHY 明确"禁止批量补记"；check-knowledge-gap.sh 兜底 |
| 4 | **D4 必须使用 templates/PROGRESS.md** | 模板系统有多套历史残留，AI 可能从记忆中"生成"模板而非复制 | init-archive.sh 封装此逻辑 |
| 5 | **S10 临时文件清理** | 收尾阶段疲惫，"先到这里"心态 | Phase 4 完成清单包含此项 |

### 🟡 中遗忘概率

| 排名 | 约束 | 遗忘原因 | 补救措施 |
|------|------|---------|---------|
| 6 | **D5 测试前置准备**（三步骤） | 直接跑 `make check` 看似正常，弹窗和并行问题不总是出现 | Phase 3→4 转换检查点提醒 |
| 7 | **S1 软链接可执行性验证** | `ls -la` 看到链接存在就认为 OK，实际执行验证需要额外命令 | verify-symlinks.sh 自动化 |
| 8 | **D7 四维度评分卡** | 编译成功 = 任务完成的惯性思维 | Phase 4 完成清单 |
| 9 | **D3 索引同步**（gen_summary.py） | "不紧急"的错觉，不影响当前编译 | close-archive.sh 提示执行 |
| 10 | **S2 禁止 ln -sf** | bash 肌肉记忆，`ln -sf` 最自然 | §6.4 规范明确提醒 |

### 🟢 低遗忘概率（有自动化工具或强触发条件）

| 排名 | 约束 | 原因 |
|------|------|------|
| 11 | **D8 官方源下载** | Phase 0 第一步，失败即停 |
| 12 | **D14 Phase 1.5 不可跳过** | 有 init-archive.sh 工具触发 |
| 13 | **D9 执行官方测试** | `make check` 是标准步骤 |
| 14 | **S3 ELF 签名四步** | 不签名则无法运行，立即暴露 |
| 15 | **S6 manifest 禁止零值** | close-archive.sh 校验 |

---

## 📎 附录：文档间约束对照

| SKILL.md 强制规范 | KNOW_YOUR_WHY 对应项 | 最终等级 |
|-------------------|---------------------|---------|
| 软链接必须验证可执行性 | S1（严重级） | 🔴 严重级 |
| 源码必须从官方一手源下载 | I4（重要级）→ SKILL 标为强制规范 | 💀 致命级 |
| 执行官方测试套件 | I1（重要级）→ SKILL 标为强制规范 | 💀 致命级 |
| 编译后必须验证核心功能 | I2（重要级）→ SKILL 标为强制规范 | 💀 致命级 |
| 依赖软件独立归档 | 无直接对应 | 💀 致命级 |
| 打包验证完整性（所有 ELF） | 无直接对应 | 💀 致命级 |
| Shell 脚本 POSIX 兼容 | I3（重要级）→ SKILL 标为强制规范 | 💀 致命级 |

> **注**：当两份文档对同一约束的严重等级定义不一致时，本报告采用较高等级（SKILL.md "强制规范" > KNOW_YOUR_WHY "重要级"）。

---

*报告生成完毕。共提取 47 条约束（19 致命 + 12 严重 + 10 重要 + 6 建议），覆盖 6 个 Phase 和 5 个 Phase 转换检查点。*
