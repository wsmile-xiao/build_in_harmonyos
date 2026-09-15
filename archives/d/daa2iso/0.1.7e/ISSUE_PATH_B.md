# 路径 B 知识库扩展申请：CI 的 L0h（R33）为行级 grep，注释里写 `self.run(` 与 `${CC}` 会被误判为失败

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6980 daa2iso 0.1.7e（规避写法落地实例）
- **关联 PR**：`!9360`（`feat/daa2iso-0.1.7e`，配方 PR，CI build #43588 校验通过）
- **知识草稿**：`knowledge/drafts/daa2iso-0.1.7e-l0h-line-grep-comment-false-positive.kv` / `.md`
- **草稿 ID**：`DRAFT-DAA2ISO-L0H-LINE-GREP-COMMENT-FALSE-POSITIVE`
- **首次命中的实例**：detachtty 11.0.0（PR `!9171`，build #43365 因本条被拦）
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/daa2iso-0.1.7e`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

L0h/R33 是**每个** conan 配方 PR 都会过的门禁项，而它的实现是**行级 grep、不过滤
注释**——这意味着"代码完全正确但被注释判失败"。更反直觉的是：**越认真地写注释
解释「不要用 `${CC}`」，越容易触发**。命中后现象是 L0h 以下全部 `blocked_by_L0`，
排查者会看到"改了别的地方还是红"，极易陷入反复重写 `build()` 的盲改循环。
本条给出**一行本地判据**与**仅改注释的处置**，可被后续任何配方 PR 直接套用。

## 二、症状与最小复现

```
o[step] L0j ... [ok]        o[step] L0m ... [ok]
o[step] L0k ... [ok]        o[step] L0n ... [ok]
o[fail] L0h: conanfile.py 在 self.run() 中依赖未定义 shell 变量 ${CC} — 用 self.conf.get() 代替 (R33)
o[fail] detachtty/11.0.0 — L0 quality gate failed: shell_env_var_in_run
oL0_RESULT=fail: gate failed: shell_env_var_in_run
oL1_RESULT=skip: blocked_by_L0
```

本地一行复现（等价于 CI 的 L0h）：

```bash
grep -nE 'self\.run\(.*\$\{(CC|CXX|CFLAGS|CXXFLAGS|LDFLAGS|AR|RANLIB)\}' archives/d/detachtty/11.0.0/conanfile.py
# 39:    # R33: f-string 嵌入到 make 参数，不在 self.run() 里用 ${CC}/${CFLAGS} 展开   ← 命中注释！
```

而被指认的 `build()` **代码完全合规**：

```python
def build(self):
    # R33: f-string 嵌入到 make 参数，不在 self.run() 里用 ${CC}/${CFLAGS} 展开   ← 唯一命中行
    cc = os.environ.get("CC", "clang")
    make_args = f'CC="{cc}" CFLAGS="{cflags}" LDLIBS=""'
    self.run(f"cd {self.source_folder} && make {make_args}")                        # 无 ${...}
```

## 三、根因

`ci/conan/build_and_test.sh` 的 L0h：

```bash
SHELL_ENV_VARS=$(grep -nE 'self\.run\(.*\$\{(CC|CXX|CFLAGS|CXXFLAGS|LDFLAGS|AR|RANLIB)\}' "$CONANFILE")
```

**整行匹配、不过滤注释**。R33 的立法本意是"禁止在 `self.run()` 中做 shell 变量展开"
（CI 环境不保证已定义），判据本应针对**可执行代码**；实现退化为文本共现后，
注释、docstring 里的说明文字同样命中 —— 属**门禁实现与立法意图偏离**的确定性误报。

## 四、处置（仅改注释，不动代码）

```python
# R33: 编译器经 f-string 注入 make 参数，不使用 shell 变量展开
#      （注释中亦避免 self.run 与 $ 花括号变量同行出现 —— CI 的 L0h 为行级 grep）
def build(self):
    cc = self._cc()          # conf > CC 环境变量 > 裸 clang
    self.run(f"cd {self.source_folder} && make CC=\"{cc}\" ...")
```

**不要为了过门禁而删掉 conf 优先的编译器解析**：CI profile 只提供
`tools.build:compiler_executables`，不提供 `CC` 环境变量，conf 优先同时满足
R33 立法本意与工程正确性。参考实现：
`archives/c/crashme/2.8.5/conanfile.py`、`archives/d/daa2iso/0.1.7e/conanfile.py`。

## 五、验证证据

| 项 | 证据 |
|---|---|
| 命中 | detachtty PR !9171 build **#43365**：L0j/L0k/L0m/L0n 全 `[ok]`，L0h `[fail] shell_env_var_in_run` |
| 修复 | 仅改写注释（代码同为 f-string + 局部变量）→ build **#43404 `CI 校验通过`** |
| 规避写法落地 | daa2iso !9360 build **#43588 ✅**、crashme !9361 build **#43591 ✅**，本地 `grep` 判据零命中 |

## 六、查重声明

- **E298**（Conan test_package 的显式运行与环境）、**E392**（raw makefile 配方三陷阱）：
  处理的是 `self.run` 的**运行语义**（cwd / env / shell 解析），本条是 **CI 门禁正则误报**
  （代码正确、注释触发），判据与处置均不同，**不合并**。
- 正式库以 `shell_env_var_in_run` / `L0h` 检索为 **0 命中**，本条为新增门禁误报模式。

## 七、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 是否建议把 L0h 的实现改为**过滤 Python 注释/docstring**（或改用 AST 扫描 `self.run`
   调用实参是否含 `${...}`）？本条目可作为该实现改进的证据与用例。
3. 是否需要把"注释里也不要写出 `self.run` 与 `${CC}` 同行"补进配方模板注释规范？
