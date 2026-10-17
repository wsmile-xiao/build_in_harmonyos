# 知识候选台账 — imlib2 1.9.1（OHOS armv8 适配）

任务：imlib2-1.9.1-r01-pc4-23-20260916T133736Z；类型：知识库扩展。
范围：knowledge/graph/index.tsv（540 条目）、knowledge/doc/、knowledge/drafts/、
knowledge/graph/（.kv）四范围查重；七轴逐候选比对。

## 候选汇总与路径决定

| # | 候选 | 首错/根因 | 修复 | 验证 | 四范围查重 | 七轴结论 | 决定 |
|---|---|---|---|---|---|---|---|
| C1 | 无 X 图像库消费者需注入 X_DISPLAY_MISSING | Imlib2.h `#ifndef X_DISPLAY_MISSING` 守卫 X11 头，宏定义在 config.h（消费者不包含）→ 消费者编译报 X11/Xlib.h not found | package_info.cpp_info.cflags = -DX_DISPLAY_MISSING | test_package 消费编译链接运行 RC=0 | doc/E527/E530/E533 相关（无 X 测试/消费者验证）但**无条目讲消费者编译宏注入** | trigger_overlap: E530(弱: 测接口非编译宏)；solution_overlap: 低；combination_novelty: 高；boundary_novelty: 高；test_migration_novelty: 中 | **new_draft** |
| C2 | 依赖 .pc 名缺失/DESTDIR 损坏 → 桥接 .pc | configure.ac PKG_CHECK_MODULES(FREETYPE, freetype2) 要求 freetype2.pc；上游包内自带 freetype2.pc 是 DESTDIR 安装原始文件（prefix=/ → //include 无效）；配方未设 pkg_config_name → PkgConfigDeps 只生成 freetype.pc | PkgConfigDeps + 在 generators_folder 补写绝对路径桥接 freetype2.pc | conan-verify G2 PASS；configure 正确检出 FREETYPE/PNG/ZLIB | DRAFT-ncdc-1.25-glib-pc-name（glib-2.0.pc 缺失，同族）；E072/E089 相邻 | trigger_overlap: 高(与 ncdc: No package 'X' found)；solution_overlap: 部分（ncdc 补原生 pc，本候选补**绝对路径桥接**且含 **DESTDIR prefix=/ 检测**——新增差异） | **new_draft**（similar_to DRAFT-ncdc，新增差异：DESTDIR 破损 pc + 绝对路径桥接） |
| C3 | config.guess 不识别 OHOS 主机 | uname -s=HarmonyOS 无匹配 → unable to guess system type | 显式 --build=aarch64-linux --host=aarch64-linux（abiword 先例） | configure 通过；loader 正常检出 | E007/E072/E122/DRAFT-E564 覆盖错误面 | trigger_overlap: 全（同错误）；solution_overlap: 低（既有=patch config.guess；本=--host 绕过） | **reuse_existing**（E007 覆盖错误面；abiword 先例为标准解；边界差异记录见 notes.md） |
| C4 | 上游测试硬编码 BUILD_TEST=false 永不构建 | AM_CONDITIONAL(BUILD_TEST, false) | 最小补丁 0001 增加 --enable-test 开关 | test=True 构建并运行 9 个 gtest 可执行 | DRAFT-arduinojson（BUILD_TESTING=OFF 类）；DRAFT-no-upstream-tests（驱动真实接口类） | trigger_overlap: 中；solution_overlap: 低；boundary_novelty: 中 | **reuse_existing**（任务"源码测试入口恢复规则"已覆盖；L3 记录于 notes.md） |
| C5 | HMDFS config.status 临时目录不可写 | mktemp ./confXXXXXX + ac_tmp → Permission denied | 预建 TMPDIR + configure 内嵌 ac_tmp 重定向 + trap 修改 | configure 通过 | E114/E052/E060/E118/E125 全覆盖 | trigger_overlap: 全；solution_overlap: 全 | **reuse_existing** |
| C6 | git dubious ownership（conan 缓存目录） | HMDFS UID 映射致仓库 owner 不一致 | git config --global --add safe.directory '*' | source() 正常 | E101 全覆盖 | trigger_overlap: 全；solution_overlap: 全 | **reuse_existing** |

## 施

- C1、C2 判定为可跨库复用的新增知识（均已由本轮真实日志验证：conan create/
  conan-verify G2/test_package 实测通过），按路径 B 建立同 stem 的 .kv/.md 草稿。
- C3-C6 复用既有知识条目，不建草稿（避免标题/关键词硬凑）。
- 本库知识 L3（版本级）已写入 1.9.1/notes.md。

## 七轴定义核对（C1/C2 为例）

- exact_duplicate: C1 无（E530 系消费者测试而非编译宏）；C2 与 ncdc 草稿非同源库、
  非同因（ncdc=缺 glib pc；本=pc 存在但 DESTDIR 破损+名称不符），非完整重复。
- causal_duplicate: C1 否（E533 为整库适配汇总，无此子因）；C2 否（新增子因：
  DESTDIR 安装残留 prefix=/）。
- trigger_overlap: C1 弱/E530；C2 高/ncdc（同为 PKG_CHECK_MODULES 找不到 .pc）。
- solution_overlap: 均部分（无同款"绝对路径桥接 + macro 注入"既有方案）。
- combination_novelty: 均高（两候选在本仓库无同组合条目）。
- boundary_novelty: C1 高（OHOS 无 X + 公开头守卫宏的组合边界）；C2 高（conan
  generators_folder + 包内 pc name/DESTDIR 双坑）。
- test_migration_novelty: 中（消费者编译宏可迁移；桥接 .pc 可迁移）。

## 关系字段

- C2 similar_to: DRAFT-ncdc-1.25-glib-pc-name-autotools-ac-check-lib；
  prerequisite_of: 所有 PKG_CHECK_MODULES 消费 conan 依赖的 autotools 库。
- C1 related_to: E530（无 X 消费者验证）、E527（broadway 后端）。
- C3 related_to: E007、E072、E122、DRAFT-E564；C5 caused_by: E002（/tmp 只读系）。

## 适用边界/反例

- C1 反例：需 X11 的库（如 X 客户端库）不可 --without-x + 注入宏幻想绕过，
  必须按 E530 处理或提供 X 环境。
- C2 反例：依赖配方已正确设置 pkg_config_name 且包内 .pc 为 relocatable
  （${pcfiledir} 形式）时无需桥接——写桥接前必须先查包内 .pc 形态。
- C3 反例：configure.ac 含关键 AC_RUN_IFELSE 运行时探测（E007 注明）时，
  --host 绕过会跳过探测，需改用 config.guess/sub 补丁（E007/DRAFT-E564 路线）。

---

## r02 复核（返工新增候选，2026-09-17）

返工（上游测试 31/31）产生的经验证新候选，四范围查重后补建同 stem 草稿对：

| # | 候选 | 根因/首错 | 修复 | 验证 | 查重 | 决定 |
|---|---|---|---|---|---|---|
| C7 | loader 硬编码 /tmp 的源码级 $TMPDIR 修复 | decompress_load.c / loader_id3.c 硬编码 mkstemp("/tmp/...-XXXXXX")，/tmp 只读 → "Unable to create a temporary file"，ff.gz/jpg.mp3 加载失败；TMPDIR 环境变量对硬编码模板无效 | 源码级补丁：getenv("TMPDIR") 非空则用其拼模板，回退 /tmp | conan create test=True，LOAD2.load_1 通过 | trigger_overlap: E002（/tmp 只读）高；solution_overlap: 低（E002=设 TMPDIR 可解，本候选=硬编码模板需源码补丁）；boundary_novelty: 高 | **new_draft**（DRAFT-imlib2-1.9.1-loader-hardcoded-tmpdir.kv/.md） |
| C8 | 无 rgb.txt 环境 XPM 命名色解析失败 | icon-64.xpm 含命名色 "aX c white"，三处 rgb.txt 路径缺失 → r=g=b=0 → 全黑（直方图 p0=ff000000 vs gif ffffffff） | 内置 24 项常用 X11 颜色名表兜底（strcasecmp） | 修复后 xpm/gif/png 解码一致，LOAD2.load_1 通过 | 无既有条目；XPM 词命中仅内核代码页保护（无关）；combination_novelty: 高 | **new_draft**（DRAFT-imlib2-1.9.1-xpm-named-colors-builtin.kv/.md） |

七轴（C7/C8 共同）：exact_duplicate=否；causal_duplicate=否（E002 覆盖面=/tmp
只读本身，本两候选为 loader 侧硬编码模板/颜色名环境缺失的具体修复，均有新增
差异且经真实日志验证可跨库复用）；trigger_overlap=E002 高 / 其余无；
solution_overlap=低；combination_novelty=高；boundary_novelty=高；
test_migration_novelty=中（测试运行环境 TMPDIR/TMP/TEMP + 真实权限挂载点组合
可迁移，链至 C7 验证路径）。

关系：C7 similar_to E002/E052/E136；C8 similar_to E002；两者均
caused_by=OHOS 平台环境缺失（/tmp 只读、无 X11 数据文件），
prerequisite_of=无 X11 平台的图像/解压库。

适用边界/反例：
- C7 反例：代码用标准临时文件机制（尊重 TMPDIR）时仅设环境变量即可，无需补丁。
- C8 反例：XPM 仅用 #hex 色时无需兜底。

r01 既有草稿保持同 stem 配对不变（C1/C2）。本 PR 携带知识草稿共 4 对
（r01 2 对 + r02 2 对），全部随 archives/i/imlib2/ 同一 PR 交付。