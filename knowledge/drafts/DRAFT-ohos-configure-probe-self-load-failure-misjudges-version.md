# DRAFT-ohos-configure-probe-self-load-failure-misjudges-version — configure 探针自身加载失败 → 版本误判 → 静默跳过整组测试

> **对应结构化数据**：`knowledge/drafts/DRAFT-ohos-configure-probe-self-load-failure-misjudges-version.kv`
> **验证实例**：debugedit 5.3（PR #9255，OHOS PC aarch64，SDK 26）
> **Status**: DRAFT ｜ **Severity**: 🔴 high ｜ **Updated**: 2026-09-15

## 1. 一句话

构建系统用「运行外部工具读版本」探测能力时，若该工具在 OHOS 上**因依赖库不在
`LD_LIBRARY_PATH` 而自身加载失败**，探测读到的是 **loader 错误文本**而非版本号，
解析失败 → 判为「不支持」→ **整组检查/测试被静默跳过**（表现为 `skipped` 而非 `failed`）。

## 2. 机制

上游 configure（debugedit 节选）：

```sh
DWZ_VERSION_STRING=$(dwz --version 2>&1 | head -1)      # ← 2>&1 把错误并进版本字符串
DWZ_MAJOR=$(echo "$DWZ_VERSION_STRING" | sed -E 's/.* ([0-9]+)\.([0-9]+).*/\1/')
DWZ_MINOR=$(echo "$DWZ_VERSION_STRING" | sed -E 's/.* ([0-9]+)\.([0-9]+).*/\2/')
...
if   test "$GDB_MAJOR" -lt "15";  then GDB_ADD_INDEX_CHECKS_OK="yes"
elif test "$DWZ_MAJOR" -gt "0";   then GDB_ADD_INDEX_CHECKS_OK="yes"
elif test "$DWZ_MINOR" -ge "16";  then GDB_ADD_INDEX_CHECKS_OK="yes"
else                                   GDB_ADD_INDEX_CHECKS_OK="no"
fi
```

`sed` 匹配不到 `数字.数字` 时**原样返回**错误文本；`test "$DWZ_MAJOR" -gt "0"` 对非数字
求值失败 → 三个分支全落空 → **判为「工具版本不支持」**。

（`2>&1` 在历史上是必要的 —— 老版本 dwz 把 `--version` 打到 stderr —— 于是 loader
错误也被一并捕获。）

## 3. 实测铁证（同一配方，唯一变量是 LD_LIBRARY_PATH）

```
# 未注入依赖库路径 —— dwz 依赖 libelf → libzstd，加载失败
ac_cv_gdb_dwz_ver='16-vs-Error loading shared library libzstd.so.1: (needed by libelf-0.195.so)...'
GDB_ADD_INDEX_CHECKS_OK='no'

# 注入后
ac_cv_gdb_dwz_ver=16-vs-0.16
GDB_ADD_INDEX_CHECKS_OK='yes'
```

`atlocal` 对照同理：旧树 `GDB_ADD_INDEX_CHECKS_OK="no"` → 新树 `"yes"`。

## 4. 为什么危险：症状完全隐蔽

| 表现 | 后果 |
|------|------|
| configure **不报错**，构建全程正常 | 无任何异常信号 |
| 受影响的测试标记为 **skipped** 而非 failed | 「通过率」看不到异常；skipped 通常不计入分母，反而显得更好 |
| 结论看起来像「平台不支持」 | 适配者会把**可用功能**写成环境限制，写进 notes / PR 描述 |

> **本案例的真实教训**：该 PR 早前的描述把失败归因为「gdb-index/dwz 深度场景，
> OHOS 受限」。补上依赖库路径后，**该组测试完全可跑** —— 这个「平台限制」结论是错的。

另一类同源风险：若探测的是**必需**能力且默认值为「不支持」，会**静默降级构建**
（功能被关掉），产出「能编译但缺能力」的库，问题延迟到运行期才暴露。

## 5. 推荐修法

```python
# 配方 generate()：注入各依赖包的 libdirs（即 runenv）
for _n, dep in self.dependencies.items():
    if not dep.package_folder:      # 未解析出二进制 → cpp_info 返回相对默认值
        continue
    for p in dep.cpp_info.libdirs:
        env.append_path("LD_LIBRARY_PATH", p)
```

> ⚠️ `cpp_info.libdirs` / `bindirs` 在 `dep.package_folder` 为 `None` 时返回**相对默认值**
> `['lib']` / `['bin']` —— 直接注入会生成裸条目（实测 `LD_LIBRARY_PATH=…:lib:lib:lib:lib:…`），
> 无意义且可能被 CWD 下同名目录误命中。故先判 `dep.package_folder`。

要点：

1. **必须覆盖工具自身的传递依赖**，不只是直接 require 的包。
   debugedit 案例：`dwz` → `libelf` → `libzstd`/`libfts`/`libobstack`，全在依赖树里，
   但都不在系统路径。
2. **只注入 PATH 不够** —— 工具的「可执行性」由 PATH 决定，「依赖库可达性」由
   `LD_LIBRARY_PATH` 决定，两者独立。
3. **修完必须复验判定结果**，而不是只看「构建通过」（见下）。
4. 若探测的是必需能力，除修环境外还应**显式断言**期望判定，避免环境异常时静默降级。

## 6. 验证方式（必须做）

```bash
# ① 决定性：搜被污染的探测缓存值
grep -nE "ac_cv_.*Error loading shared library" <build>/config.log
# 期望：无输出；有输出即本 bug

# ② 在同等构建环境下重跑探测
sh -c '. <generators>/conanbuild.sh
       echo "dwz --version -> $(dwz --version 2>&1 | head -1)"'
# 期望 "dwz version 0.16"；若为 "Error loading shared library ..." 即确认工具自身加载失败

# ③ 检查判定落点
grep -nE "_CHECKS_OK=" <build>/tests/atlocal
# 本次修复后由 no → yes
```

## 7. 禁止

- ❌ **「测试被跳过 → 判定平台不支持」** —— skipped 可能是探测失败导致的静默降级。
  先看 `config.log` 里 `ac_cv_*` 是否含错误文本，再下结论。
  （本案例中「OHOS 受限」这一结论就是错的。）
- ❌ **「只注入 PATH 就够了」** —— 可执行性与依赖库可达性是两件事。
- ❌ **「构建通过 → 探测正确」** —— 本 bug 的特征正是「构建全程正常、rc=0」，
  必须复验探测值本身。
- ❌ **「用 sed 解析版本一定可靠」** —— 解析失败**不报错**，而是原样返回或返回空，
  随后 `test` 对非数字求值失败落 else，形成静默误判。解析失败必须显式检出。
- ❌ **改完不复验判定** —— 效果体现在「判定翻转」与「跳过转真跑」上；不复验既无法确认
  生效，也会漏掉口径变化（本次确有测试从 skipped 转为真跑后失败）。

## 8. 与既有条目的关系（差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **E203 / E493**（musl `__progname`）| 同批产出的另一根因（debugedit 的 `error.h` 程序名）。**已按既有条目修复，不重复沉淀** |
| **DRAFT-ohos-gnu-tool-injection-needs-prepend-and-datadir** | 同批姊妹条目：那条讲「工具没被命中 / 缺数据文件」，本条讲「工具命中但自身加载失败致探测误判」。两者共同点是 `LD_LIBRARY_PATH`/PATH 环境不完整，但故障层不同（工具可用性 vs 探测判定）|
| **E106**（path_adjustment）| 同族背景：PATH 顺序影响行为，但那条讲的是选择 toybox 还是 GNU 实现，不涉及「探测判定被污染」|

> 查重（2026-09-15）：main 上 `GDB_ADD_INDEX` / `gdb_dwz` / `自身加载失败` /
> `configure.*探针` / `ac_cv_.*错误文本` **均 0 命中**；`版本解析` 命中 1 处（非本机制）。
> 本条为空白领域。

## 9. 方法论提炼

1. **探测类故障看探测输入与缓存值**（`config.log` 的 `ac_cv_*`），不看构建退出码。
2. **「跳过」与「失败」语义不同** —— skipped 可能是探测失败导致的静默降级，
   必须先排除，再宣称「平台不支持」。
3. **工具的 PATH 可达性与依赖库可达性分别验证**。
4. **修完看判定是否翻转**，并留意「跳过转真跑」带来的口径变化。
5. **警惕 `2>&1` 捕获的不仅是版本** —— 工具加载失败时错误文本会冒充版本号。
