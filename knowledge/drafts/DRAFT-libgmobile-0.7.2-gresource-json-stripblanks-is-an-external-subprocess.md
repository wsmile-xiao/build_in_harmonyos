# DRAFT：`preprocess="json-stripblanks"` 是 PATH 查找的外部子进程，不是链接依赖

> 状态：草稿（待知识库主编 promote）
> 来源：libgmobile 0.7.2 适配，`archives/l/libgmobile/0.7.2`
> 类别：build-system / meson / glib / gresource / hidden-build-dependency

## 现象

在只把依赖的 `lib/` 路径喂给链接器、没把依赖的 `bin/` 放进 `PATH` 的构建环境里，
meson 配置一个用 `<gresources>` 的项目会在**资源编译**这一步失败，而不是在
链接这一步：

```
data/meson.build:1:0: ERROR: Command
  [".../glib-compile-resources", "--sourcedir", ..., "gmobile.gresources.xml", ...]
  failed with status 1.
<stderr>: Failed to execute child process ".../json-glib-format" (No such file or directory)
```

关键症状：**错误里出现的是「找不到某个程序」，但项目从头到尾没有声明过对那个
程序的依赖**。在 `meson.build` 里 grep `json-glib` 只能找到运行期那条
`dependency('json-glib-1.0', ...)`——它已经被 conan 满足；`glib-compile-resources`
本身也确实存在、可执行。

## 根因

### (1) glib 把 json-stripblanks 实现成「运行期外挂程序」

看 ohpcd 的 `glib/2.84.0.1` 制品：

```
$ llvm-readelf -d .../bin/glib-compile-resources | grep NEEDED
 (NEEDED)  Shared library: [libc.so]
 (NEEDED)  Shared library: [libgio-2.0.so]
 (NEEDED)  Shared library: [libgobject-2.0.so]
 (NEEDED)  Shared library: [libglib-2.0.so]
 (NEEDED)  Shared library: [libintl.so]

$ llvm-strings .../bin/glib-compile-resources | grep -i json
JSON_GLIB_FORMAT
json-glib-format
json-stripblanks
```

**没有** `libjson-glib` 这条 `DT_NEEDED`，但二进制里有 `json-glib-format` 这个
程序名。这不是「静态链接进去了」，而是 glib 源码里
`g_find_program_in_path("json-glib-format")` + `g_spawn_sync()` 的痕迹：
`json-stripblanks` 的处理方式是**把 JSON 交给一个外部可执行文件去压缩**，
程序名可由环境变量 `JSON_GLIB_FORMAT` 覆盖。

于是出现一个三角，三者互不蕴含：

| 视角 | 结论 |
| --- | --- |
| 链接图（`DT_NEEDED`） | glib 不依赖 json-glib |
| 运行期（装了 glib 之后天天用） | 不依赖 json-glib —— 只有编译资源那一瞬间才需要 |
| 构建期（正在编译资源） | **必须**能从 PATH 找到 `json-glib-format` |

「链接图完整」和「构建能力完整」在这里是两个不同的命题。

### (2) 这条依赖藏在 XML 属性里，不在构建脚本里

只有当数据文件里写了 `preprocess="json-stripblanks"` 时它才存在：

```xml
<gresources>
  <gresource prefix="/mobi/phosh/gmobile/">
    <file preprocess="json-stripblanks">devices/display-panels/apple,j314s.json</file>
    ...
```

libgmobile 0.7.2 的 `data/gmobile.gresources.xml` 共 34 个 `<file>`，**全部**
带这个属性。所以：

- 扫 `meson.build` 看不到它（它不在 `dependency()` 里）；
- 扫链接命令也看不到它（它不产生 `-l` 参数）；
- 它只在「读数据文件」这一层可见。

### (3) meson 的 gnome 模块只负责「找 glib-compile-resources」

`gnome.compile_resources()` 的职责是把 `glib-compile-resources` 找出来并调用。
至于被调用的那个进程自己还会去 `PATH` 里找谁，meson 无从得知、也不表达。
因此**构建系统不会**把这条工具依赖转成任何形式的依赖声明——它既不出现在
编译命令行里，也不出现在链接命令行里，只在子进程的 `execvp()` 失败时以
`Failed to execute child process` 的形式暴露。

## 与之相反的错误直觉

最容易走的岔路是：「资源里是 JSON → 所以 glib 需要 json-glib → 给 glib 加一条
`json-glib` 依赖」。

这条直觉是错的，而且**修不好问题**：把 json-glib 的库路径喂给链接器，对
`glib-compile-resources` 的子进程 `PATH` 查找毫无影响；同时它还会在依赖图里
凭空造出一条本不存在的 `glib → json-glib` 边（层次倒挂 / 潜在的环）。

> 判据很简单：**缺的是库还是程序？** 报错文案是
> `Failed to execute child process`（程序）、还是
> `undefined reference to`（符号）？前者改 `PATH`，后者改依赖。

## 解决方案

两条一起做，都不改上游：

1. **把工具所有者的 `bin/` 前置进 `PATH`**。不要只挑 glib 一个去加——工具可能
   由任意一个依赖提供，按依赖表遍历最稳：

   ```python
   env = Environment()
   for dep in self.dependencies.host.values():
       b = os.path.join(dep.package_folder, "bin")
       if os.path.isdir(b):
           env.prepend_path("PATH", b)
   ```

2. **再显式钉死 `JSON_GLIB_FORMAT`**，把「靠 PATH 顺序猜」塌缩成「钉死路径」：

   ```python
   tool = find_host_tool("json-glib-format")   # 遍历各依赖 bin/ 找
   if tool:
       env.define("JSON_GLIB_FORMAT", tool)
   ```

   这样跨 worker 不会因为 `PATH` 顺序抖动而「这台机器能过、那台不能」。

3. **两种角色在配方里分开表达**：json-glib 在本包里同时是
   **运行期依赖**（`gm_display_panel_new_from_data()` 走 libjson-glib 解析面板
   JSON，产物 `libgmobile.so` 有 `DT_NEEDED: libjson-glib-1.0.so`）和
   **构建期工具来源**（`bin/json-glib-format`）。前者写进 `requirements()`，
   后者写进构建环境——不要混成一条。

对 libgmobile 而言，`data/meson.build` 的 `gnome.compile_resources(...,
extra_args: '--manual-register', ...)` 还有一个配套点：`--manual-register`
意味着资源不会自注册，库必须自己调 `gm_init()` → `gm_register_resource()`。
这不是本条的问题，但它是「资源到底有没有被编进去」的运行时判据——见
`test_package/test.c` 里通过 `gm_list_devices()` /
`gm_display_panel_new_from_resource()` 读回 34 条设备与 `purism,librem5`
面板的断言。

## 同类家族（把工具依赖藏进子进程的构建步骤）

同一个模式在 glib 生态里到处都有，识别信号一律是「报错说找不到某个**程序**，
而项目从没声明过它」：

| 步骤 | 外部程序 | 怎么被找到 |
| --- | --- | --- |
| `gnome.compile_resources` + `json-stripblanks` | `json-glib-format` | `PATH`，可被 `JSON_GLIB_FORMAT` 覆盖 |
| `gnome.compile_resources` + `xml-stripblanks` | `xmllint` | `PATH` |
| `gnome.generate_gir` | `g-ir-scanner` | 有独立的 `g-ir-scanner` 变量/程序查找 |
| gtk-doc | `gtkdoc-scan` / `gtkdoc-mkdb` | `PATH` + `GTKDOC_*` 变量 |
| autotools 引导 | `aclocal` / `automake` / `libtoolize` | `PATH`，宏文件另需 `ACLOCAL_PATH` |
| pkg-config 探测 | `pkg-config` | `PKG_PROG_PKG_CONFIG` |

共同结论：**打包时把依赖的 `lib/` 喂给链接器是不够的，`bin/` 也要喂给 `PATH`。**

## 验证命令

```bash
# 1) 证明「不是链接依赖」——看 DT_NEEDED，别只看 strings
llvm-readelf -d <glib_pkg>/bin/glib-compile-resources | grep NEEDED
llvm-strings  <glib_pkg>/bin/glib-compile-resources | grep -i json
#    → NEEDED 里没有 libjson-glib；strings 里有 JSON_GLIB_FORMAT

# 2) 确认这条路真的被走到（否则本条不成立）
grep -n  'preprocess='      <src>/data/*.gresources.xml
grep -c  'json-stripblanks' <src>/data/*.gresources.xml   # → 34

# 3) 负向复现：把 json-glib 的 bin/ 从 PATH 摘掉
env PATH=<without-json-glib-bin> meson setup _b <src>     # → 资源编译阶段炸

# 4) 正向：放回 PATH，或显式覆盖
JSON_GLIB_FORMAT=<json-glib_pkg>/bin/json-glib-format meson setup _b <src>

# 5) 自检：资源真的进了产物，而 json-glib 只在运行期需要
nm -D <build>/libgmobile.so | grep -i gm_get_resource
llvm-readelf -d <pkg>/lib/libgmobile.so | grep json-glib
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 看到资源里有 JSON 就给 glib 加 `json-glib` 依赖 | 链接图里根本没有这条 `DT_NEEDED`；缺的是构建期 `PATH`，改依赖表修不好 | 依赖图被污染，资源编译仍失败，排查方向被带偏 |
| 放开 `wrap_mode` 让 meson 去下载 json-glib 子项目 | 上游 `fallback:` 只在依赖**未找到**时才触发；已由 conan 提供时应当让它被正常找到 | CI 不可联网即失败；即使成功也拿到与制品不同源的版本，制品不可复现 |
| 只看 `llvm-strings` 里有 `json-glib` 就断定「链接了 json-glib」 | 程序名本来就会以字符串形式出现在二进制里（要用它去 `g_spawn`） | 得出完全相反的结论，误加依赖边 |
| 为绕过工具缺失直接删掉 `preprocess="json-stripblanks"` | 产物语义变了（资源不再压缩），且永久偏离上游 | 资源内容与上游不一致，属实现降级而非适配 |

## 关联

- `similar_to` **DRAFT-mpsolve-3.2.3-make-check-green-is-not-deliverable-green**：
  同族思路——「看起来够了」的证据层级（退出码 / 链接图）与真实能力脱节；
  那一条讲测试报表，这一条讲构建依赖图。
- `similar_to` **E007**（`config.guess` / `config.sub` 三元组补丁族）：同属
  「工具链自带的平台知识过期/缺失」，但那一条缺的是**三元组识别规则**，
  这一条缺的是**一个外部可执行文件的可见性**——前者要打补丁，后者只要改环境。
- 配套（本条目主题之外）：PkgConfigDeps 生成的 glib `.pc` 缺 `-lintl` 与
  `glib_mkenums` 一类工具变量，需要就地增补生成物（glib 在 OHOS 上与其
  `proxy-libintl` 子项目一同构建，但 glib 配方的 `package_info` 未声明
  `intl` 系统库）。

## 上游可提交性

不需要向上游提交任何东西：本条的结论正是「上游没错，改构建环境即可」。
若要从上游侧彻底消除这个坑，可行的做法是在 `meson.build` 里显式
`dependency('json-glib-1.0')` 之外，再用 `find_program('json-glib-format')`
把工具依赖表达出来——但这是上游的取舍，不是本仓适配的必需项。
