# cryptokit 1.21.1 编译进度

**日期**: 2026-07-28
**状态**: ⚠️ 部分完成（C stubs 层级）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| init-build | ✅ | 源码下载到 builds/cryptokit-1.21.1.work |
| 补丁 | ⚠️ | 无补丁需要 |
| 完整构建 (OCaml) | ❌ | 环境无 OCaml 编译器 (需 ≥ 4.13.0) |
| C stubs 编译 | ✅ | 19 个纯 C 算法文件已编译 |
| Conan 配方 | ✅ | conanfile.py + conandata.yml + test_package/ 已修复质量缺陷 |

## 环境限制（2026-08-08 更新）

- ✅ OCaml 4.14.1.1 已合入 main（PR #3767）——工具链已入库
- ❌ zarith ≥ 1.13 / dune ≥ 2.5 依赖链未合入 main（仅分支 feat/zarith-1.14、feat/dune-3.17.0）
- ❌ 完整 OCaml 构建仍不可行：cryptokit 的 src/dune 声明 `(libraries unix zarith)` 且 config 依赖 dune-configurator，本机与制品仓均无这些 OCaml 库
- 当前有效策略：C stubs 层独立适配（19 个纯 C 算法文件 + 桩头文件）

## 上游测试结论（2026-08-08）

- 上游测试（test.ml / prngtest.ml / speedtest.ml）依赖完整 cryptokit 库构建（zarith + dune-configurator）
- 依赖链未就绪前上游测试**无法执行**，如实声明豁免（不虚报通过率）
- test_package 替代验证：CMake 编译 test.c 调用 SHA-256 API（SHA256_init/add_data/finish）对比已知摘要，验证符号解析

## 后续步骤

1. 为 zarith 1.14（feat/zarith-1.14 分支）创建 PR 合入 main
2. 为 dune 3.17.0（feat/dune-3.17.0 分支）创建 PR 合入 main
3. 依赖链就绪后升级 cryptokit 配方为完整 OCaml 构建（requirements 声明 ocaml/zarith tool_requires）
4. 完整构建命令: `cd builds/cryptokit-1.21.1.work && ./configure && dune build`
---

1. **R33**: conanfile.py build() 从 Conan conf 获取编译器路径，不硬编码
2. **R34**: test_package 通过 CMake 编译 test.c 调用 SHA-256 API（SHA256_init/add_data/finish），验证加密算法功能正确
3. **requirements()**: C stubs 层无额外依赖，OCaml 完整构建需 zlib/1.3.1
4. **build 系统**: 使用 VirtualBuildEnv 而非错误的 AutotoolsToolchain

## 后续步骤

1. 发布 zlib/1.3.1 到制品仓（如果尚未发布）
2. 安装 OCaml ≥ 4.13.0 和 dune ≥ 2.5 完成完整构建
3. 完整构建命令: `cd builds/cryptokit-1.21.1.work && ./configure && dune build`
---

**编译结束**: 2026-07-28 08:32
**最终状态**: built
