# 贡献指南

> 如何为鸿蒙编译知识库添加新软件或改进现有内容。
> 对齐 SKILL.md v12.21 · Conan 配方体系

## 角色与权限

本项目采用 **协作者 / 主编** 双角色模式，通过 Git 分支 + GitCode PR 协作。

| 操作 | 协作者 | 主编 |
|------|--------|------|
| 编译软件（init-build, build） | ✅ | 不做 |
| 知识图谱草稿（graph add --draft） | ✅ | 不做 |
| 创建分支、推送、创建 PR | ✅ | 不做 |
| 合并/拒绝 PR（GitCode 平台） | ❌ | ✅ |
| 本地审核（review） | ❌ | ✅ |
| 修改 index.tsv / SUMMARY.md | ❌ 禁止 | ✅（合并 PR 时自动） |
| 修改 SKILL.md / references / templates / scripts | ❌ 禁止 | ✅ |

**身份声明**：
```bash
export OHC_AGENT_ID="A7F3"    # 协作者（4 位随机 ID）
export OHC_ROLE=editor        # 主编
```

---

## 贡献流程

### 方式 A：探索性编译（推荐，适合首次/复杂软件）

```bash
# 1. 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> <版本> [--url=URL]

# 2. AI 手动编译（唯一需要智能的步骤）
source .build-context-<name>-<ver> && cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j2 && make install DESTDIR=$TEST_PREFIX
make check

# 3. 生成 Conan 配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本>

# 4. 验证配方（8 道门禁）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>

# 5. 收尾归档
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed
```

**状态值**：
- `published`：conan-verify 通过 + CI upload 成功
- `built`：conan-verify 通过，未 upload
- `failed`：编译或验证失败
- `archived`：旧版本归档

### 方式 B：一键全流程

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py build <软件名> <版本>
# → 多阶段编译驱动（详见 SKILL.md §1.1 模式 A），含 Conan 配方生成+验证+收尾
```

### Conan 配方检查清单

`conan-init` 后 AI 必须检查：
- `requirements()`：依赖引用使用 `name/version` 格式
- `generate()`：系统同名库必须 `BUILD_SHARED_LIBS=OFF`（R26）
- `package_info()`：`cpp_info.libs` 正确声明
- `conandata.yml`：包含 sha256 校验
- `test_package/`：存在且包含可执行测试
- `settings.os` 判断必须 `in ("Linux", "OHOS")`，不能 `== "Linux"`（R32）

---

## 分支规范

### 分支命名

```
{type}/{软件名}-{版本}
```

- **type**：`feat`（新增）/ `fix`（修复）/ `update`（更新）
- 分支名**不加**任何随机 ID / AgentID 后缀（AgentID 仅用于知识图谱草稿归属，见 `graph add --draft`）

### 协作者 Git 铁律

- ❌ 不推 main，不走捷径：创建功能分支 → push → GitCode PR
- ❌ 不碰基础设施：SKILL.md / references/ / templates/ / scripts/ / ci/ / index.tsv / SUMMARY.md 只读
- ❌ 不碰他人归档目录
- ✅ 新增知识用 `graph add E{N} --draft`

---

## PR 规范

### 提交流程

```bash
# 1. 本地自检
python3 $SKILL_ROOT/scripts/ohc-run.py submit <软件名> <版本>

# 2. 创建分支
git checkout -b feat/<软件名>-<版本>

# 3. 暂存文件
git add archives/<首字母>/<软件名>/<版本>/
git add knowledge/drafts/    # 知识图谱草稿（如有）

# 4. 提交
git commit -m "feat(<软件名>): <版本> 编译完成"

# 5. 同步最新
git rebase main

# 6. 推送
git push origin feat/<软件名>-<版本>

# 7. 在 GitCode 创建 Pull Request
```

### PR 格式要求

- **单软件原则（W2，CI JC6 硬拦截）**：每个 PR **只允许提交一个软件**（一个 `archives/<首字母>/<软件名>/<版本>/` 目录及其知识图谱草稿）。多个软件 = 拆成多个 PR，CI 检测到多软件目录会直接拦截
- **标题**：`feat(<软件名>): <版本> 编译完成` 或 `fix(<软件名>): <版本> 修复描述`
- **描述三要素**：
  1. **变更内容**：新增/修改了哪些文件
  2. **质量状态**：conan-verify 结果
  3. **特殊说明**：补丁说明、依赖变更、已知问题等

### 主编审核

```bash
# 拉取并检出 PR 分支
git fetch origin && git checkout feat/<软件名>-<版本>

# 本地审核
python3 $SKILL_ROOT/scripts/ohc-run.py review <软件名> <版本>

# 通过 → GitCode Squash 合并 → git pull main
# 拒绝 → GitCode Close PR + 评论说明
```

PR 合并后主编自动执行：草稿→正式目录、重建 index.tsv、重建 SUMMARY.md。

---

## 归档结构

### 双层结构

```
archives/{首字母}/{软件名}/          # 软件级（跨版本共享）
├── manifest.yaml                   # 软件级元数据 + 版本索引
├── README.md                       # 软件描述
└── {版本}/                         # 版本级（每次编译快照）
    ├── conanfile.py                # Conan 配方【CI 输入】
    ├── conandata.yml               # 源码 URL + 补丁声明【CI 输入】
    ├── test_package/               # Conan 消费者测试【CI 输入】
    │   ├── conanfile.py
    │   ├── MANIFEST.yml            # 上游测试声明
    │   └── *.c / *.sh              # 测试源文件
    ├── patches/                    # 补丁文件【CI 输入】
    │   └── 0001-xxx.patch
    ├── manifest.yaml               # 编译元数据【AI 元数据】
    ├── notes.md                    # 适配笔记【AI 元数据】
    └── reports/                    # 验证报告【AI 元数据】
```

### 文件分类

| 分类 | 文件 | CI 读取 | AI 读取 |
|------|------|---------|---------|
| CI 输入 | conanfile.py / conandata.yml / test_package/ / patches/ | ✅ | ✅ |
| AI 元数据 | manifest.yaml / notes.md / reports/ | ❌ | ✅ |

> CI 只读 4 类文件，不读 manifest.yaml / notes.md / reports/。

### 补丁规范

- **命名**：`NNNN-{文件名}.patch`（0001 开始，连续编号）
- **格式**：unified diff，至少 3 行上下文
- **要求**：单一职责、可复现、可验证（`patch --dry-run -p1`）
- **生成**：`ohc-run.py refresh-patch --auto`（推荐）
- **禁止**：sed 改 configure/Makefile 等生成文件

### manifest.yaml 必填字段

```yaml
software: example              # 软件名称
version: 1.0.0                 # 版本号
status: published              # published | built | failed | archived
build_system: autotools        # autotools | cmake | meson | makefile | custom
compile_date: 2026-06-27       # YYYY-MM-DD
dependencies:
  required: []
  optional: []
patches_applied: []            # refresh-patch 自动填充
test_results:
  type: official               # official | manual | skipped
  total: N
  passed: N
  failed: N
knowledge_ref: []              # 引用的 E 编号列表
```

---

## 质量检查

### Conan 验证 8 道门禁

`conan-verify` 执行以下检查，全部通过才可标记 `published`：

| 门禁 | 名称 | 说明 |
|------|------|------|
| G0 | 预构建风险评估 | 知识图谱预查询，非阻塞 |
| G1 | 配方完整性 | conanfile.py + conandata.yml + test_package/ 存在且字段完整 |
| G2 | conan create | 从干净源码构建，验证配方自包含性 |
| G3 | 系统同名库隔离 | readelf -d 检查系统同名库未输出 .so 到系统路径 |
| G4 | 产物完整性 | bin/lib/include 产物检查 |
| L2 | 烟雾测试 | `--version` 可执行 |
| L4 | 安全扫描 | NX/PIE/RELRO |
| L5 | 产物基线 | SHA256 基线对比 |

> G2 失败时自动调用知识图谱引擎匹配错误模式。命中→展示根因+修复命令；未命中→自动生成草稿。

### CI 流水线

| 流水线 | 触发 | 执行步骤 | Upload |
|--------|------|---------|--------|
| PR 校验 | PR 创建/更新 | setup.sh → build_and_test.sh | ❌ |
| 正式发布 | PR 合并到 main | setup.sh → build_and_test.sh → upload.sh → sign.sh | ✅ CNB |

- CI 纯 zsh + conan，不依赖 ohc-run.py / 知识图谱 / 草稿机制
- Upload 安全边界：密钥仅存 CI 执行机，PR 校验不 upload

### 知识图谱贡献

编译过程中积累的经验以草稿形式提交：

```bash
# 添加知识草稿
python3 $SKILL_ROOT/scripts/ohc-run.py graph add E{NNN} --draft

# 独立运行引擎匹配
python3 $SKILL_ROOT/scripts/ohc-run.py engine "错误日志"
```

草稿写入 `knowledge/drafts/`，随 PR 一起提交，主编合并 PR 时自动移入正式目录并重建索引。

### 依赖管理

```bash
# 查看缺少的依赖
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps <软件名>

# 自动安装预编译包
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --install <软件名>
```

预编译包优先原则（R18）：编译过程中发现的任何依赖缺失，必须先查 cmd-pkgs 和 Conan 制品仓。

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [SKILL.md](SKILL.md) | 主操作手册（v12.21） |
| [KNOW_YOUR_WHY.md](KNOW_YOUR_WHY.md) | 核心设计理念与约束 |
| [docs/ADAPTATION_GUIDE.md](docs/ADAPTATION_GUIDE.md) | AI 适配操作手册 |
| [docs/TEST_QUALITY_SPEC.md](docs/TEST_QUALITY_SPEC.md) | 测试质量规范 |
| [references/iron-rules.md](references/iron-rules.md) | 52 条铁律详解（R1-R52） |

---

*对齐 SKILL.md v12.21 · 2026-09-03*
