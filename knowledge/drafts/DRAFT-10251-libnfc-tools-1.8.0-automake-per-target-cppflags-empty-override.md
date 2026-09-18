# DRAFT-10251-libnfc-tools-1.8.0-automake-per-target-cppflags-empty-override：automake per-target `*_CPPFLAGS =`（空值）替换 `AM_CPPFLAGS`，VPATH 构建下头文件找不到

> Contributor: SunShine_06 | Status: Draft | Updated: 2026-09-16
> Source: libnfc-tools 1.8.0 适配（PR #10251）关联的 Cutter 1.2.6 交叉编译（VPATH 构建）
> 对应：`knowledge/drafts/DRAFT-10251-libnfc-tools-1.8.0-automake-per-target-cppflags-empty-override.kv`

## 现象

automake 工程 VPATH（`srcdir != builddir`，conan 构建的标准形态）编译某目标时，
头文件找不到——**但同样的 `-I` 在别的目标上明明生效**：

```console
xml_la-...c:2:10: fatal error: 'cut-module-impl.h' file not found
 #include <cut-module-impl.h>
```

关键线索：`AM_CPPFLAGS` 里已经写了 `-I$(top_srcdir)` 等路径，`make` 命令行
打印的编译命令里却**没有**这些 `-I`。

## 根因

automake 的 `AM_CPPFLAGS` 只是**默认值**。一旦 Makefile.am 对某个目标显式写了
**per-target** 的 `*_CPPFLAGS`，automake 就用它**替换**（而非追加）默认值：

```makefile
# 上游 module/report/Makefile.am（示意）
AM_CPPFLAGS = -I$(top_srcdir) -I$(top_builddir)      # 默认
...
xml_la_CPPFLAGS =                                     # ← 空值：显式声明了，但为空
```

生成的 `Makefile` 里 `xml_la_CPPFLAGS` 被展开为空串，于是 `$(AM_CPPFLAGS)`
**完全不参与**该目标的编译，`-I` 全丢。空值尤其隐蔽：如果写的是非空值，
一眼能看出被覆盖；写成空值看起来只是"没设置"。

> 同族陷阱：`AM_CFLAGS`/`AM_CXXFLAGS`/`AM_LDFLAGS` 与 per-target
> `*_CFLAGS`/`*_LDFLAGS` 是完全相同的替换关系。

## 方案（三选一，按侵入性从低到高）

**① make 命令行回填（不改上游文件，推荐用于"只为一处救急"）**

```sh
make -C module/report \
  xml_la_CPPFLAGS="-I$BUILD -I$SRC" \
  xml_factory_la_CPPFLAGS="-I$BUILD -I$SRC"
```

命令行变量优先级高于 Makefile 内赋值，且不动源码——**适配期最快、可审计**
（命令留在脚本/配方里）。缺点是要逐个目标点名。

**② configure 变量注入（不改上游文件，适合 conan 配方）**

```python
# conanfile.py configure()
tc.variables["CPPFLAGS"] = f"-I{self.source_folder} -I{self.build_folder}"
```

只有当该目标最终仍引用全局 `CPPFLAGS` 时才有效；若 `Makefile.am` 里写的是
`*_CPPFLAGS = ` 空值，注入无效 → 退回 ① 或 ③。

**③ 补丁改上游（改源码，须披露）**

把空赋值删掉或补上正确 `-I`，作为 patch 单列并在 PR「上游测试/文件修改说明」里披露。

> 三种都必须先在 **VPATH** 布局下复现（`mkdir build && cd build && ../configure`），
> in-source 构建（`srcdir == builddir`）往往看不到这个错——因为相对路径凑巧成立。

## 判别（三行定位）

```sh
# 1) 找 per-target CPPFLAGS 赋值（尤其空值）
grep -nE '^[A-Za-z_]*_la_CPPFLAGS|^[A-Za-z_]*_CPPFLAGS' */Makefile.am

# 2) 看生成的 Makefile 里是否真为空
grep -n '^xml_la_CPPFLAGS' module/report/Makefile

# 3) 看编译命令里有没有 -I（make V=1 或看 libtool 回显）
make V=1 2>&1 | grep 'cut-module-impl\|fatal error' | head -3
```

## 验证（真实证据）

Cutter 1.2.6 在 HarmonyOS PC（OHOS clang 15.0.4）上 VPATH 构建：

- 修复前：`module/report` 编译 `xml_la-*` 报 `cut-module-impl.h file not found`；
- 用 ① 回填 `xml_la_CPPFLAGS`/`xml_factory_la_CPPFLAGS` 后编译通过；
- 最终 libcutter + cutter runner + report/stream/UI 模块全部产出，6 个 libnfc 上游用例真实执行通过。
- 完整过程见 `archives/l/libnfc-tools/1.8.0/upstream-tests/CUTTER-BUILD.md` 踩坑表第 7 项。

## 适用边界

- **触发面**：automake 工程 + VPATH 构建（conan build 的默认形态）+ 上游对某些目标
  写了 per-target `*_CPPFLAGS`/`*_CFLAGS`/`*_LDFLAGS`（含空值）。**非 OHOS 专有**——
  Linux 上只要 VPATH 构建同样复现；
- **反例**：`srcdir == builddir` 的 in-source 构建常不报错，**不能据此判定"没问题"**；
- **反例**：`-I` 路径本身写错、或头文件确实不存在 → 不是本模式，别用回填掩盖。

## 关系

- 同族：`AM_CFLAGS`/`AM_LDFLAGS` 与 per-target 变量为相同替换语义；
- 场景邻居：Cutter 交叉编译全链见
  `DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard`（本条是其构建期子问题）。

## 查重

按 `AM_CPPFLAGS` / `per-target CPPFLAGS` / `_la_CPPFLAGS` / `VPATH` 检索
`knowledge/graph/` 与 `knowledge/drafts/`：

- `E346-draft-2301`（X11 子库 pkg-config 桩）关键字重叠但对象不同——那是*依赖模块缺失*，
  本条是*变量替换语义*；
- **无既有"automake per-target 变量替换默认值"条目** → 本条为新增。

⚠️ **签名家族重叠说明（机器预审发现，已人工比对）**：`ohc draft-review` 首轮把本条
判为「疑似重复 → E169/E217」，原因是初版 `error_signature` 写了泛化的
`fatal error: <X>.h file not found`，与两个既有条目的签名家族字面重合（sig=1.0）。
人工比对确认**根因不同，非重复**：

| 条目 | 根因 | 语境 |
|------|------|------|
| E217 | CMake `includedirs` / 安装路径（`DESTINATION include`） | CMake + test_package |
| E169 | OHOS 缺 `argp.h`（glibc API 缺口） | musl API 缺口 |
| **本条** | automake per-target 变量**替换** `AM_CPPFLAGS`（变量语义） | automake + VPATH |

已据此收紧本条 `error_signature`（去掉泛化编译错误字面量，改用 automake 变量形态
+ VPATH 语境作辨别指纹），避免本条劫持「头文件找不到」这一大类节点。
