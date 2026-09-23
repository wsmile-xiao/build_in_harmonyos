# DRAFT-ohos-gnu-tool-injection-needs-prepend-and-datadir — 注入 GNU 工具必须 prepend，且需补齐其数据文件

> **对应结构化数据**：`knowledge/drafts/DRAFT-ohos-gnu-tool-injection-needs-prepend-and-datadir.kv`
> **验证实例**：debugedit 5.3（PR #9255，OHOS PC aarch64，SDK 26）
> **Status**: DRAFT ｜ **Severity**: 🟡 medium ｜ **Updated**: 2026-09-15

## 1. 一句话

OHOS 的 `/bin/*` 大量是 **toybox 简化实现**。适配时 require 一个 GNU 版工具包并注入 PATH，
有两个**独立且都极易漏**的陷阱：

1. **PATH 顺序** —— 用 `append_path` 会把目录放到 PATH **末尾**，被 `/bin` 的 toybox 版遮蔽，
   注入**从未生效**；
2. **外部数据文件** —— 部分 GNU 工具的「能力」在数据文件里（GNU `file` 需 `magic.mgc`），
   只换二进制不够。

## 2. 陷阱①：`append_path` 注入静默失效

```python
# ❌ 看起来完全正确，实际无效
for _n, dep in self.dependencies.items():
    for p in dep.cpp_info.bindirs:
        env.append_path("PATH", p)      # 追加到 PATH 末尾
```

实测（debugedit 适配）：

```
$ command -v file
/bin/file                     # toybox 0.8.12 ← 系统版先被命中
$ find ... -print | file -N -f -
file: Unknown option 'N' (see "file --help")     # 枚举到 0 个文件
```

改成 `prepend_path` 后：

```
$ command -v file
<conan>/p/file.../bin/file    # file-5.48 ✅
```

**最阴险之处**：注入代码看起来完全正确 —— 依赖已 require、路径确实进了 PATH、
buildenv/runenv 都生成成功、日志无任何异常。**只有 `command -v` 的实际解析结果**能暴露它。

### 陷阱①附：`cpp_info.*dirs` 的相对路径陷阱

`dep.cpp_info.bindirs` / `libdirs` 在依赖**未解析出二进制**（`dep.package_folder` 为 `None`）
时返回**相对默认值** `['bin']` / `['lib']`。直接遍历注入会往环境里塞进裸条目 ——
实测生成的 env 文件：

```
PATH=…/cpio…/p/bin:…:bin:bin:bin:…/zstd…/p/bin:bin:…
LD_LIBRARY_PATH=…/file…/p/lib:…:lib:lib:lib:lib:…
```

这些条目既无意义，又会被运行时**当前工作目录下的同名目录**意外命中。故注入前先判：

```python
for _n, dep in self.dependencies.items():
    if not dep.package_folder:      # 未解析出二进制 → 跳过
        continue
    for p in dep.cpp_info.bindirs:
        env.prepend_path("PATH", p)
```

（只拼 `dep.package_folder` 前缀并不能消除「None 时无意义」的问题，仍需判空。）

## 3. 陷阱②：工具能力依赖外部数据文件

GNU `file` 的分类能力来自 magic 数据库，conan 包把它放在 `<pkg>/share/misc/magic.mgc`，
**不在默认搜索路径**里。即便 PATH 已正确指向 GNU file，仍报：

```
file: could not find any valid magic files! (No such file or directory)
```

修复：

```python
if "file" in self.dependencies:
    magic = os.path.join(self.dependencies["file"].package_folder,
                         "share", "misc", "magic.mgc")
    if os.path.isfile(magic):
        env.define("MAGIC", magic)
```

**症状与陷阱①相似但根因完全不同**：一个是「没命中工具」，一个是「命中了但工具缺数据」。
两者叠加时现象都是「已有依赖但功能不可用」，极易被误判为「依赖缺失」。

## 4. 验证方式（关键）

```bash
# ① 运行时实际命中哪个二进制（不是看配置）
command -v file                  # 期望 <conan>/.../p/bin/file
file --version                   # 期望 file-5.48（GNU），非 toybox

# ② 该 GNU 工具是否支持所需选项
file -N /dev/null                # 期望正常，非 "Unknown option 'N'"

# ③ 数据文件是否可用
echo '' | file -N -f -           # 缺 MAGIC 时报 could not find any valid magic files

# ④ 在**消费方同等环境**复验（构建/测试脚本常以子 shell 运行）
sh -c '. <generators>/conanbuild.sh; command -v file'
```

## 5. 实测效果（debugedit 5.3）

| 修复 | 结果 |
|------|------|
| `requires("file/5.48.1")` 但用 `append_path` | 仍报 `Unknown option 'N'`，枚举 `0 files` |
| 改 `prepend_path` | `command -v file` → GNU file-5.48 |
| `+ env.define("MAGIC", ...)` | 枚举 `0 files` → **`3 files`** |
| 上游测试通过数 | **34 → 40**（失败 12 → 6）|

同类：`cpio` 也是 toybox 版，`cpio --quiet` 报 `Unknown option 'quiet'`，
接入 `cpio/2.15` 同样需 prepend 才生效。

## 6. 禁止

- ❌ **「已 require GNU 工具包 → 认为生效」** —— 所有配置与日志都显示正常，
  只有 `command -v` 的解析结果能证明。
- ❌ **用 `append_path` 注入 PATH** —— 会被 `/bin` 的 toybox 版遮蔽。
  系统存在同名工具时，注入**必须** `prepend_path`。
- ❌ **见到 `Unknown option 'X'` 就断定工具版本问题** —— 先用 `command -v <tool>` +
  `<tool> --version` 区分「命中 toybox」与「真的版本旧」。
- ❌ **「换了 GNU 工具就不用管数据文件」** —— `file`/`terminfo`/`locale` 等工具的
  能力来自外部数据文件。
- ❌ **在交互 shell 验证就认为构建环境正常** —— conan 的注入在 env 对象里，
  必须 source 生成的环境脚本后在子 shell 复验。

## 7. 与既有条目的关系（差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **E188**（use-gnu-coreutils）| 同族：toybox `install` 功能简化。该条给的是「换 GNU 工具」这一方向；本条补上**换了之后为什么仍不生效**（PATH 顺序 + 数据文件）|
| **E106**（path_adjustment）| **方向相反**：E106 是把 `/bin` **提前**（让 toybox 优先，规避 GNU coreutils 的 SELinux/HMDFS stdout 限制）；本条是注入 GNU 工具时必须**前置 conan bin**（让 GNU 优先于 toybox）。两者共同点是「PATH 顺序决定命中哪个实现」，但目标相反，不可混用 |
| **E510 / E254**（toybox patch）| 同族：toybox 版工具行为与 GNU 不一致（patch 无法处理路径层级/fuzz）。本条给出**通用处置方式**（prepend + 数据文件）|
| **DRAFT-ohos-configure-probe-self-load-failure-misjudges-version** | 同批产出的姊妹条目（debugedit 适配的另一根因），讲 configure 探针判定错误，与本条互补 |

> 查重（2026-09-15）：main 上 `file -N` / `cpio.*quiet` / `MAGIC=` / `magic 数据库` /
> `PATH 末尾` / `append_path.*遮蔽` / `which 解析` **均 0 命中**；
> `toybox` 命中 38 个（均为具体工具行为，非「注入顺序」这一机制）；
> `magic.mgc` 唯一命中 E546（讲交叉构建生成器选择，**无关**）。
> `__progname` 已由 **E203 / E493** 覆盖（属 debugedit 的另一个根因，已按既有条目修复，
> 不重复沉淀）。本条为空白领域。

## 8. 方法论提炼

1. **判定「工具是否被替换成功」看运行时解析结果**（`command -v` + 实际调用），
   而不是依赖声明或配置生成。
2. **「工具能运行」≠「工具功能可用」** —— 后者还需其外部数据文件齐备。
3. **环境注入类改动必须在与消费方一致的环境中验证**（source 环境脚本后的子 shell）。
4. **一次修复应扫清整组测试** —— 若只影响个别用例，往往说明还没找到共同根因。
