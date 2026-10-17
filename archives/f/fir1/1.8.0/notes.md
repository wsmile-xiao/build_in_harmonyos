# fir1 1.8.0 适配笔记

## 编译环境
- 构建系统: cmake (C++11, 静态库 libfir_static.a + 头文件 Fir1.h)
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64)
- 状态: published

## 编译步骤

```bash
# 官方源码 (tag 1.8.0)
#   https://github.com/berndporr/fir1/archive/refs/tags/1.8.0.tar.gz
#   SHA-256 d05d73cc534d28c754cc574b6b428d8b00012e5d4f7e00692031c146acf8d831
python3 scripts/ohc-run.py init-build fir1 1.8.0 --url=https://github.com/berndporr/fir1/archive/refs/tags/1.8.0.tar.gz

# 手动 CMake 编译验证 (Mode B)
cmake <src> -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<test-prefix> -DCMAKE_CXX_COMPILER=clang++
make -j4 && ctest --output-on-failure   # 6/6 通过
make install

# Conan 配方
python3 scripts/ohc-run.py conan-init fir1 1.8.0
python3 scripts/ohc-run.py conan-verify fir1 1.8.0   # G0-G4 + L2/L4/L5 全 PASS
JUNK_PR_DIFF=<worktree>/pr.diff python3 scripts/ohc-run.py finish fir1 1.8.0 published  # W2/W3/W5 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 fir1 为 python → env_unsupported | 根目录 setup.py (SWIG 绑定包装) 在 _manifest_scan 中优先于根 CMakeLists.txt；docs/ 下 22 个 Doxygen 生成 .js 计入 nodejs 统计 (nodejs:22 cpp:10 python:3) | 按 R47 边界规则人工复核：根 CMakeLists.txt project(CXX) + 10 个 .cpp + 6 个 ctest 为 C++ 主体，setup.py/fir1.i 为 SWIG 绑定、docs/ 为生成文档均非主体 → 判 cpp 继续适配 |
| 2 | CMake 4.x 拒绝 test/CMakeLists.txt `cmake_minimum_required(3.1.0)` | CMake ≥4 移除 <3.5 兼容 (E103) | 补丁 0001-test-CMakeLists.txt.patch 提升至 3.5；conandata.yml 注册 patch + strip:1 (E515) |
| 3 | finish W3 junk_check 拦截 | E017 镜像注入残留 conandata.yml.ghfast-bak + main 上其他库基线 .staging-verified (cloog/kics) | 清理残留；本地 W3 用 JUNK_PR_DIFF=pr.diff 单包口径，基线文件零改动 (SHA 前后一致) |
| 4 | conan-verify 首次 G2 失败 | patch 文件用 Git a/b 前缀但 conandata 未标 strip:1 | 按 E515 在 conandata.yml patch 条目加 strip: 1 |

## 源码修改

- `patches/0001-test-CMakeLists.txt.patch`：`test/CMakeLists.txt` cmake_minimum_required 3.1.0 → 3.5（CMake ≥4 兼容）

## 依赖版本

无第三方依赖（纯 C++11 标准库）。

## 验证结果

```bash
# 上游测试 (双口径)
#   source_declared_total=6  configured_executable_total=6  executed_passed_total=6  (6/6 = 100%)
ctest --output-on-failure  # 6/6 PASS; 逐项独立运行全部 rc=0
# HarmonyOS 专项测试 (tests-ohos/ohos_test.cpp): PASS
# 消费者验证 (test_package/test.cpp, 经公开 API + libfir_static.a): PASS
# conan-verify: G0-G4 + L2/L4/L5 PASS
# finish: W2 (PR 原子性) PASS, W3 (本地 CI) PASS, W5 (知识完整性) PASS
```

## 知识候选台账与七轴查重

### 候选 C1: lang-preflight 对"根目录 setup.py (SWIG 绑定) + docs/ Doxygen js"的 C++ 库误判 python

- **真实错误**: `detected_language=python`, `build_system=setuptools`, 自动写终态 env_unsupported
- **根因**: `_manifest_scan` 中 `setup.py` 命中优先级高于同层 `CMakeLists.txt`；`_source_stats` 未排除 docs/（22 个 Doxygen .js 计入 nodejs:22, 总 35, 主体 63% <70%）→ manifest python 胜出
- **修复**: R47 边界规则人工复核（根 CMakeLists project(CXX) + cpp 主体 → cpp），继续适配全流程通过
- **验证**: 按 cpp 完成 init-build→编译→6/6 上游测试→conan-verify G0-G4 PASS→W2/W3/W5 通过
- **适用范围**: 根目录同时存在 setup.py (SWIG/ctypes 绑定) 与 CMakeLists.txt 且 docs/ 含 Doxygen 生成物的 C/C++ 库

**四范围查重**:
| 范围 | 结果 |
|------|------|
| 正式条目 (doc/) | 未命中 (无 lang-preflight 误判正式条目) |
| 图谱 (index.tsv) | 未命中 (0 条 lang-preflight 相关) |
| 草稿 (drafts/) | 部分覆盖 (见七轴) |
| 运维知识 (memory) | 部分覆盖 (dshlibs 纯脚本误判) |

**七轴查重** (vs DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect / DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect / DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect / DRAFT-libcec-8.1.7-langpreflight-binding-subdir-misdetect / DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect / DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect):

| 轴 | 判定 | 说明 |
|----|------|------|
| exact_duplicate | false | 无任何既有条目与本签名完全一致 |
| causal_duplicate | false | 根因组合不同：根级 setup.py 遮蔽根 CMakeLists（libuninameslist 是 py/ 子目录内 setup.py + autotools；emio 是测试目录 Cargo.toml） |
| trigger_overlap | true | 同为 lang-preflight env_unsupported 终态触发 |
| solution_overlap | true | 同为 R47 边界规则人工复核判 cpp 继续 |
| combination_novelty | true | "根目录 setup.py(SWIG) + CMakeLists.txt + docs/Doxygen js"三者组合未见于既有条目；libuninameslist 建议的"仅顶层检索"修复对本签名无效（setup.py 本就在顶层） |
| boundary_novelty | true | 主体占比 <70% 时 manifest 直接胜出（判 python 而非 mixed）的路径未被既有条目覆盖 |
| test_migration_novelty | false | 无测试迁移成分 |

**关系**: similar_to: DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect, DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect, DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect; caused_by: lang_detect.py _manifest_scan 顶层 setup.py 优先 + _SKIP_DIRS 缺 docs; prerequisite_of: 无; conflicts_with: 无

**路径决定**: `new_draft` — 路径 B（知识库扩展）。已建同 stem 草稿: `knowledge/drafts/DRAFT-fir1-1.8.0-langpreflight-swig-root-setup-misdetect.{md,kv}`

### 候选 C2: CMake 4.x 拒绝 cmake_minimum_required <3.5

- 正式条目 E103 (bump-cmake-minimum-version) 完全覆盖（含相同错误特征正则）→ `reuse_existing`
- 附随问题: refresh-patch Git a/b 前缀补丁需 strip:1 → E515 完全覆盖 → `reuse_existing`

### 候选 C3: E017 镜像注入残留 conandata.yml.ghfast-bak 触发 W3 junk_check

- 草稿 DRAFT-E323-conan-verify-ghfast-bak-rollback 覆盖 → `reuse_existing`
- 其他库基线 .staging-verified 噪声 → 单包 JUNK_PR_DIFF 口径（与记忆运维知识一致），基线零改动

**路径决定总述**: C1 → `new_draft` (路径 B)；C2/C3 → `reuse_existing` (路径 A 知识复用)。非噪声候选均已登记并完成四范围查重。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/f/fir1/1.8.0/conanfile.py | Conan 2 配方 (CMake, 静态) |
| archives/f/fir1/1.8.0/conandata.yml | 官方源 + SHA-256 + patch 注册 (strip:1) |
| archives/f/fir1/1.8.0/patches/0001-test-CMakeLists.txt.patch | CMake 最小版本补丁 |
| archives/f/fir1/1.8.0/test_package/ | 消费者验证 (test.cpp 调公开 API) |
| archives/f/fir1/1.8.0/tests-ohos/ohos_test.cpp | HarmonyOS 专项测试 |
| archives/f/fir1/1.8.0/reports/test-report.md | 功能测试报告 (6/6 + 专项 + 消费者) |
| archives/f/fir1/1.8.0/packaging/README.md | 打包说明 |
| knowledge/drafts/DRAFT-fir1-1.8.0-langpreflight-swig-root-setup-misdetect.{md,kv} | 路径 B 知识草稿 |

## 注意事项

- lang-preflight 对"根级 setup.py 绑定 + docs/ 生成物"组合会误判 python：必须按 R47 人工复核根构建系统与主体占比，不得直接接受 env_unsupported 终态
- 本地 W3 需 JUNK_PR_DIFF=pr.diff 单包口径，防 main 上其他库基线垃圾误拦
- 提交前需清理 conandata.yml.ghfast-bak 残留

---

**编译结束**: 2026-09-19 13:19
**最终状态**: published
