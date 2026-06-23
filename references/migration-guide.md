# 软件迁移指南 — 迁移到 Conan 配方框架

> 本文档描述如何将一个软件迁移到 v3.0 Conan 配方框架。
> 适用于：新软件首次适配、旧软件从 manifest 模式迁移到 Conan 模式。

## 1. 迁移目标

每个软件的每个版本最终交付物：

```
archives/{letter}/{name}/{version}/
  ├── conanfile.py        # Conan 配方（CI 唯一构建输入）
  ├── conandata.yml       # 源码 URL + SHA256 + 补丁声明
  ├── test_package/       # Conan L1 测试
  ├── patches/            # 补丁文件（按需）
  ├── notes.md            # 适配笔记（AI 参考）
  └── reports/            # 验证报告（按需）
```

软件级文件：

```
archives/{letter}/{name}/
  ├── manifest.yaml       # 软件级元数据 + 版本索引 + 状态
  └── README.md           # 软件描述
```

## 2. 迁移流程

### Phase 1: 探索编译（AI 驱动）

```bash
# 1. 初始化构建上下文
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> <版本> --url=<源码URL>

# 2. 加载上下文，手动编译
source .build-context-<name>-<ver>
cd $BUILD_SRC_DIR

# 3. configure（根据构建系统选择）
# autotools: ./configure --prefix=$DEFAULT_PREFIX
# cmake:     cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..
# meson:     meson setup builddir --prefix=$DEFAULT_PREFIX
# makefile:  make

# 4. 编译 + 安装
make -j2 && make install DESTDIR=$TEST_PREFIX

# 5. 测试
make check
```

**探索阶段产出**：
- `notes.md` — 记录 configure 参数、遇到的问题、补丁用途
- `patches/*.patch` — 必要的源码补丁
- `.build-context` — 构建系统、源码路径、工具链信息

### Phase 2: 生成 Conan 配方

```bash
# 自动从探索结果生成 conanfile.py + conandata.yml + test_package/
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本> --force
```

**AI 必须检查生成的 conanfile.py**：

| 检查项 | 铁律 | 说明 |
|--------|------|------|
| `requirements()` | R27 | 依赖格式 `name/ver@ohpcd/stable` |
| `generate()` 静态链接 | R26 | `BUILD_SHARED_LIBS=OFF` / `-static` |
| `package_info()` | — | `cpp_info.libs` 列表正确 |
| `conandata.yml` sha256 | — | 必须是真实 SHA256，不能是占位符 |
| `test_package/` | R28 | 存在且类型正确（库/可执行文件） |

**常见需要手动修正的地方**：
- 补丁路径不正确 → 检查 `patches/` 目录与 `conandata.yml` 中的声明
- configure 参数缺失 → 从 `notes.md` 补充到 `generate()` 方法
- 依赖版本不对 → 检查 `requirements()` 中的版本号
- 可执行文件包的 `test_package/` 用了 CMake → 确认 `conan-init` 正确检测了包类型

### Phase 3: 本地验证

```bash
# 运行完整验证（7 道门禁 + 知识图谱）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>
```

**验证门禁**：

| 门禁 | 名称 | 失败处理 |
|------|------|---------|
| G1 | 配方完整性 | 补全缺失文件/字段 |
| G2 | conan create | 查看知识图谱建议（R30），修复 conanfile.py |
| G3 | 静态链接 (R26) | 在 `generate()` 添加静态链接配置 |
| G4 | 产物完整性 | 检查 `package()` 方法是否正确安装 |
| L2 | 平台 smoke test | 检查二进制是否能在 HarmonyOS 运行 |
| L4 | 安全扫描 | 检查 NX/PIE/RELRO（非阻塞警告） |
| L5 | 产物基线 | 首次运行保存基线，后续对比 |

**G2 失败时**：
- conan-verify 自动查询知识图谱（R30）
- 命中 → 展示修复方案，AI 按方案修复
- 未命中 → 自动生成草稿 `knowledge/drafts/DRAFT-*.kv`（R31），AI 审查后提升为正式 E-entry

### Phase 4: 收尾归档

```bash
# 完成归档（6 步自动）
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> built
```

**状态选择**：
- `built` — conan-verify 通过，未上传（AI 本地验证完成）
- `failed` — conan-verify 未通过（需修复后重试）

> ⚠️ AI 不要标记 `published`——那需要 CI upload 完成后由 CI 设置（R29）

### Phase 5: 提交 PR

```bash
# 创建功能分支
git checkout -b feat/<软件名>-<版本>

# 添加归档文件
git add archives/<字母>/<软件名>/<版本>/

# 提交
git commit -m "feat: add <软件名> <版本> conan recipe"

# 推送并创建 PR
git push origin feat/<软件名>-<版本>
# 在 GitCode 上创建 PR 到 main
```

### Phase 6: CI 验证（无 AI 参与）

PR 创建后，CI 流水线自动触发：

```
PR 校验流水线:
  setup.sh → build_and_test.sh (conan create + L4/L5 检查)
  → PASS: PR 可合并
  → FAIL: 需修复 conanfile.py 后重新推送
```

PR 合并到 main 后，正式发布流水线：

```
正式发布流水线:
  setup.sh → build_and_test.sh → upload.sh (conan upload 到 CNB) → sign.sh
  → 状态变为 published
```

## 3. 从旧框架迁移（manifest 模式 → Conan 模式）

### 3.1 旧框架特征

旧版本的归档只有 `manifest.yaml` + `notes.md` + `patches/`，没有 conanfile.py。

### 3.2 迁移步骤

```bash
# 1. 确认旧归档存在
ls archives/<字母>/<软件名>/<版本>/
# 应看到: manifest.yaml notes.md patches/ (可能还有 packaging/)

# 2. 清理废弃文件
rm -rf archives/<字母>/<软件名>/<版本>/packaging/
rm -f  archives/<字母>/<软件名>/<版本>/.verify-passed
rm -f  archives/<字母>/<软件名>/<版本>/.staging-verified

# 3. 生成 Conan 配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本> --force

# 4. 检查生成的 conanfile.py
# - 确认 requirements() 格式为 @ohpcd/stable (R27)
# - 确认 generate() 有静态链接配置 (R26)
# - 确认 conandata.yml sha256 不是占位符

# 5. 本地验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>

# 6. 修复验证失败项，重复 4-5 直到 PASS

# 7. 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> built
```

### 3.3 迁移注意事项

| 问题 | 处理 |
|------|------|
| manifest.yaml 的 source.url 与实际不符 | 以 .build-context 中的 URL 为准，更新 conandata.yml |
| 补丁在 conandata.yml 中声明但文件不存在 | 检查 patches/ 目录，删除无效声明 |
| 旧的 packaging/ 目录 | 删除，Conan 体系替代 |
| 旧的 .verify-passed 标记 | 删除，由 conan-verify 替代 |
| manifest.yaml 中 status 为 published | 降级为 built，需 CI 重新验证 |

## 4. 新软件适配流程

对于从未在 SKILL 中出现过的软件：

```bash
# 1. 搜索软件 URL
python3 $SKILL_ROOT/scripts/ohc-run.py search-url <软件名> <版本>

# 2. 初始化（使用搜索到的 URL）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> <版本> --url=<URL>

# 3. 探索编译（Phase 1）
# 4. 生成配方（Phase 2）
# 5. 本地验证（Phase 3）
# 6. 收尾归档（Phase 4）
# 7. 提交 PR（Phase 5）
# 8. CI 验证（Phase 6）
```

## 5. 版本级 manifest.yaml 的角色

### 当前角色

版本级 `manifest.yaml` 目前作为 `conan-init` 的输入数据源，包含：
- `source.url` / `source.sha256` — 源码信息
- `build.system` — 构建系统
- `configure_options` — 配置参数
- `dependencies` — 依赖列表
- `status` — 状态追踪

### 未来方向（待实施）

版本级 manifest.yaml 可逐步精简为**仅状态追踪**：
- `status` 和 `build_date` 移到软件级 manifest 的版本索引中
- `source.url` / `sha256` 已在 `conandata.yml` 中（CI 唯一真相源）
- `build.system` / `configure_options` / `dependencies` 已在 `conanfile.py` 中
- `conan-init` 改为从 `.build-context` + 软件级 manifest + `patches/` 读取数据

> 此变更需要重构 `conan_recipe.py` 的数据源，暂未实施。

## 6. 检查清单

迁移完成前，逐项确认：

- [ ] `conanfile.py` 存在且字段完整（name, version, source, build, package, package_info）
- [ ] `conandata.yml` 的 sha256 是真实值（非 `REPLACE_WITH_ACTUAL_SHA256`）
- [ ] `test_package/conanfile.py` 存在且类型正确（库包用 CMake，可执行文件包用 subprocess）
- [ ] `patches/` 中的补丁都在 `conandata.yml` 中声明
- [ ] 终端工具的 `generate()` 有静态链接配置（R26）
- [ ] 依赖引用格式为 `@ohpcd/stable`（R27）
- [ ] `conan-verify` 全部门禁 PASS（或已知非阻塞警告）
- [ ] `notes.md` 记录了适配过程和关键决策
- [ ] 软件级 `manifest.yaml` 的版本索引已更新
- [ ] PR 分支命名规范：`feat/<软件名>-<版本>`
