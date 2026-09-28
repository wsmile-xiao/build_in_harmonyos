# DRAFT-dnswire-0.5.0-protoc-c-missing-pregenerated-pb-c-exports-sources

> Contributor: pc4-25 | Status: Draft | Updated: 2026-09-26
> Source: dnswire 0.5.0 HarmonyOS PC adaptation
> (archives/d/dnswire/0.5.0, r01, task dnswire-0.5.0-r01-pc4-25-20260925T143830Z)
> 对应：knowledge/drafts/DRAFT-dnswire-0.5.0-protoc-c-missing-pregenerated-pb-c-exports-sources.kv

## 现象

dnswire 0.5.0（C 库，DNS encapsulations / DNSTAP protobuf / Frame Streams，
autotools 构建）在 OHOS 适配构建时：

```text
# configure 阶段
checking for protoc-c... no
configure: error: The protoc-c program was not found. Please install the protobuf-c compiler!
# 即使放宽 protoc-c 后，make 阶段
cp: bad 'dnstap.pb-c.h': No such file or directory
# 根因一：官方 codeberg tag tarball 不含子模块内容
$ ls src/dnstap.pb/     # 空目录（.gitmodules 声明了 dnstap.pb 子模块）
# 根因二：protoc-c / protoc / protoc-gen-c 在 OHOS 主机与 CI 均不存在
```

## 根因分析

1. **官方 tarball 不含 proto 子模块**：codeberg tag archive（git archive 产物）
   只导出被跟踪文件，`src/dnstap.pb` 子模块（`https://github.com/dnstap/dnstap.pb.git`）
   内容缺失——与 E150 / DRAFT-E616 / DRAFT-bandit-2.0.0 同根因，但 dnswire 的
   子模块内容是构建**必需**的 `.proto` 源（`dnstap.pb/dnstap.proto`），
   `src/Makefile.am` 的 codegen 规则 `dnstap.pb-c.c: dnstap.pb/dnstap.proto` 依赖它。
2. **protoc-c 编译器在 OHOS 构建主机/CI 不可用**：configure.ac 里
   `AC_PATH_PROG([PROTOC_C], [protoc-c])` + `AC_MSG_ERROR` 硬失败。
3. **Conan 依赖只解决运行库**：protobuf-c/1.5.1 提供 libprotobuf-c 静态库与头文件，
   但**不提供 protoc-c 编译器**（该配方 BUILD_PROTOC 只用于自测）。

与 ocserv/1.5.0（0004-pre-generated-protobuf-c-sources.patch，Meson 场景）不同，
dnswire 是 autotools 场景，且本项目 refresh-patch 批量重排会丢弃"新增文件补丁"，
因此本条目验证了更稳的 Conan 2 载体：**exports_sources + source() 落位**。

## 解决方案

1. **一次性预生成 pb-c 文件**（设备端，host 工具链）：
   - protoc：来自 ohpcd 制品仓 `protobuf/3.17.3` 包（`bin/protoc`，
     libprotoc 3.17.3 实测可运行）；
   - protoc-gen-c：protobuf-c 1.5.1 官方源码
     `cmake -DBUILD_PROTOC=ON -DBUILD_TESTS=OFF` 构建产出；
   - 生成：`protoc --plugin=protoc-gen-c=<path> --c_out=. -I <proto_dir> dnstap.proto`
     → `dnstap.pb-c.c` / `dnstap.pb-c.h`（与 dnstap.pb 子模块 commit 687347e1 对应）；
2. **配方携带**：`archives/d/dnswire/0.5.0/pregen/` 存 `dnstap.pb-c.c`、
   `dnstap.pb-c.h`、`m4/pkg.m4`；conanfile.py 声明 `exports_sources = "pregen/*"`，
   `source()` 内 `copy()` 至 `src/`、`src/dnswire/`（头文件放对 include 相对路径）、`m4/`；
3. **configure.ac 补丁**：protoc-c 硬失败改为可选——缺失时
   `AC_SUBST([PROTOC_C], [true])`；
4. **src/Makefile.am 补丁**：移除 `@PROTOC_C@` codegen 规则，改为
   `dnswire/dnstap.pb-c.h: $(srcdir)/dnstap.pb-c.h` + `cp $(srcdir)/dnstap.pb-c.h dnswire/`
   （out-of-tree 构建必须用 `$(srcdir)` 前缀）；
5. **conandata.yml 只声明修改文件补丁**（configure.ac + Makefile.am + 测试文件），
   新增文件不走 patches（避免 refresh-patch 重排丢失）；
6. `m4/pkg.m4`（pkg-config 0.29.2 官方 m4）同随 pregen 携带，解决干净环境
   autoreconf 报 `'pkgconfig_DATA' is used but 'pkgconfigdir' is undefined`
   （PKG_INSTALLDIR 宏未定义）。

## 验证

```bash
conan create archives/d/dnswire/0.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -tf test_package --user=ohpcd --channel=stable
# → conan create 通过；test_package（dnstap 编解码往返）PASSED
# → W3 本地 CI：L0（JC/junk_check）pass、L1 test_package pass、Pass rate 100%
# → 上游 make check 6/6 PASS（test5 另经 E461 abstract-socket 补丁）
# → 鸿蒙专项测试 16/16 PASS；消费者验证（consumer）编译链接运行 OK
```

## 适用边界与反例

- **适用**：autotools（或 CMake codegen 规则）依赖 protobuf-c 且构建期需要
  protoc-c 生成 pb-c、官方 tarball 不含 proto 子模块、OHOS 主机/CI 无 protoc-c
  的 C 库适配。
- **反例/边界**：
  - 若官方 tarball 自带 `.proto` 且构建主机可装 protoc/protoc-gen-c，应先走
    `tool_requires` 常规 codegen（本条目 O 载体成本更低但在自制工具链时不必）；
  - 纯 header-only 或不需要 pb-c 代码生成的目标不适用；
  - proto 子模块过大时，优先考虑锁定 submodule commit + conandata 多源
    destination（DRAFT-bandit 方案）以保持源码可追溯；本条目适合 pb-c 产物
    稳定且上游不锁定生成器版本的库。

## 四范围查重结论（七轴）

- **exact_duplicate**: false — 无既有条目描述"protoc-c 缺失 + 子模块 proto 缺失 + 预生成 pb-c 经 exports_sources 携带"的组合
- **causal_duplicate**: partial — E150/DRAFT-E616/DRAFT-bandit 覆盖"tarball 缺子模块"根因，但落在 **源码补齐**（多源下载），未覆盖生成器缺失与**预生成产物携带**的方案轴
- **trigger_overlap**: true — 与 E150/DRAFT-E616 共现 "submodule missing / No such file" 触发面，但 dnswire 首错是 `protoc-c not found`（工具链面）
- **solution_overlap**: partial — 与 ocserv 实践同属"预生成 pb-c"，但 ocserv 走 patches 且批次补丁有丢失风险；本条目走 exports_sources + source() 落位，机制不同
- **combination_novelty**: true — "protoc-c 不可用 + autotools codegen 规则 + exports_sources 预生成载体 + m4 宏随包"组合无既有条目
- **boundary_novelty**: true — 明确了适用边界（tarball 无 proto / 无 protoc-c / autotools）与反例（有 proto 或可装工具链时走 tool_requires）
- **test_migration_novelty**: true — test_package 中 consumer 端"仅用已导出头文件编解码往返"的验证方式可迁移至其他 protobuf-c 消费者库

- **similar_to**: E150（tarball 缺 submodule）、E461（OHOS socket 能力矩阵——同次适配的另一条知识）
- **caused_by**: —（无上游内因）
- **prerequisite_of**: —（暂无后续条目）
- **conflicts_with**: —（无冲突）

## 决策

- knowledge/doc：未命中（E150 只覆盖子模块源码补齐，未覆盖生成器缺失+预生成产物载体）
- knowledge/graph：未命中（E150 为 manual-download，E461 为 socket）
- knowledge/drafts：未命中（DRAFT-E616/bandit 覆盖源码补齐分支，未覆盖本组合）
- index.tsv：未命中
- **路径决定：B（new_draft）** — 任一候选已验证、可跨库复用、查重未命中且存在新增差异；
  建同 stem .md/.kv 草稿，随 dnswire PR 交付。若主编评估认为与 E150/bandit 合并更优，
  可 promote 时 merge-into，不影响本轮交付。