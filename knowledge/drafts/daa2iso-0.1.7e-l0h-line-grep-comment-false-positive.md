# CI 的 L0h（R33）是行级 grep：注释里写 `self.run(` 与 `${CC}` 会被误判为失败

> Draft: `DRAFT-DAA2ISO-L0H-LINE-GREP-COMMENT-FALSE-POSITIVE`
> Stem: `daa2iso-0.1.7e-l0h-line-grep-comment-false-positive` — 与同 stem 的 `.kv` 成对
> 实例：detachtty 11.0.0（PR !9171）首次命中；规避写法已应用于 daa2iso 0.1.7e（PR !9360）

## 基本信息

- **ID**: DRAFT-DAA2ISO-L0H-LINE-GREP-COMMENT-FALSE-POSITIVE
- **严重度**: 2
- **类别**: ci-gate, false-positive, conan-recipe-style
- **触发工具**: ci（conan build_and_test.sh 的 L0h 门禁）
- **阶段**: verification（L0 质量门禁）

## 错误特征

```
o[step] L0j: Checking version collision with registry (R37)... [ok] version not in registry yet
o[step] L0k: Checking commands.json for CLI tools (R38)...      [ok] commands.json valid (type=tool)
o[step] L0m: Checking directory structure (R39)...              [ok] directory structure valid
o[step] L0n: Checking branch name matches package (R40)...      [ok] branch 'feat/detachtty-11.0.0' matches exactly
o[fail] L0h: conanfile.py 在 self.run() 中依赖未定义 shell 变量 ${CC} — 用 self.conf.get() 代替 (R33)
o[fail] detachtty/11.0.0 — L0 quality gate failed: shell_env_var_in_run
oL0_RESULT=fail: gate failed: shell_env_var_in_run
oL1_RESULT=skip: blocked_by_L0          ← L1 起全部被跳过
```

注意 **L0h 的输出位置在 L0j/L0k/L0m/L0n 之前**，说明它是先跑的批次；但它挂了以后
L1/L2/L4/L5 全部 `blocked_by_L0`，所以现象是"改了别的都还是红"。

## 可复现问题

`archives/d/detachtty/11.0.0/conanfile.py` 的 `build()` **代码本身完全合规**：

```python
def build(self):
    # R33: f-string 嵌入到 make 参数，不在 self.run() 里用 ${CC}/${CFLAGS} 展开   ← 第 39 行：注释
    cc = os.environ.get("CC", "clang")
    cflags = "-O2 -Wall -DNEED_PTY_H -fno-strict-aliasing"
    make_args = f'CC="{cc}" CFLAGS="{cflags}" LDLIBS=""'
    self.run(f"cd {self.source_folder} && make {make_args}")                        ← 无 ${...}
```

命中 L0h 的**是第 39 行那条解释性注释**：它在同一行里同时含有 `self.run(` 与 `${CC}`。
把注释改写成不含 `${}` 字面组合后，同一份代码立刻通过（build **#43365 → #43404**）。

本地一行复现（等价于 CI 的 L0h）：

```bash
grep -nE 'self\.run\(.*\$\{(CC|CXX|CFLAGS|CXXFLAGS|LDFLAGS|AR|RANLIB)\}' archives/d/detachtty/11.0.0/conanfile.py
# 39:    # R33: f-string 嵌入到 make 参数，不在 self.run() 里用 ${CC}/${CFLAGS} 展开
```

## 根因分析

`ci/conan/build_and_test.sh` 的 L0h 实现：

```bash
SHELL_ENV_VARS=$(grep -nE 'self\.run\(.*\$\{(CC|CXX|CFLAGS|CXXFLAGS|LDFLAGS|AR|RANLIB)\}' "$CONANFILE")
```

**整行匹配、不过滤注释**。R33 的立法本意是"禁止在 `self.run()` 里做 shell 变量展开"
（CI 环境不保证已定义），判据本应针对**可执行代码**；但实现退化为文本共现，
于是**越认真地写注释解释"不要用 ${CC}"，越容易触发**。这是门禁实现与立法意图
的偏离，属确定性误报，与配方功能无关。

## 已试失败方向

- **反复改写 `build()` 的代码逻辑** → 无效果，命中行在注释里。
- **换成 `self.conf.get("tools.build:compiler_executables")` 却保留原注释** → 仍红。
- **只看 CI 评论首行的"类别：未知"就以为是编译失败** → 方向完全跑偏；
  必须读评论里「失败步骤完整日志」的 `[fail]` 行。

## 最终方案（step-by-step）

1. **先本地复跑 L0h 正则**（见上），定位命中**行号**，确认它在注释还是代码里；
2. 若在注释里 → 改写注释，去掉 `self.run(` 与 `${…}` 的**字面共现**：

   ```python
   # R33: 编译器经 f-string 注入 make 参数，不使用 shell 变量展开
   #      （注释中亦避免出现 self.run 与 $ 花括号变量的同行字面组合，
   #         CI 的 L0h 为行级 grep，注释同样命中）
   ```

3. 保留（并推荐）conf 优先的编译器解析写法，它同时满足 R33 立法本意与工程正确性：

   ```python
   def _cc(self):
       compilers = self.conf.get("tools.build:compiler_executables")  # CI profile 只给 conf
       ...  # 回退 CC 环境变量 > 裸 clang
   ```

4. 参考实现：`archives/c/crashme/2.8.5/conanfile.py`、`archives/d/daa2iso/0.1.7e/conanfile.py`
   —— 两者注释与代码均已按此规范书写，L0h 直接通过。

## 边界与查重

- 与 **E298**（Conan test_package 的显式运行与环境）、**E392**（raw makefile 配方三陷阱）
  的区别：E298/E392 处理的是 `self.run` 的**运行语义**（cwd、env、shell 解析），
  本条处理的是 **CI 门禁的正则误报**（代码正确但被注释触发），判据与处置均不同
  （改注释措辞 vs 改运行方式），**不合并**。
- 正式库以 `shell_env_var_in_run` / `L0h` 检索为 **0 命中**，本条为新增门禁误报模式。
- 与 **E527**（GTK broadway）等"门禁相关"条目无重叠。

## 关联

- 首次命中：PR **!9171**（detachtty 11.0.0，build #43365）
- 修复验证：build **#43404**（CI 校验通过）
- 规避写法落地：PR **!9360**（daa2iso 0.1.7e）、PR **!9361**（crashme 2.8.5）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
