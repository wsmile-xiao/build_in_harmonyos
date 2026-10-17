# libnss-cache 0.22 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-27}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 知识判定（executor_local_required）

- knowledge_decision: reuse_existing（路径 A）
- 判定时间: 2026-09-27
- 扫描范围: 官方只读快照 knowledge-snapshot-libnss-cache-0.22-r01-bootstrap-and-adapt-pc1-34-20260927T082634Z（repository=gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git, ref=main, HEAD=c611f7d61b422eda200fc49481cf0d404e63f10c, sparse=knowledge）

候选 1：conan get() 对 codeload URL（末段为 tag 名无扩展名）解压报 BadZipFile → 命中 E276（error_signature 逐字段匹配：BadZipFile: File is not a zip file|codeload.github.com/.../tar.gz/refs/tags/vX.Y.Z；rec_approach=explicit filename in get()，与本轮修复一致）。另见 E483（explicit-filename-in-get）、E392（raw-makefile-conan-recipe-pattern 含 BadZipFile 陷阱）。逐字段适用性验证通过。

候选 2：OHOS profile tools.build:compiler_executables 为字典、raw makefile 需在 source_folder 执行 → 命中 E392（error_signature 含 KeyError.*compiler_executables|tools\.build:compiler_executables，rec_approach=raw-makefile-conan-recipe-pattern）。逐字段适用性验证通过。

候选 3：OHOS/musl 缺 <nss.h>/<gshadow.h> 且 fgetspent_r/fgetsgent_r 未声明，需 tree-local compat 头与 musl 派生重入解析器 → 无等价命中（graph/doc/drafts 均无 nss.h/gshadow 条目）；但该经验仅适用于 NSS 模块族库，跨库复用价值未证实，按规则走路径 A 记录 path_a_no_knowledge，不创建草稿。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 型配方（shared-library）|
| conandata.yml | 官方 codeload URL + sha256 8b13a2b0... + patches 列表 |
| patches/0001-ohos-musl-compat.patch | OHOS/musl 兼容补丁 |
| test_package/ | 实质 API 消费者测试 |

## 注意事项

- 上游 Makefile 默认 CC=gcc，配方以 Conan toolchain clang 覆盖（R33）
- 库产物为 libnss_cache.so.2，package() 额外复制无版本名 libnss_cache.so 供链接
- 官方标签 version/0.22 = commit 35d28bf60b7f
---

**编译结束**: 2026-09-27 19:59
**最终状态**: built
