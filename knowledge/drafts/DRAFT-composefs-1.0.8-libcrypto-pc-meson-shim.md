# DRAFT: meson dependency('libcrypto') 需 libcrypto.pc 垫片 — composefs 1.0.8 适配实证

## 问题
`conan create`（conan 2.29.1 + ohos-aarch64 profile）在 build() 的 meson configure 阶段报：
`meson.build:52:16: ERROR: Dependency "libcrypto" not found (tried pkg-config and system)`，
即使 openssl/4.0.1 已在依赖图中正确解析。

## 根因
Conan 2 的 PkgConfigDeps 对 openssl 按组件名生成 `openssl.pc / openssl-crypto.pc /
openssl-ssl.pc`，**不生成 libcrypto.pc**；而 composefs 的 meson.build 按 pkg-config 惯用名
写 `dependency('libcrypto')`。二者命名映射不一致，meson 无法通过 pkg-config 找到该依赖。

## 方案
配方 generate() 内（不提交本地路径）：从 `self.dependencies["openssl"].package_folder`
读取依赖包 prefix，生成 `libcrypto.pc`（prefix/libdir/includedir + `Libs: -L${libdir} -lcrypto`），
放入独立 pc 目录并 prepend 到 `tc.pkg_config_path`。可推广到任何"惯用 pkg-config 名 ≠
PkgConfigDeps 生成名"的 meson 依赖场景。

## 验证（本轮真实日志）
- `conan install --requires=openssl/4.0.1 -g=PkgConfigDeps`：仅生成 openssl*.pc，无 libcrypto.pc
- 垫片后：meson configure 通过（Dependency libcrypto found）；conan-verify G2 全过、
  test_package 消费者 exit 0

## 适用边界
- 适用：meson 构建 + conan 组件化依赖包（openssl 及其它按组件生成 .pc 的包）
- 反例：不应把垫片 .pc 提交进仓库（含本地绝对路径）；依赖包已发布时不得报 dependency_missing

## 查重差异（七轴摘要）
| 轴 | 结论 |
|---|---|
| exact_duplicate | 否（pkg_config_path/libcrypto.pc 关键词 0 命中） |
| causal_duplicate | 否 |
| trigger_overlap | 否（触发=meson configure 依赖解析） |
| solution_overlap | 否（generate() 内 .pc 垫片为新增方案） |
| combination_novelty | 是 |
| boundary_novelty | 是（PkgConfigDeps 命名映射边界） |
| test_migration_novelty | 是（conan-verify G2 实测迁移） |

关系：无 similar/caused_by/prerequisite/conflicts。
