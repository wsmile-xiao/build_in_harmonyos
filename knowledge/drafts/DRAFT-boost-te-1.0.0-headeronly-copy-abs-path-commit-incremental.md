# DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental — header-only 配方 copy() 绝对路径陷阱 + W3 零提交 full 模式基线噪声的 commit-first 规避

## 问题现象

boost-te 1.0.0（boost-ext/te，C++17 单头文件类型擦除库）在 OHOS armv8 上做
Conan 2.x 适配时，遇到两条与库本体无关、可跨库复用的配方/流程陷阱：

```
# (1) package() copy() 相对 dst → 头文件未进包 → test_package 配置期报错
CMake Error in CMakeLists.txt:
  Imported target "boost-te::boost-te" includes non-existent path
    ".../.conan2/p/b/xxx/p/include"   ← package 内没有 include/
  in its INTERFACE_INCLUDE_DIRECTORIES.

# (2) finish/W3 的 junk_check 回退 full 模式，命中其他库基线杂项
[FAIL] JC5: 1 个 archives 下未登记的隐藏文件:
       archives/u/util-linux-login/2.42.2/.ci-trigger   ← 不在本库 diff
JC_RESULT=fail / L0_RESULT=fail: junk_check failed
检查模式: full (52638 个文件)
```

## 根因分析

1. **copy() 相对 dst**：Conan 2 `copy()` 的 `dst` 为相对路径时相对**当前 build 目录**
   解析，而非 package 目录。header-only 配方 `package()` 若写
   `copy(self, "*", src=f"{self.source_folder}/include", dst="include")`，
   头文件被打进 build 目录，package 内无 include → CMakeDeps 生成的
   `INTERFACE_INCLUDE_DIRECTORIES` 指向 `package_folder/include`（不存在），
   test_package 配置期直接报 "Imported target ... includes non-existent path"。
2. **junk_check 模式选择链**：`pr.diff > incremental（git diff origin/main...HEAD）> full（git ls-files 整仓）`。
   新库分支若零提交，三点 diff 为空 → 回退 **full 模式**扫全仓，命中 origin/main 上
   其他库历史提交带入的跟踪杂项文件（如空 blob `.ci-trigger`，不在 JC5_ALLOWED
   白名单）→ JC5 fail 阻塞 W3。该文件不在本库 PR diff 内，真实 CI（pr.diff 模式）
   不会命中 —— 属**共享基线噪声**而非本库缺陷。

## 方案

1. **package() 的 copy() 一律使用绝对路径**（参照 ghc-filesystem 既有配方注释）：

   ```python
   def package(self):
       copy(self, "boost/*", os.path.join(self.source_folder, "include"),
            os.path.join(self.package_folder, "include"))
   ```

2. **新库分支先 commit 本库工作**，使 `git diff origin/main...HEAD` 非空 →
   junk_check 自动回退 **incremental** 只查本库文件 → W3 通过：

   ```bash
   git add archives/b/boost-te      # 只暂存本库路径
   git commit -m "feat(boost-te): ..."
   python3 scripts/ohc-run.py finish boost-te 1.0.0 published
   ```

   全程不 `git rm --cached` 其他库文件、不修改其他库、不伪造产物 —— 这是区别于既有
   baseline-noise 草稿（git rm --cached 隔离 → finish 复验 → git add 恢复）的
   **零副作用替代路径**。

## 验证（boost-te 1.0.0 本轮真实日志）

1. 绝对路径修复后 `conan create` G2 PASS；test_package 消费者/专项二进制编译、链接、
   运行全部退出码 0（adaptation_validation.log）。
2. commit 后重跑 finish：W3 "检查模式: incremental (9 个文件)"，`JC_RESULT=pass`、
   L0/L1 pass、Pass rate 100% (1/1)，状态 published（w3-local-ci.log）。

## 适用范围与边界

- 所有 header-only / copy-based 打包配方（绝对路径规则跨库通用）；
- 共享 build_in_harmonyos 仓库全部新库零提交分支的 finish/W3 流程；
- 边界：零提交 → full 模式（会被他库基线噪声误伤）；有提交 → incremental（只查本库）。
  若垃圾文件确属本库自身工作流标记且需保留，才走框架白名单登记（单独 PR）。

## 查重（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | partial（陷阱 (2) 与 dr_mp3/kdbusaddons baseline-noise 草稿根因同源） |
| trigger_overlap | true（陷阱 (2) 触发面与既有 baseline-noise 草稿相同） |
| solution_overlap | partial（绝对路径修复无既有记录；commit-first 与既有 git rm --cached 方案不同） |
| combination_novelty | true |
| boundary_novelty | true（零提交→full / 有提交→incremental 边界） |
| test_migration_novelty | false |

- similar_to: E257, E311, DRAFT-dr_mp3-0.7.2-baseline-noise-isolation, DRAFT-kdbusaddons-baseline-noise-isolation
- caused_by: [] / prerequisite_of: [] / conflicts_with: []
- 决定: `new_draft`（路径 B，与 boost-te 归档进同一 PR）
