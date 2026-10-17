# DRAFT — conan 的 `run(env=...)` 实测**未把 `CFLAGS`/`LDFLAGS` 送达编译器**（同一份 env 用 `subprocess.run(env=dict)` 却可编译成功）

> 触发事件：zstandard 0.25.0 HarmonyOS PC 适配（PR #12210）。配方在 `build()` 里
> 需把 conan 依赖 `zstd` 的 include/lib 注入编译过程（2026-09-23 真机实测）。

> 查重说明：`env argument to ConanFile.run() should be a list` 这一层（`env` 只收
> 「KEY=VALUE」字符串列表、传 dict 直接断言失败）已被 `DRAFT-8945`（botan3 3.12.0）
> 的 `error_signature` 收录，**本稿不重复申报**；只保留其未覆盖的增量。

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-8945`（botan3 3.12.0） | 草稿 | 同一 API 的**形态**——`ConanFile.run(env=...)` 只收字符串列表，传 dict 断言失败 | 8945 覆盖「形态」，**未**涉及「环境未送达编译器」这一**生效性**问题；本条只保留该增量（`.kv` 的 `related_draft` 已标注） |
| E 编号检索（`ConanFile.run` / `zdict.h`） | — | `graph/index.tsv` 与 `E*.kv` **0 命中** | — |

## 错误特征

改成字符串列表后不再报 API 错，但编译找不到头文件：

```
c-ext/python-zstandard.h:28:10: fatal error: 'zdict.h' file not found
1 error generated.
error: command '/data/service/hnp/bin/clang' failed with exit code 1
```

而**同一份 env 手工在 shell 里跑同一条命令却能编译成功**：

```bash
CFLAGS="-I<zstd>/include" LDFLAGS="-L<zstd>/lib -lzstd" \
  python3 setup.py bdist_wheel --system-zstd -d <wheels>   # ✅ 成功
```

## 根因分析

### 要点 1：`env` 的形态

`ConanFile.run(command, env=...)` 的 `env` 只接受**字符串列表**
（`["KEY=VALUE", ...]`），传 `dict` 直接 `AssertionError`（与
`subprocess.run(env=dict)` 的习惯不同）。

### 要点 2：即使传成列表，环境也未送达编译器

实测该环境**未把 `CFLAGS`/`LDFLAGS` 送达编译器**（`zdict.h` 找不到）。conan 的
`run()` 会叠加自己的 buildenv，与 distutils 读取 `CFLAGS` 的时机/覆盖关系不可靠。

### 要点 3：对照组证明 env 内容是对的

把**同一份 dict** 交给 `subprocess.run(..., env=env)` → 编译通过。说明问题只在
「经 conan `run()` 传递」这一段，不在 env 内容。

## 推荐方案

需要**可靠注入** `CFLAGS`/`LDFLAGS` 时，优先用 `subprocess.run(cmd, env=dict)`：

```python
r = subprocess.run(
    [python_exe, "setup.py", "bdist_wheel", "--system-zstd", "-d", wheels],
    cwd=src_dir, env=env, capture_output=True, text=True, timeout=1800)
if r.returncode != 0:
    raise ConanException("bdist_wheel --system-zstd failed:\n"
                         + ((r.stdout or "") + (r.stderr or ""))[-2000:])
```

并自行检查 `returncode` 后抛 `ConanException`，保留「不静默」语义（R51）。

## 禁止做法

- ❌ **不要**把 `dict` 直接传给 `self.run(env=...)`（直接断言失败）。
- ❌ **不要**在 CFLAGS 没生效时反复调整路径内容 —— 先用「手工 shell 能否编过」做
  对照实验：能编过说明 env 内容对，问题在传递路径。
- ❌ **不要**改用 `self.run(..., env=[...])` 后就不再校验编译产物：实测该路径下
  CFLAGS 可能根本没送达，需以「头文件是否被找到」为准而非以「没报 API 错」为准。

## 验证证据

- **主证据**：zstandard 0.25.0（PR #12210）真机实测。
  - `self.run(..., env=[f'CFLAGS={...}', ...])` → `fatal error: 'zdict.h' file not found`。
  - 同一份 env 手工 shell → 产出
    `zstandard-0.25.0-cp312-cp312-ohos_aarch64.whl`。
  - 改用 `subprocess.run(env=dict)` → conan create 端到端通过，
    消费者测试输出 `OK: zstandard 0.25.0 real API ok (... linked zstd (1, 5, 7))`。
- **交叉佐证**：本仓其他 C 扩展配方凡需注入编译环境者，均可复现「`self.run(env=)`
  不生效、`subprocess` 生效」的差异。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / conan 2.29.1。

## 查重结论

- 对 `CFLAGS` + `self.run` / `ConanFile.run` 检索：**0 命中**（无「CFLAGS 未送达」条目）。
- 对 `zdict.h` / `include path not passed` 检索：**0 命中**。
- `DRAFT-8945` 覆盖的是同一 API 的**形态**（须为列表），**未**涉及「环境未送达编译器」
  这一生效性问题 —— 二者互补，不重叠。
- **盲区声明**：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人
  提交过同主题草稿。
