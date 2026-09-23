# elfio 3.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-05
- 编译器: clang/clang++（OHOS SDK，aarch64）
- 状态: built

## 编译步骤

ELFIO 是 C++ header-only 库，使用 CMake 构建。release tarball 不含 tests/ 目录，
在 generate() 中禁用 examples 和 tests（`ELFIO_BUILD_EXAMPLES=False`、`ELFIO_BUILD_TESTS=False`）。

```bash
conan create archives/e/elfio/3.9/conanfile.py --name=elfio --version=3.9 \
    -pr:h=<worktree>/ci/conan/profiles/ohos-aarch64 \
    -pr:b=<worktree>/ci/conan/profiles/ohos-aarch64 \
    -s build_type=Release
```

安装产物：include/elfio/ 头文件 + CMake 配置文件 + licenses/COPYING。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 `Invalid: 'settings.os.version' value not defined` | 相对路径 `-pr=ci/conan/profiles/ohos-aarch64` 被 `~/.conan2/profiles` 同名嵌套旧副本遮蔽（无 os.version、libstdc++11） | 用绝对路径 `-pr:h=$(pwd)/ci/conan/profiles/ohos-aarch64 -pr:b=...` 强制指向官方 profile（知识候选 2 → DRAFT-elfio-3.9-conan-profile-relative-path-shadowing） |
| 2 | W3 本地 CI JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | 分支未提交时 junk_check 回退 full 整仓扫描，连坐其他库历史基线空文件（sha256=e3b0c442…） | 提交本库归档后 W3 走 incremental（9 文件）通过；基线路径原样保留、哈希记录（既有草稿 libfort/libpopcnt 已覆盖，复用） |
| 3 | 上游 ELFIO 测试编译失败 `'boost/test/included/unit_test.hpp' file not found` | release 包不含 tests/；tests/ 依赖 Boost unit_test_framework，本地无头文件且 registry 下载失败 | 依赖/基础设施阻塞，如实记录（0/36 全量通过率），不阻塞本库 header-only 交付 |
| 4 | HarmonyOS 专项测试编译报 `use of undeclared identifier 'EM_AARCH64'` | ELFIO 3.9 elf_types.hpp 未定义 EM_AARCH64（183） | 测试内本地 `#define EM_AARCH64 183`（L3 笔记，本库专属） |
| 5 | 上游 URL 需镜像 | github.com 直连超时 | 下载走 gh-proxy.com；conandata.yml 保留官方 HTTPS URL，CI 自动加镜像 fallback |
| 6 | /tmp 只读 | 平台限制 | 使用 $TMPDIR / worktree 内临时目录 |

## 源码修改

无补丁。ELFIO 是 header-only 库，源码无需修改即可在鸿蒙 PC 平台编译。

## 依赖版本

无依赖（header-only）。上游 tests/ 需 Boost unit_test_framework（缺失 → 依赖阻塞，已记录）。

## 验证结果

```bash
# conan-verify 门禁（G0-G4 + L2/L4/L5 全 PASS）
$ python3 ./scripts/ohc-run.py conan-verify elfio 3.9
# → All gates PASS

# conan create（test_package 双测试）
$ conan create archives/e/elfio/3.9/conanfile.py --name=elfio --version=3.9 \
    -pr:h=<worktree>/ci/conan/profiles/ohos-aarch64 -pr:b=<worktree>/ci/conan/profiles/ohos-aarch64 \
    -s build_type=Release
# → ELFIO version: 3.9
# → All ELFIO API tests passed!
# → HarmonyOS special test PASSED (real OHOS ELF parsed + aarch64 round-trip)

# W3 本地 CI（incremental 9 文件）
# → Junk Files: 0，L0/KC/JC 全 PASS
```

## 注意事项

- ELFIO 是 header-only 库，package_type 为 "header-library"，无编译产物
- conandata.yml URL 指向 GitHub 官方 releases 源（Release_3.9），SHA-256 767b269063fc35aba6d361139f830aa91c45dc6b77942f082666876c1aa0be0f
- 上游测试完整枚举见 reports/upstream-test-ledger.md（36 独立用例，0/36 因 Boost 缺失未运行）
- 知识路径：new_draft（候选 2 profile 路径遮蔽）→ 【知识库扩展】，见 knowledge-candidate-ledger.md---

**编译结束**: 2026-09-05 06:28
**最终状态**: built
---

**编译结束**: 2026-09-05 17:07
**最终状态**: built
