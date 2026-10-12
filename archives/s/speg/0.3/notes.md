# speg 0.3 适配笔记

## 编译环境
- 构建系统: python（纯 Python 库——无 C/C++ 源码、无 autotools/CMake 构建系统）
- 编译日期: 2026-10-02
- 编译器: 不适用（无编译）
- 状态: built（conan-verify 全部通过；CNB upload 由 CI release 流水线执行）

## 编译步骤
纯 Python 库，无 configure/make。Conan 配方：
- `build()` 为 no-op（无编译）
- `package()` 把 `speg/` 目录拷贝到 `lib/python3/`（s3transfer 纯 Python 范式）
- `package_info()` 无 libs

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 Autotools 模板（configure+make） | 模板默认按构建系统生成 | 按 s3transfer 纯 Python 范式重写 conanfile.py（build=pass、拷贝 speg/ 到 lib/python3） |
| 2 | G1 门禁缺 export_sources() 和补丁应用调用 | G1 结构检查要求 | 增加 `export_sources()`（export_conandata_patches）+ source()/build() 中 apply_conandata_patches（patches 为空，no-op） |
| 3 | W3 L0k(R38) 要求 commands.json | package_type="application" 被当作 CLI 工具 | 改为 "python-require"（纯 Python 库先例 zipp/aetos）——speg 无任何可执行文件，正确不建 commands.json |
| 4 | W3 JC 垃圾文件误报（full 模式） | 本分支未提交 → `git diff origin/main...HEAD` 为空 → junk_check 回退 full 模式扫全仓 → 命中 origin/main 里历史遗留的 `.build-closed`/`.staging-verified`（cloog/kics/libbfio/thc） | 生成 `pr.diff` 模拟真实 CI 的 prdiff 模式（只扫本 PR 文件）——真实 CI 用 PR diff 不会扫到 main 存量文件 |
| 5 | manifest/notes 模板占位符残留 | close-archive 只填 status 字段 | 手工按 aetos 已归档 manifest 格式填充完整 |

## 源码修改
无补丁（patches/ 为空——纯 Python 直接拷贝，无需修改源码）。

## 依赖版本
无第三方依赖（上游 PKG-INFO 无 Requires-Dist）。

## 验证结果
```bash
# conan create（干净构建，含 test_package）——G2 通过
conan create archives/s/speg/0.3 -pr:h=ci/conan/profiles/ohos-aarch64 ... --build=missing
# test_package 消费者测试（R34）——3/3 断言通过
PYTHONPATH=<pkg>/lib/python3 python3 test_package/test_speg.py
# 上游 CI 冒烟（.travis.yml 同款）
python3 -c "import speg"
```

## 交付物
无打包产物（纯 Python 模块，随配方拷贝）。

## 注意事项
- 上游 v0.3 **无任何测试文件**（git tag v0.3 树 + PyPI sdist 双路核验，test_peg.py 在整个 git 历史中从未存在）；v0.3 CI 仅 `import speg` 冒烟。通过率如实记录（rule 4，不伪造），详见 UPSTREAM_TESTS.md。
- master 分支的 tests/（test_parser.py/test_position.py）是 v0.4+ 重写后的 API，与 0.3 不兼容，不能用于 0.3。
---

**编译结束**: 2026-10-02 17:34
**最终状态**: built
