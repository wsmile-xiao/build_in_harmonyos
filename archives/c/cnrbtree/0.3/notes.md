# cnrbtree 0.3 适配笔记

## 编译环境
- 构建系统: makefile（上游 raw Makefile，无 configure）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (15.0.4, OHOS aarch64)
- 状态: built

## 编译步骤

1. `init-build cnrbtree 0.3 --url=https://github.com/cnlohr/cnrbtree/archive/refs/tags/v0.3.tar.gz`
   - 官方 tag v0.3（commit ce5a76f77b730367bdca9f4723b3b6e387ac9928）
   - SHA-256: da2912ea856a77fe609e35bc73411c45f4ba2248a59cbe2178c9c649011eb374
   - lang-preflight: detected=c（task=cpp，兼容族通过）
2. 编译上游测试/示例：
   - `make CC=clang testtree simple`（rc=0）
   - `./testtree`（rc=0，红黑树 3000x300 随机插入删除 + 不变量校验）
   - `./simple`（rc=0，README 示例）
3. 安装头文件：`cp cnrbtree.h $TEST_PREFIX/include/`
4. `conan-init cnrbtree 0.3`：生成配方骨架后按 header-only 变体 A 改写（package_type=header-library，
   无 build()，package() 拷贝 cnrbtree.h+LICENSE）
5. `conan-verify cnrbtree 0.3`：G1/G2/G3/G4 + L1/L4 全部 PASS（conan create 干净构建）
6. `finish cnrbtree 0.3 built`：W3 本地 CI 模拟通过（单包 JUNK_PR_DIFF 口径），状态 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make: gcc: No such file or directory` | 上游 Makefile recipe 内直接硬编码 `gcc`（无 CC 变量），OHOS 工具链仅 clang | 改写 recipe 为 `$(CC)`，`make CC=clang` 编译（补丁 0001-Makefile.patch） |
| 2 | conan-init 生成 Autotools 模板不适用 | cnrbtree 是单头文件库（CNRBTREE_IMPLEMENTATION），无 configure/编译产物 | 按本仓 header-only 变体 A 模式改写配方（参照 sse2neon/1.9.1） |
| 3 | W3 junk_check JC1 误拦 | full/incremental 模式扫描到 main 上其他库（cloog/kics）历史 `.staging-verified` 垃圾 | 生成本库单包 pr.diff，以 JUNK_PR_DIFF=pr.diff 口径重跑 W3（0 junk） |
| 4 | /tmp 只读 | OHOS /tmp 为只读挂载 | 使用 ~/tmp 作为工作目录 |

## 源码修改

- `patches/0001-Makefile.patch`：Makefile 两条 recipe 中 `gcc` → `$(CC)`
  （testtree 与 simple 目标；保留上游 -fsanitize=address,undefined 等标志）

## 依赖版本

- 无第三方依赖（header-only 库，仅需 C 编译器）

## 验证结果

```bash
make CC=clang testtree simple   # rc=0
./testtree                      # rc=0（含红黑不变量校验，输出 OK）
./simple                        # rc=0（7 == 7 / 1 == 1 / 0 == 0）
conan create (conan-verify G2)  # rc=0，test_package 1032 断言全 PASS
W3 build_and_test.sh            # L0 pass（单包口径）
```

## 上游测试台账

- 独立上游用例: 1（testtree.c，含 5 个断言块）→ 全量通过 1/1 (100%)
- 样例: simple.c（README example，非独立用例）→ 运行通过
- 完整双口径台账: reports/test-report.md

## 注意事项

- 本库为 header-only 库类型（无 CLI/无 bin 产物），按 R38 判定不需要 commands.json
- 知识候选: recipe 内嵌编译器（非变量形式）→ $(CC) 化（路径 B 新草稿，
  见 knowledge/drafts/DRAFT-cnrbtree-0.3-makefile-recipe-gcc-hardcode.kv/.md）

---

**编译结束**: 2026-09-22 00:41
**最终状态**: built
