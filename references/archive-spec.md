> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# 附录：归档规范与模板

来源: SKILL.md §6

---

## 6.1 标准归档目录结构（⭐ 强制规范）

> **每个归档必须包含以下文件。** ohc-run.py init-archive 创建骨架时应生成全部必填文件。

```
archives/{首字母}/{软件名}/                    ← 软件级（跨版本）
│
├── README.md              # ⭐ 必填：编译说明 + 平台适配要点（版本级）
├── RELEASENOTE.md         # ⭐ 必填：发布说明（软件级，聚合多版本）
│
└── {版本}/               ← 版本级（每次编译的快照）
    ├── manifest.yaml      # ⭐ 必填：元数据
    ├── PROGRESS.md        # ⭐ 必填：编译进展记录
    │
    ├── patches/           # ⭐ 必填：补丁目录
    │   ├── 0001-{file}.patch
    │   └── ...
    │
    ├── reports/           # ⭐ 必填：报告目录
    │   ├── test-report.md
    │   ├── skill-feedback.md
    │   └── quality-report.md
    │
    └── packaging/         # 🟡 预编译包（verify PASS 后必须）
        ├── {name}-{ver}-ohos-aarch64.tar.gz
        └── {name}-{ver}-ohos-aarch64-debug.tar.gz
```

### 必填文件内容规范

| 文件 | 最小内容要求 | 模板/参考 |
|------|-------------|----------|
| **manifest.yaml** | §6.2 全部字段 | ohc-run.py init-archive 自动生成 |
| **README.md** | 软件简介 + 构建命令 + 补丁清单 + 已知限制 + 验证方法 | 见下方模板 |
| **PROGRESS.md** | 各 Phase 状态(checkbox) + configure 参数 + 编译结果 + 源码修改清单表 | 见下方模板 |
| **test-report.md** | 测试套件类型 + 通过/失败数 + 失败原因分析(平台限制 vs 真bug) | 无固定模板 |
| **skill-feedback.md** | F编号列表(流程缺失/矛盾/脚本问题) + 严重度 + 建议 | §6.6 格式 |

---

## 6.2 manifest.yaml 必填字段

| 字段 | 说明 |
|------|------|
| software, version, status | 名称/版本/ success\|partial\|failed |
| build_system | autotools\|cmake\|meson\|makefile\|custom-perl |
| compile_date | YYYY-MM-DD |
| dependencies | required + optional 列表 |
| build_config | target/options |
| patches_applied | file + purpose（refresh-patch 自动填充） |
| patch_generation | hash 绑定（refresh-patch 自动填充） |
| build_cleanliness | standard_params_only + extra_params（P0 记录） |
| compatibility | level + issues + notes |
| test_results | type + passed + failed + note |
| knowledge_gained | 本次沉淀（L3 笔记） |

---

## 6.3 补丁命名规范

- 格式：`NNNN-{文件名}.patch`（四位序号 + 文件名）
- 例：`0001-config.sub.patch`、`0003-configure.patch`
- 内嵌依赖加前缀：`0004-glib-config.guess.patch`

---

## 6.4 知识分层表

| 层 | 归属 | 特征 | 写入时机 |
|----|------|------|---------|
| L1 平台真理 | `knowledge/*.md` | 任何软件都可能遇到 | Phase 3 实时 |
| L2 模式经验 | `knowledge/*.md` 章节 | 同类构建系统复现 | Phase 3 实时 |
| L3 本版笔记 | `manifest.yaml` knowledge_gained | 仅本软件本版本 | Phase 3+4 |

不确定时先标 `⏳ 待评估`，Phase 4 再决定。

---

## 6.5 PREBUILD_TODOLIST 依赖顺序

编译多款软件时，按此顺序执行（下层依赖上层）：

```
第零阶段: pkg-config
第一阶段: sed → coreutils → gawk          (无外部依赖)
第二阶段: automake → libtool             (Autotools 链)
第三阶段-A: zlib → bzip2 → xz → gzip    (压缩库)
第三阶段-B: openssl → ncurses → libffi   (SSL/终端)
第三阶段-C: gdbm → readline             (数据库/编辑)
第四阶段: wget → rsync → jq → file → tar → dos2unix  (网络/文件)
第五阶段: bash → htop → strace → patch   (高级工具)
第六阶段: texinfo → help2man → libpipeline  (文档/辅助)
第七阶段: man-db                          (文档系统)
```

> **注意**：使用 `ohc-run.py init-build` 时无需手动关注此顺序——单个软件的依赖在 registry 的 `known_issues` 中标注。批量编译时参考此顺序。

---

## 6.6 流程自省（skill-feedback.md 格式）

编译过程中发现 SKILL 自身问题时，记录到 `reports/skill-feedback.md`：

```markdown
### F{NNN}: {简短描述}
- 类别: 流程缺失 / 矛盾 / 脚本问题 / 导航错误
- 严重: 🔴🟡🟢
- 场景: {在哪步发现的}
- 建议: {怎么改}
```

Phase 4 归档时汇总 feedback 到 manifest.yaml `skill_feedback` 字段。

---

## PROGRESS.md 完整模板

> 📌 **权威模板源**: `templates/PROGRESS.md`。ohc-run.py init-archive 和此处定义均引用同一文件。修改模板时只需更新该文件即可全局生效。

```markdown
# {软件名} {版本} — 编译进度

> 档案创建时间: YYYY-MM-DD HH:MM:SS
> 最后更新: YYYY-MM-DD (当前状态)
> 当前会话 ID: (可选，用于多轮对话追踪)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | ... |
| 版本 | ... |
| 状态 | 🔵 进行中 / ✅ success / ⚠️ partial / ❌ failed |
| 构建系统 | autotools/cmake/meson/... |
| 源码路径 | URL |

## 二、编译阶段（checkbox 实时更新）

### Phase 1: 环境准备
- [ ] ohc-run.py init-build 完成 / 源码下载解压

### Phase 2: 编译（configure + make + make install 到 $TEST_PREFIX）
- [ ] configure 完成（--prefix=$TEST_PREFIX，记录参数和耗时）
- [ ] make 编译完成（记录错误和修复）
- [ ] make install 到 $TEST_PREFIX 完成

### Staging 验证（⭐ 必须做）
- [ ] $TEST_PREFIX 文件完整性检查
- [ ] 功能回归测试结果

### Phase 3: 测试验证
- [ ] make check / make test 结果
- [ ] 安全弹窗触发确认

### Phase 4: 预编译包制作（⭐ verify PASS 后必须）
- [ ] Step 1-10 打包流程（见 packaging.md）

### Phase 5: 归档收尾
- [ ] 补丁生成（ohc-run.py refresh-patch --auto）
- [ ] manifest.yaml / README.md / PROGRESS.md 更新
- [ ] ohc-run.py verify-build 质量门禁

## 三、对话记录（⭐ 断点续传核心）

> **每轮对话结束时必须更新此节。新 AI 会从这里恢复上下文。**

### 对话 #N — YYYY-MM-DD HH:MM
**操作**: （做了什么，如"执行 configure"、"修复 xxx bug"、"制作预编译包"）
**结果**: （成功/失败/部分成功，附关键输出摘要）
**发现的问题**: （遇到的坑、错误信息、根因分析）
**当前状态**: （精确到哪个步骤，下一步该做什么）
**遗留问题**: （未解决的、需要下轮继续的）

---

### 对话 #1 — YYYY-MM-DD HH:MM
**操作**: 执行 ./configure --prefix=$TEST_PREFIX
**结果**: ✅ 成功（~310秒），零额外参数
**发现的问题**: 无
**当前状态**: Phase 2 configure 完成，下一步执行 make
**遗留问题**: 无

### 对话 #2 — YYYY-MM-DD HH:MM
**操作**: make -j1 && make install DESTDIR=$TEST_PREFIX
**结果**: ✅ 成功，二进制已安装到 $TEST_PREFIX/bin/
**发现的问题**: 无
**当前状态**: Phase 2 完成，下一步 Staging 验证(§2.8) + make check
**遗留问题**: 无

（后续每轮对话追加...）

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| ... | ... | ... | ... |

## 五、预编译包交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| ... | ... | ... |

## 六、结束记录
- **最终状态**: ...
- **结束时间**: ...
```

---

## 文件命名统一表

| 用途 | 正确名称 | 禁止名称 |
|------|---------|---------|
| 测试报告 | `test-report.md` | `TEST_REPORT.md` `build-report.md` |
| 质量报告 | `quality-report.md` | （ohc-run.py verify-build 固定输出） |
| SKILL 反馈 | `skill-feedback.md` | `feedback.md` |
| 进展记录 | `PROGRESS.md` | `progress.md` `STATUS.md` |
d` `STATUS.md` |
