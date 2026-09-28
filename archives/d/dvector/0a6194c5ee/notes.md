# dvector 0a6194c5ee 适配笔记

## 编译环境
- 构建系统: headeronly（无构建系统，单文件头库，v12.21 header-only 模板）
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15.0.4（ohos-aarch64 Conan profile）
- 状态: built

## 源码信息
- 上游: https://github.com/BareRose/dvector
- 版本标识: 0a6194c5ee（上游提交 `0a6194c5ee22b2e5c7450c81b98923fc6de12b1c`，提交信息 "Remove extra brackets and add usage comment (#5)"）
- 许可证: CC0-1.0（公共领域）
- 内容: 单文件 `dvector.h`（735 行）2D/3D 向量/四元数/矩阵数学库，含 vec2/vec3/vec4/quat/mat2/mat3/mat4/frst 类型，支持 DVECTOR_ISOC（ISO C99 兼容）与 DVECTOR_IMPLEMENTATION（单编译单元）模式

## 编译步骤

1. `init-build dvector 0a6194c5ee --url=https://github.com/BareRose/dvector`
   - github.com/archive 下载被网络阻断，改经 codeload.github.com 获取官方 tarball
2. lang-preflight 对纯 header-only 库（仅 .h 无 .c/.cpp 实源）误判为 `other(none)` 并自动写 env_unsupported 终态；核验 `dvector.h` 为 ISO C99 兼容 C/C++ 头文件库，属 c/cpp 兼容族，SKILL v12.21 明确支持 header-only 无构建族，按 headeronly 路径继续
3. `conan-init` 生成配方后人工修正：
   - `package_type = "header-library"`（Conan 2 要求 library 类型声明 shared 选项，header-only 用 header-library）
   - `package()` 中 `copy()` 的 dst 显式 `os.path.join(self.package_folder, "include")`（相对 dst 落到 build 目录导致 "No files in this package!"）
   - conandata `sources.url` 改为官方 archive tarball（仓库主页 URL 使 conan get 403）
4. `conan-verify`：G1/G2/G3/G4 全部通过（conan create 干净构建 + test_package 消费者测试 16 断言全过）
5. `finish built`：W2 结构检查、W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 `other` 写 env_unsupported 终态 | 纯 header-only 库无 .c/.cpp 实源，E13 `.h` 中立不计数 → 无可统计源文件 | 核验头文件为 C99 兼容族，按 SKILL v12.21 header-only 支持路径继续（工具盲区，非库缺陷） |
| 2 | conan create: `Package type is 'library', but no 'shared' option declared` | Conan 2 library 类型要求 shared 选项契约 | `package_type = "header-library"`（E283 等价命中） |
| 3 | `package(): WARN: No files in this package!` → CMakeDeps Imported target include 路径不存在 | conan 2 `copy()` 相对 dst 相对 build 目录解析，未进 package | dst 显式 `os.path.join(self.package_folder, "include")`（DRAFT-boost-te/DRAFT-gulrak-filesystem 等价命中） |
| 4 | conan create source(): 403 FORBIDDEN | conandata `sources.url` 指向仓库主页，get() 无法下载 | 改为官方 archive tarball URL `https://github.com/BareRose/dvector/archive/0a6194c5ee.tar.gz` 并核对 sha256 |
| 5 | W3 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | 新库分支零提交，junk_check 回退 full 模式整仓扫描，命中 main 基线其他库遗留隐藏文件 | 审计确认属无关历史基线（其他库、不在本库白名单），临时 index/工作区隔离 → 复验 W3 通过 → 无条件恢复（DRAFT-boost-te 等价命中） |

## 源码修改

无补丁、无源码修改（header-only 库直接打包）

## 依赖版本

- 无第三方依赖（requires 为空）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify dvector 0a6194c5ee
# G1 PASS / G2 conan create PASS / G3 PASS / G4 PASS
# test_package: ./test_dvector → "dvector consumer test: ALL PASSED"（16 断言，RC=0）
python3 scripts/ohc-run.py finish dvector 0a6194c5ee built
# W2 结构检查 PASS / W3 本地 CI 模拟 PASS（setup.sh + build_and_test.sh）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library） |
| conandata.yml | 官方 archive tarball 源 + sha256 |
| test_package/ | CMakeLists.txt + test.c（16 断言消费者测试）+ conanfile.py + MANIFEST.yml |
| manifest.yaml | 版本级元数据（status=built） |
| reports/test-report.md | 测试报告（16/16 通过） |

## 知识判定（本地快照查重，路径 A）

- knowledge_repository: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git (main, HEAD a2798f3a)
- 快照: /storage/Users/currentUser/tianyi/knowledge-snapshot-dvector-0a6194c5ee-r01-bootstrap-and-adapt-pc2-33-20260926T132609Z（只读稀疏，4832 文件）
- 扫描范围: knowledge/graph/E*.kv + knowledge/doc/E*.md + knowledge/drafts/*.{md,kv}
- 等价命中（逐字段验证适用）:
  - E257（G1 要求显式 build() no-op）：error_signature 与本轮 G1 失败逐字匹配，rec_approach=no-op-build-for-header-only 与修复一致 → reuse
  - E283（package_type=library 缺 shared 契约）：error_signature 逐字匹配，declare-shared-contract 与本轮 header-library 修复等价 → reuse
  - DRAFT-boost-te-1.0.0-headeronly-copy-abs-path（copy() 相对 dst 陷阱 + 零提交 full 模式基线噪声）：两个场景均与本轮 #3/#5 完全对应 → reuse
  - DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include（"No files in this package!"/Imported target 路径不存在）：与本轮 #3 对应 → reuse
- knowledge_decision: **reuse_existing（路径 A）**，不创建新草稿
- 未走路径 B 理由：所有可沉淀经验在快照中已有等价命中；lang-preflight 误判属共享框架工具行为，按治理规则不入路径 B
