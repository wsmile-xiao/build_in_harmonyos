# DRAFT — meson 内置选项 `b_ndebug` 被 `--buildtype` 重新推导：上游断言被编译掉、测试「假通过」

> **触发事件**：libliftoff 0.5.0（meson）在 HarmonyOS PC 上适配。首次 `conan create`
> 报 **57 Ok / 1 Fail**，唯一失败项是上游自带的哨兵用例 `test/check_ndebug.c`。
> 日期：2026-09-28

## 与既有条目的关系

| 既有条目 | 关系 |
|---|---|
| **E259**（Conan Release 的 `-DNDEBUG` 让 `assert(含副作用表达式)` 不求值） | **机制相关、根因不同**。E259 是「语法层副作用被抹掉」，修法是改源码把副作用移出 `assert`；本条是「meson 内置选项 `b_ndebug` 的**设置途径**失效」，修法是改构建配置并实测校验。E259 全文不含 meson/`b_ndebug`/introspect（实测 grep 计数 **0**） |
| `DRAFT-taocpp-tuple-1.0.0-ndebug-werror-upstream-test-debug-build` | CMake 侧同类现象，但表现为**编译期 `-Werror unused variable`**——构建直接失败，**容易被发现**。本条更危险：构建与测试都「成功」，只是用例实际什么都没执行 |
| `DRAFT-libnih-1.0.3-ndebug-assert-sideeffect-hoist`、`embedmq-1.0.1-ndebug-assert-control-flow-test` | 同为 assert/NDEBUG 族，但均属**源码层**处置；本条属**构建配置层** |

> 本技法已在仓内**两个已入库配方**中出现（`archives/j/jose/14`、`jose/15` 的
> `_force_live_assertions`，以及 `archives/l/libliftoff/0.5.0`），但知识库此前无对应条目
> —— 本条补齐该沉淀缺口。

## 错误特征

测试**几乎全绿**，只有一个用例失败，且失败的用例名里带 `ndebug`：

```
 1/58 libliftoff:check_ndebug                                   FAIL      0.31s   exit status 1
...
Summary of Failures:
 1/58 libliftoff:check_ndebug                                   FAIL      0.31s   exit status 1
Ok:                57
Fail:              1
```

失败原因（哨兵自己打印的）：

```
NDEBUG is defined, cannot run tests
```

> ⚠️ **易误判点**：看到「57 过 1 失败」，第一反应是去查那个失败用例是不是上游缺陷、
> 或把它标记为「平台限制」跳过。**这是错误方向**。那个失败项是上游**故意设计**的哨兵，
> 它失败的含义恰恰是：**其余 57 个「通过」是假的**。

## 根因分析

`b_ndebug` 是 meson 的**内置（built-in）选项**，其值可由 `buildtype` 推导。
`MesonToolchain` 会把配方在 `tc.project_options` 里请求的值写进 machine file，
**但 conan 同时还往 setup 命令行上传了 `--buildtype=release`**；在处理顺序上，
buildtype 的推导覆盖了 machine file —— 于是请求的 `false` 被丢弃。

实测（libliftoff 0.5.0 构建内 `meson introspect --buildoptions`）：

| 选项 | 请求值 | **实际生效值** |
|---|---|---|
| `werror` | false | `False` ✅ |
| `default_library` | shared | `'shared'` ✅ |
| `c_std` | c11 | `'c11'` ✅ |
| **`b_ndebug`** | **false** | **`'true'`** ❌ |

即：**同批请求的其它选项全都生效，唯独内置选项 `b_ndebug` 没有**——这正说明它不是
「配方写错了」，而是「内置选项的生效途径被 buildtype 覆盖」。

### 为什么危害是「静默」的

libliftoff 上游把**断言体及其副作用**全写在 `assert()` 里（`test_alloc.c` 18 处、
`test_dynamic.c` 43 处、`test_prop.c` 27 处、`test_priority.c` 4 处、`test_candidate.c` 7 处，
共 **99 处**）。`-DNDEBUG` 下 `assert(EXPR)` 展开为 `((void)0)`，EXPR 根本不求值 ——
用例体等于空执行，而测试框架仍然报「通过」。**57 个用例零验证，却交付一个全绿的报告。**

若不运行上游测试（或上游没写哨兵），这个失真完全无感：表现为「测试全过」，
实际什么都没验证。libliftoff 的 `test/check_ndebug.c` 就是上游为抓这种情况专门写的：

```c
#include <stdio.h>

int
main(int argc, char *argv[])
{
#ifdef NDEBUG
	fprintf(stderr, "NDEBUG is defined, cannot run tests\n");
	return 1;
#else
	return 0;
#endif
}
```

## 判定口径

**测试结果里出现一个名字含 `ndebug` 的用例失败、而其余用例「全过」→ 那「全过」不可信。**

排查命令（对任意 meson 构建）：

```bash
meson introspect <build_dir> --buildoptions | grep -A2 '"b_ndebug"'
```

若 `value` 为 `"true"`，则上游断言未生效，测试计数不可用。

## 推荐方案

在 `meson.configure()` **之后**、`meson.build()` 之前钉正，并用 introspect **实测校验**：

```python
def build(self):
    meson = Meson(self)
    meson.configure()
    self._force_live_assertions()   # ← 本方案
    meson.build()
    meson.test()

def _force_live_assertions(self):
    build_dir = self.build_folder
    # ① 钉正生效值
    self.run(f'meson configure "{build_dir}" -Db_ndebug=false', env="conanbuild")

    # ② 读取**实际生效值**
    info = os.path.join(build_dir, "liftoff-buildoptions.json")
    self.run(f'meson introspect "{build_dir}" --buildoptions > "{info}" 2>&1',
             env="conanbuild", ignore_errors=True)
    effective = {}
    try:
        with open(info, encoding="utf-8") as handle:
            for entry in json.load(handle):
                effective[entry.get("name")] = entry.get("value")
    except (OSError, ValueError) as exc:
        raise ConanException(f"cannot verify meson options: {exc}")

    for key in ("buildtype", "b_ndebug", "werror", "default_library"):
        self.output.info(f"LIFTOFF_MESON_OPTION {key} = {effective.get(key)!r}")

    # ③ 校验失败必须硬失败
    # meson 的 b_ndebug 是 combo 选项，introspect 返回字符串 "false"/"true"
    if str(effective.get("b_ndebug")).strip().lower() != "false":
        raise ConanException(
            f"b_ndebug is {effective.get('b_ndebug')!r}: upstream assertions "
            "would be compiled out and the test tally would be meaningless")
```

**三个要点缺一不可**：

1. **不能只写 `tc.project_options["b_ndebug"] = "false"`** —— 实测无效（被 buildtype 覆盖）。
2. **不能只发 `meson configure` 命令而不校验** —— meson 选项是 combo，introspect 返回的是
   字符串 `"false"`，必须按字符串比对（`value` 也可能是 `True`/`False` 布尔，视选项类型）。
3. **校验失败必须硬失败（raise）** —— 否则又回到「静默假通过」的老路。

## 这是「让断言真实生效」，不是「改测试让其通过」

本方案**不修改、不跳过、不删除任何上游测试文件**；58 项在断言生效后**全部真实执行并通过**：

| 状态 | `b_ndebug` 生效值 | 测试结果 | 含义 |
|---|---|---|---|
| 修复前 | `'true'` | `Ok: 57 / Fail: 1` | 57 项**空执行**、哨兵报警 |
| 修复后 | `'false'` | `Ok: 58 / Fail: 0` | 58 项**真实执行**并通过 |

构建日志留证（`conan create` 输出）：

```
libliftoff/0.5.0: LIFTOFF_MESON_OPTION buildtype = 'release'
libliftoff/0.5.0: LIFTOFF_MESON_OPTION b_ndebug = 'false'
libliftoff/0.5.0: LIFTOFF_MESON_OPTION werror = False
libliftoff/0.5.0: LIFTOFF_MESON_OPTION default_library = 'shared'
...
Ok:                58
Fail:              0
```

## 禁止做法

- ❌ **删除 / 跳过 / deselect `check_ndebug`**：它是上游故意设计的**唯一告警装置**，
  它失败正是「其余用例通过数不可信」的信号。屏蔽它 = 销毁告警、让 57 个空执行的用例
  冒充全绿 —— 这是伪造测试结果（违反 R51）。
- ❌ **把「Ok: 57 / Fail: 1」记成「上游测试失败」或「平台限制」**：这不是用例失败，
  而是**构建配置未生效**的信号。误判根因会导向错误修复（改测试 / 给上游打补丁），
  真正的配置问题被掩盖。

## 备选方案（退路）

仅当上游测试必须 Release 构建（依赖 Release 宏或优化行为）且 `b_ndebug=false` 下
无法正确工作时，才把**测试**单独用 debug 构建运行：

```bash
meson setup <test_build_dir> --buildtype=debug && meson test -C <test_build_dir>
```

代价：测试环境与发布产物的构建类型不一致，测试语义偏离上游真实 Release 行为。
**首选方案更强**：保持 Release 构建类型，只钉正 `b_ndebug`。

## 验证证据

- **实测环境**：HarmonyOS PC / aarch64 / clang 15 / conan 2.29.1 / meson 1.11.1。
- **软件**：libliftoff 0.5.0（上游 tag `v0.5.0`），测试经 `test/libdrm_mock.c` 的
  `override_dependency` 替换真实 libdrm，无需 `/dev/dri`。
- **仓内同技法先例**：`archives/j/jose/14`、`archives/j/jose/15`（均已入库）。
- **PR**：#13394，commit `def4d06c1`。

## 查重结论

- `b_ndebug`：全知识库（graph + drafts）**0 命中**。
- `meson introspect --buildoptions`：有若干条目提及 introspect，但**无一**与
  `b_ndebug`/断言失效相关。
- `assert.*被消除` / `零执行` / `计数失真` / `assert.*不生效`：**0 命中**同主题。
- 最相近的 **E259** 已逐字核对：全文不含 meson/`b_ndebug`/introspect。
- **盲区声明**：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过同主题草稿。
