# DRAFT-prebuilt-bindir-tool-relocated-runpath — 依赖包预编译构建期工具 RUNPATH 迁移失效，消费方须注入依赖包 libdir 到构建环境 LD_LIBRARY_PATH

- 申报域：构建系统语义 / 工具链行为（八分类内）
- 机理分层：L1 平台/构建系统语义（单库发现即可申报；阻塞面=构建失败，真实失败由 notes.md 问题表 #10 记录 + 本文双态探针复现）
- source run：cdemud-1.0.0（cdemu-daemon 1.0.0，2026-09 适配）

## 一句话规则

依赖包以预编译 ELF 形态交付的构建期工具（代码生成器），其 RUNPATH 常指向生产该包时的临时构建目录；Conan 包落库/迁移后该路径不存在，工具 DT_NEEDED 的第三方 .so 只能靠消费方构建环境解析——消费方 make 调用该工具前必须把 .so 所在依赖包 libdir 注入 build-scope `LD_LIBRARY_PATH`，否则 rc=127、构建中断。

## 机理链（三步，全部设备实证）

1. **工具形态**：dbus-glib/0.114 包交付的 `bin/dbus-binding-tool` 为 aarch64 OHOS ELF（`llvm-readelf -h`：`dynamically tagged aarch64, /lib/ld-musl-aarch64.so.1`），`DT_NEEDED libexpat.so`；expat 包在 OHOS 只发布 `lib/libexpat.so`（lib/ 内无 .a）。
2. **RUNPATH 失效**：`llvm-readelf -d` 显示 `RUNPATH=/storage/Users/currentUser/.cache/conan2/p/b/dbus-b2a06f5fb46b5/b/build-release/dependency-archives`——dbus-glib 配方自身构建期的临时目录，包迁移后不存在；loader 不再能经 RUNPATH 解析 libexpat.so。
3. **消费方触发**：cdemu-daemon 的 Makefile（BUILT_SOURCES）经 PATH 裸名调用 `dbus-binding-tool --prefix=cdemud_daemon --mode=glib-server …/cdemud-service.xml > ../src/cdemud-service-glue.h`（本 run CI 日志 rework-cdemud-only-console.log L346、cdemud-conan-create-standalone.log L401 可见实际调用）。无 LD_LIBRARY_PATH 时 musl loader 报 `Error loading shared library libexpat.so: (needed by …/bin/dbus-binding-tool)` + `XML_*: symbol not found`，rc=127 → make 失败。

## 阻塞面证据（构建失败）

- 真实失败记录：run 内 `archives/c/cdemud/1.0.0/notes.md` 问题表 #10（"make 期 dbus-binding-tool 报 Error loading shared library libexpat.so"）。
- 双态复现探针（自包含，2026-09-09 Curator 逐字实跑）：见 .kv `verification_cmd`——neg_rc=127 + 加载错误原文；`LD_LIBRARY_PATH=<expat 包>/lib` 时 pos_rc=0。该探针不依赖本 run 任何日志。

## 修复（rec）

消费方配方 `generate()`：

```python
env.append_path("LD_LIBRARY_PATH", os.path.join(self.dependencies["expat"].package_folder, "lib"))
```

随 `Environment` build script 落盘（cdemud 配方实际实现：`archives/c/cdemud/1.0.0/conanfile.py` generate()，"dbus-binding-tool is a prebuilt OHOS ELF … expat libdir must be on the loader path" 注释处）。只在构建会话生效，不污染 test_package/产物运行环境（P-ENV-001 作用域纪律）。

## fallback（诚实权衡）

一次性预生成 glue 头并以 conandata 注册补丁入源码树（见 .kv fallback_*），构建不再调用该工具。权衡：掩盖而非修复；生成物随上游 xml/工具版本漂移，仅作退路。

## forbid（反模式，带 reason/consequence）

1. 往 conan cache 包目录拷 .so"就地修复"——违反 cache 只读铁律（E236 族），副本失溯、干净构建再现。
2. 全局 export LD_LIBRARY_PATH 指向 cache 路径——泄漏进运行/测试环境，按目录序静默改依赖版本（P-ENV-001）。
3. patchelf 改写工具 DT_NEEDED/RUNPATH——破坏制品完整性与 OHOS 签名（DRAFT-patchelf-breaks-ohos-signing 同型风险）。

## 去重记录（摘要，完整版见 curation-report）

- `knowledge/graph/*.kv`：grep `dbus-binding-tool|binding.tool|genmarshal|marshaller|code.gen` 零命中；`LD_LIBRARY_PATH` 命中 E019/E073/E236/E266/E298 等 19 条，逐条比对均为运行期库加载、HMDFS symlink、la-free 归档、链接期缺库（clang/libxml2）、test_package env 等相邻面，无一条覆盖"构建期工具 ELF + RUNPATH 迁移失效 + 消费方构建环境注入"组合。
- `knowledge/drafts/`：grep `dbus|expat` 命中 DRAFT-expat-cmake-soname-1912（expat 自身 soname，不同问题）、DRAFT-upstream-test-runtime-libs / E318 OPENSSL-DYNLINK 等（运行/测试面 LD_LIBRARY_PATH），无构建期工具条目。
- 经验仓 `ophs_ci_review/`：grep `dbus-binding-tool|g_type_init` 零命中。
- 新增价值：诊断增量在"make 期 rc=127 + Error loading shared library lib<dep>.so (needed by <bindir 工具>)"→ 直接定位"依赖包预编译工具"而非产品库；修复范式可平移到一切"预编译工具 + 仅 .so 依赖"组合（E266 为同族链接期现象）。

## 挂钩

- principles：P-ENV-001（作用域纪律）、P-LINKAGE-001（OHOS 静态优先/expat 仅 .so 的背景）
- similar_to：E019（库加载失败家族，phase=runtime）、E236（dependency-archives/la-free 家族——RUNPATH 指向 dependency-archives 的成因）、E266（工具 ELF 缺 .so 的链接期同族现象）
