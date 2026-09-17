# 知识候选台账 — libxmlplusplus 3.2.5（第一轮适配）

> 本台账按 SKILL 知识治理要求记录：每项非噪声候选的真实错误、根因、修复、验证、
> 适用范围、四范围查重结果与七轴查重结论，最后给出路径决定。
> 适配库：libxmlplusplus 3.2.5（上游 libxml++ 3.x 线，Meson 构建）。

## 一、候选清单

### C1. init-build 下载失败（OHOS /tmp 不可写）
- **真实错误**：`urllib` 下载官方 tarball 报 `Remote end closed connection` / curl 报
  `error 23: client returned ERROR on write`，写入 /tmp 失败（/tmp 挂载受限、写 0 字节）。
- **根因**：OHOS /tmp 目录不可正常写入（E002 平台限制）。
- **修复**：设置 `TMPDIR/TMP/TEMP=$HOME/tmp`，预下载 tarball 并注入 `EXPECTED_SHA256` 后
  重跑 init-build。
- **验证**：init-build 全流程通过，SHA-256 与官方一致（0c9b381b…）。
- **适用范围**：所有 OHOS 平台下载/构建落 /tmp 的工具链路径。
- **四范围查重**：graph/index.tsv **命中 E002**（/tmp 只读、TMPDIR、Permission denied）；
  doc/E002.md 已覆盖；drafts 无独立重复。
- **七轴查重**：exact_duplicate=true（E002 完整覆盖）。
- **结论**：**复用 E002，不新建草稿**。

### C2. MesonToolchain 用 profile 的 cppstd=17 覆盖项目 meson.build 声明默认（c++11）→ 需 tc.cpp_std 回退
- **真实错误**：libxml++ 3.2.5 的 meson.build 声明 `project(..., default_options: ['cpp_std=c++11'])`，
  但共享 profile `compiler.cppstd=17` 使 MesonToolchain 在 native file 的
  `[built-in options]` 写入 `cpp_std='c++17'`，直接覆盖项目默认（编译期行为与项目声明不符；
  对 2.x 线还会因 C++17 移除 auto_ptr 而编译失败）。
- **根因**：Conan `MesonToolchain` 的 cpp_std 取自 settings.compiler.cppstd（共享 profile 是
  17），它写入 native file 的 built-in options，优先级高于 meson.build 的 default_options。
  共享 profile 不能改，需在 recipe 内显式回退。
- **修复**：`generate()` 中 `tc.cpp_std = "c++11"`（与 libxmlpp 2.42.3 / glibmm 同款）。
- **验证**：conan create G2 PASS，meson setup 使用 c++11；conan-verify 8 门禁全 PASS。
- **适用范围**：所有用 MesonToolchain 且上游 meson.build 声明较低 cpp_std（C++11 时代
  GNOME C++ 包装家族：libxml++/glibmm/libsigc++ 等）的 OHOS 配方。
- **四范围查重**：
  - graph/index.tsv：**未命中同机制条目**；相近 E293（旧 C++ 代码 dynamic-exception-spec/
    register 编译错误，方案 `-Wno-error` 编译标志，不涉及 meson native file 通道）、
    E130（把 -std=c++11 改成 c++17，方向相反）、E538 draft（pangomm cxx17 profile，
    主题是 shared/options 冲突与包 ID，非 cpp_std 回退）。
  - knowledge/doc/：无 MesonToolchain cpp_std native file 覆盖条目。
  - graph/*.kv：E293.kv 仅覆盖 autotools/cmake 编译错误通道。
  - knowledge/drafts/：DRAFT-mesa-*（proc self exe）、E562（ar 注入）等均与本候选机制不同。
- **七轴查重**（详下）。

### C3. Meson native file 未声明 ar/ranlib → 注入 llvm-ar/llvm-ranlib
- **真实错误**：MesonToolchain 只映射 c/cpp，meson setup 探测定裸名 llvm-ar 失败风险。
- **根因**：clang 工具链在 /data/service/hnp/bin，不在 conan create 的 PATH 上。
- **修复**：`_inject_meson_archiver()` 从编译器目录推导并在 native file `[binaries]`
  写入 ar/ranlib 绝对路径。
- **验证**：conan create G2 PASS。
- **四范围查重**：**命中 E562 draft**（native file 未声明 ar 且 PATH 无 llvm-ar，触发实例
  c-stdaux；与 E012/E236/E296/E385 对比后确认本机制专有）。
- **七轴查重**：exact_duplicate=true（E562 草稿完整覆盖同一机制与方案）。
- **结论**：**复用 E562（已有草稿），不新建**。

### C4. 非交叉构建时 meson test 运行需注入依赖 libdir（g_libintl_* gettext 符号）
- **真实错误**：`meson test` 运行时 libglib-2.0.so.0 的 gettext 符号（g_libintl_*）无法解析
  → exit 127（CI 实测风险；本地探索构建亦有 LD 路径依赖）。
- **根因**：依赖包内 libintl 动态库不在默认加载路径。
- **修复**：build() 中 `LD_LIBRARY_PATH=<全部依赖包 lib dirs> meson test`.
- **验证**：meson test 4/4 OK。
- **四范围查重**：E123（meson 静态库 libintl g_libintl_ undefined symbol，链接期）、
  E107/E142（libintl 链接方案）、E120/E132（libxml2 LD_LIBRARY_PATH）部分相关；
  本候选聚焦「meson test 运行期注入依赖 libdir」。
- **七轴查重**：trigger_overlap=部分（LD 路径域）；solution_overlap=部分（注入依赖 libdir
  与 E120 同思路）；combination_novelty=false（机制简单，纳入配方注释即可）。
- **结论**：**复用既有知识（E120/E123），配方内注释记录，不新建草稿**。

### C5. 3.x 线依赖 glibmm-2.4（glibmm 2.66.x，非 2.68+）
- **真实错误**：meson `dependency('glibmm-2.4', '>= 2.32.0')` 需要 glibmm-2.4.pc；
  glibmm 2.68+ 提供 glibmm-2.68.pc（需 sigc++-3.0），不匹配。
- **修复**：requires("glibmm/2.66.9")（2.4 ABI 线最后提供者）。
- **四范围查重**：E538 draft（pangomm）提及 glibmm 但主题不同；libxmlpp 2.42.3 归档
  notes 已记录同款裁决（L3 本版笔记）。
- **结论**：**属于 2.42.3 已记录的家族知识延续，归档 notes 记录，不新建草稿**。

### C6. 3.x API 差异：get_child_text() → get_first_child_text()
- **真实错误**：`Element::get_child_text()` 在 3.x 移除，测试/消费者编译失败。
- **修复**：改用 `Element::get_first_child_text()` → `TextNode::get_content()`。
- **结论**：上游 API 演进，非 OHOS 平台知识；notes 记录，**噪声候选**。

## 二、C2 七轴查重明细

| 轴 | 判定 | 说明 |
|----|------|------|
| exact_duplicate | false | 四范围均无「MesonToolchain cpp_std 覆盖项目默认」条目 |
| causal_duplicate | 部分 | 与 E293 同源于 profile cppstd=17，但 E293 走编译错误→标志通道，本候选走 native file built-in options 通道 |
| trigger_overlap | 部分 | 同为 cppstd=17 触发，但触发点不同（编译期错误 vs meson setup native file 生成） |
| solution_overlap | 部分 | E293 用 toolchain-flag 降级警告；本候选用 tc.cpp_std 回退，机制不同 |
| combination_novelty | true | 「上游声明低 cpp_std 的 meson 项目 + MesonToolchain 从 profile 覆盖 + tc.cpp_std 回退」组合无既有方案 |
| boundary_novelty | true | 边界清晰：仅 meson + native file 通道受影响；autotools/cmake（AutotoolsToolchain/CMakeToolchain）不产生此覆盖 |
| test_migration_novelty | true | 可迁移至 glibmm/libsigc++/pangomm 等 C++11 时代 GNOME C++ 包装库 |


- **覆盖/新增差异**：E293 覆盖「旧 C++ 代码在 cppstd=17 下的编译错误 + 标志修复」；C2 新增
  「MesonToolchain 生成 native file 时用 profile cpp_std 覆盖 meson.build default_options，
  需 tc.cpp_std 显式回退」机制，未覆盖。
- **关系字段**：similar_to=E293,E130,E538；caused_by=无；prerequisite_of=无；conflicts_with=无。
- **适用边界/反例**：仅 MesonToolchain 且上游 meson.build 显式声明较低 cpp_std 时适用；
  上游未声明 cpp_std 或声明 c++17 的项目不受影响；改共享 profile 不可行（影响全局）时回退有效。

## 三、路径决定

- **reuse_existing**：C1（E002）、C3（E562 draft）、C4（E120/E123）、C5（2.42.3 notes 延续）。
- **new_draft**：C2（MesonToolchain cpp_std 覆盖回退）→ 已验证（conan-verify G2 全 PASS）、
  可跨库复用（GNOME C++ 包装家族）、查询未命中且存在新增差异 → **路径 B（知识库扩展）成立**。
- 已建立同 stem 草稿对：
  - `knowledge/drafts/DRAFT-libxmlplusplus-3.2.5-meson-cppstd-nativefile-rollback.kv`
  - `knowledge/drafts/DRAFT-libxmlplusplus-3.2.5-meson-cppstd-nativefile-rollback.md`
- **path_a_no_knowledge**：不适用（存在新增知识，路径 B）。

## 四、查重执行记录（命令与范围）

- 范围 1 graph/index.tsv：`grep -inE 'cpp_std|cppstd|c\+\+11|glibmm|libxml|meson.*archiver|native file|llvm-ar|gettext|libintl|TMPDIR|/tmp' knowledge/graph/index.tsv`
- 范围 2 knowledge/doc/：`grep -rinE 'cpp_std|MesonToolchain|glibmm-2\.4|libintl|g_libintl|llvm-ar' knowledge/doc/*.md`
- 范围 3 knowledge/graph/*.kv：`grep -rinE 'cpp_std|MesonToolchain|glibmm|libintl|g_libintl|llvm-ar' knowledge/graph/*.kv`
- 范围 4 knowledge/drafts/：`ls knowledge/drafts/ | grep -iE 'meson|cpp|cxx|glibmm|intl'`