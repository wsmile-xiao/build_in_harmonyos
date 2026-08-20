# tree-sitter 0.25 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure)
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# tree-sitter 使用纯 Makefile，无需 configure
cd tree-sitter-0.25.work
export CC=clang CXX=clang++
make -j1
make install PREFIX=$HOME/tmp/test-install-tree-sitter-0.25
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连不通 | 网络限制 | 使用 git clone + Python urllib 下载 |
| 2 | sha256 不匹配 | API tarball 与 archive URL 返回内容不同 | 使用 conan 实际下载的 hash |
| 3 | make 找不到 Makefile | Conan build_folder 与 source_folder 不同 | 使用 `make -C {self.source_folder}` |
| 4 | 测试找不到 .so | package() 复制了 .so 但默认 shared=False | 按 options.shared 条件复制 |
| 5 | conf.get API 不兼容 | OHOS conan 2.29.1 无 tools.build:compiler_executables:c | 改用 os.environ.get("CC") |

## 源码修改

无补丁，tree-sitter 0.25.0 在鸿蒙平台上原生编译通过。

## 依赖版本

无外部依赖。tree-sitter 核心库是纯 C 实现。

## 验证结果

```bash
# conan-verify 全部通过
G1: PASS (配方完整性)
G2: PASS (conan create 干净构建)
G3: PASS (系统同名库隔离)
G4: PASS (产物完整性)
L2: PASS (smoke test)
L4: PASS (安全扫描)
L5: PASS (产物基线)
```

## 注意事项

- tree-sitter 上游测试套件需要 Rust/cargo 环境，跳过不影响核心 C 库
- tree-sitter 不是系统同名库，R26 不适用
- 构建产物包含 .a (静态) 和 .so (共享)，Conan 配方默认静态
---

**编译结束**: 2026-08-10 10:32
**最终状态**: built
