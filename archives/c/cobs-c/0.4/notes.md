# cobs-c 0.4 适配笔记

## 编译环境
- 构建系统: custom（官方源码无 configure/make/CMake，直接编译 C 源文件）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / llvm-ar
- 状态: built（conan-verify 全过，W3 100%）

## 编译步骤

1. 官方 tag `version_0.4` 源码（cobs.c/cobsr.c + cobs.h/cobsr.h + UnitTestC + UnitTestPython）
2. 本地编译验证：`clang -fPIC -O2 -c cobs.c` + `cobsr.c` → `llvm-ar rcs libcobs.a`
3. 上游 C 测试：`clang -fPIC -O2 -I. UnitTestC/main.c cobs.c cobsr.c -o unit_test_c && ./unit_test_c` → exit 0（12 组表驱动 encode 全过）
4. 上游 Python 测试：Python 2.x 套件最小移植到 Python 3.12（xrange→range、tostring→tobytes、str→bytes、cdll 精确名符号链接 + LD_LIBRARY_PATH）→ pytest 22/22 通过
5. conan-init 生成配方 → 手动改写 conanfile.py 为自定义编译（无构建系统纯 C 库）
6. conan-verify：G1/G2/G3/G4 通过（含 test_package 消费者测试 + R34 破坏性负向验证）
7. finish：W3 本地 CI 模拟通过（Pass rate 100%），补齐 test-report/packaging/.staging-verified
8. W3 基线隔离复验：JC 命中 main 基线中其他库（cloog/kics）的 3 个空运行时状态文件，
   记录路径与隔离前 SHA-256（均为 e3b0c442... 空文件），临时隔离、按 CI prdiff 口径复跑门禁、
   原样恢复并核对恢复后 SHA-256 一致（pre==post），未修改/未提交/未写入知识库或 PR

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub 仓库页返回 HTML | 仓库 URL 不是归档 | 用官方 tag 归档 `archive/refs/tags/version_0.4.tar.gz` |
| 2 | conan create 报 `no such file: cobs.c` | basic_layout 下源文件在 source_folder，build() cwd 是 build_folder | build() 内 `cd $source_folder && clang -c ... -o $build_folder/...` |
| 3 | G1 报缺 export_sources()/补丁应用 | conan-verify G1 强制方法声明（即使 0 补丁） | 补 export_conandata_patches/apply_conandata_patches 声明 |
| 4 | `tools.build:archiver` conf 不存在 | Conan 2.29 无此 conf | 归档器直接写 `llvm-ar` |
| 5 | Python 上游测试收集失败 | py2 代码（tostring/xrange/cdll 属性加载抛 AttributeError） | 最小移植 + 精确库名符号链接 + LD_LIBRARY_PATH |
| 6 | W3 JC 命中其他库基线空文件 | 全仓 full 扫描（本地 HEAD 落后 origin/main 三点 diff 为空回退 full） | 基线隔离复验 + prdiff 口径复跑（与 CI 一致） |
| 7 | /tmp 只读 | HMDFS /tmp 只读 | 用可写 TMPDIR（/storage/Users/currentUser/tmp） |

## 源码修改

无（0 补丁；配方层修改见 conanfile.py/manifest.yaml/test_package）

## 依赖版本

无第三方依赖（纯 C 单库，零依赖）

## 验证结果

```bash
# 上游 C 测试（exit 0）
./UnitTestC/unit_test_c
# 上游 Python 测试（22/22 passed, exit 0）
LD_LIBRARY_PATH=<so-dir> python3 -m pytest test_cobs.py test_cobs_c.py test_cobsr.py test_cobsr_c.py -v
# conan-verify（G1-G4 全过）
ohc-run.py conan-verify cobs-c 0.4
# W3 本地 CI（Pass rate 100%）
ohc-run.py finish cobs-c 0.4 built
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 自定义编译配方（无构建系统纯 C 库） |
| conandata.yml | 官方 tag 源 + SHA-256 |
| test_package/test.c | 消费者测试（cobs/cobsr 编解码闭环） |
| packaging/libcobs.a + 头文件 | 静态库产物 |
| reports/test-report.md | 测试报告（双口径） |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 七轴查重 |

## 知识引用

- knowledge/drafts/DRAFT-cobs-c-0.4-no-build-system-pure-c-conan-recipe.{kv,md}（Path B，C1）
- knowledge/drafts/DRAFT-cobs-c-0.4-py2-upstream-tests-py3-ctypes-cdll-port.{kv,md}（Path B，C2）

## 注意事项

- 库为纯静态库（shared=False），无 bin/ 产物 → 非 CLI 库，不需 commands.json
- W3 JC 命中的 cloog/kics 基线文件为 main 既有其他库文件，未纳入本库 diff/PR
---

**编译结束**: 2026-09-20 23:55
**最终状态**: built
