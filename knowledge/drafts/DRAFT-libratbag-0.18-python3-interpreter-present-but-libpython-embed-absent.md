# DRAFT：有 `python3` 解释器 ≠ 有 libpython（embed）—— 上游把两者混在一个无条件块里，配置期直接失败

> 状态：草稿（待知识库主编 promote）
> 来源：libratbag 0.18 适配，`archives/l/libratbag/0.18`
> 类别：build / meson / conan / portability / python

## 错误特征

在一台「有 `python3`、但没有 `python3-dev`/`libpython3-dev`」的构建机上，
meson 配置期报出**两条**看起来互不相关的失败，实际根因是同一个：

```
meson.build:515:11: ERROR: Dependency "python-3.11-embed" not found, tried pkgconfig and cmake
```

或者（换一个 meson 版本/发行版措辞）：

```
Run-time dependency python3-embed found: NO (tried pkgconfig)
meson.build:581:11: ERROR: Program 'swig' not found or not executable
```

识别信号是：**这台机器上 `python3 -c 'print(1)'` 明明是通的**，而 meson 却说
python 依赖找不到。这两个陈述并不矛盾 —— 它们说的是两个不同的东西：

| 上游代码 | 探测的对象 | 在只装解释器的机器上 |
|----------|-----------|---------------------|
| `py3 = pymod.find_installation()` | **解释器可执行文件**（PATH 里的 `python3`） | ✅ 找得到 |
| `py3.dependency(embed : true)` / `dependency('python3-embed')` | **可嵌入开发库**（`python-3.x-embed.pc` + `Python.h` + `libpython3.x.so`） | ❌ 找不到 |

`find_installation()` 成功**不能**推出 `dependency(embed:true)` 会成功。

## 触发条件

两条同时成立：

1. 上游把「找解释器」和「找 libpython」写在**同一个无条件块**里，且最后一步是
   `required = true`；
2. 构建机只装了 Python 解释器，没装开发库（OHOS worker 就是这种形态）。

libratbag 0.18 的现场（`meson.build`）：

```meson
dep_python3 = dependency('', required : false)
pymod = import('python')
py3 = pymod.find_installation()                    # ← 只证明有解释器
if meson.version().version_compare('>= 0.53.0')
  dep_python3 = py3.dependency(embed : true)       # ← 这里才需要 libpython
endif
py_version = py3.language_version()
embed = py_version.version_compare('>= 3.8') ? '-embed' : ''
if not dep_python3.found()
  dep_python3 = dependency('python-@0@@1@'.format(py_version, embed), required : false)
  if not dep_python3.found()
    dep_python3 = dependency('python3@0@'.format(embed))   # ← required=true，硬失败
  endif
endif
```

紧跟着还有**第二个独立的坑**：

```meson
# ratbag-command uses Swig bindings to call libratbag directly
swig = find_program('swig')            # ← 只服务于可选的绑定目标，却挡在所有路径前
```

`swig` 与 Python 毫无关系 —— 它是另一条「只因为要生成可选绑定，就要求整个构建
都装好」的无条件依赖。

## 根因分析

### 「解释器在」是一个比想象中弱得多的证据

在容器/CI/嵌入式镜像里，「装了 Python」几乎总是指只装了运行时：

| 发行版包 | 提供 | 常见装法 |
|----------|------|----------|
| `python3` | `/usr/bin/python3` | 几乎总有 |
| `python3-dev` / `libpython3-dev` | `Python.h`、`libpython3.x.so`、`python3.pc` | **经常没有** |

`py3.dependency(embed : true)` 走的是 pkg-config 查 `python-3.x-embed.pc`，
这是**开发库**提供的文件。OHOS worker 上这个文件不存在，`find_program('swig')`
也失败。

### 最容易踩的推断错误：拿「同仓库其它 meson 包能过」当反证

同一个仓库里明明有别的 meson 包（glib 等）构建成功，于是直觉认为「既然它们能过，
libpython 肯定在」。**这个推断不成立**：

- glib 用 Python 只是**跑脚本**（`gdbus-codegen`、`glib-mkenums`），只需要
  `find_installation()`；
- 它**从不调用** `py3.dependency(embed : true)`，也从不 `#include <Python.h>`。

所以「仓库里别的 meson 包能过」只证明**解释器在**，对 libpython 一个字都没说。
要用这个证据链，必须先确认那些包是否真的探测过 embed 依赖 —— 只看「它也是
meson 包」是不够的。

### 为什么不能在配置期硬失败

上游第三个分支是 `dependency('python3@0@'.format(embed))`（**required 默认
true**）。这意味着「只缺 libpython」不是降级，而是**整个构建在配置期终止** ——
哪怕调用方只想要 `liblur.so`，一行 Python 绑定代码都不会用到。

## 修复方案

补丁新增一个**默认 true** 的布尔选项，把 libpython 查找与 swig 块一起包进去：

```meson
# meson_options.txt
option('python-bindings',
	type : 'boolean',
	value : true,
	description : 'Build the swig-based Python bindings and ratbag-command (requires swig and libpython, default=yes)')
```

```meson
# meson.build
enable_python_bindings = get_option('python-bindings')
...
if enable_python_bindings
  if meson.version().version_compare('>= 0.53.0')
    dep_python3 = py3.dependency(embed : true)
  endif
  if not dep_python3.found()
    ...（原有的两级回退）
  endif
endif
...
if enable_python_bindings
  swig = find_program('swig')
  ...
endif
```

配方配置时 `-Dpython-bindings=false`。

三条细节必须同时做到：

1. **默认值保持 `true`** —— 非 OHOS 平台行为逐字节不变，补丁是纯增量的，
   将来上游合并也没有行为争议（P005）。
2. **`find_installation()` 保持无条件** —— meson 自身、以及上游那些纯 Python
   的测试脚本（libratbag 有 3 个 `data-parse-test` / `duplicate-test` /
   `receiver-id-test`）仍然需要解释器。把它一起关掉，等于把「缺 libpython」
   升级成「连解释器都不找」，会把本来能构建的平台也弄坏。
3. **关掉的必须是整块** —— 只关 libpython、留下 `find_program('swig')`，配置
   是过了，生成期接着炸。

先例：仓库内 graphviz 的 `--disable-swig` 是同一模式。

## 判据 / 复现命令

```sh
# 判据一：解释器有没有（这一步几乎总是有）
command -v python3 ; python3 -c 'import sys; print(sys.version)'

# 判据二：embed 开发库有没有 —— 这才是上游真正要的，三者全空即没有
pkg-config --exists python-3.11-embed && echo has-embed-pc || echo no-embed-pc
pkg-config --exists python3-embed     && echo has-embed-pc || echo no-embed-pc
ls /usr/include/python3*/Python.h 2>/dev/null      # 空 = 没有

# 判据三：swig 有没有（与 python 无关的第二个坑）
command -v swig

# 判据四：上游到底把两者绑在一起没有
grep -n "find_installation\|dependency(embed\|python3-embed\|find_program('swig')" meson.build

# 判据五：别拿「同仓库别的 meson 包能过」当反证 —— 先去查它有没有探测 embed
grep -rn "dependency(embed\|python3-embed\|Python.h" <那些包的源码>/meson.build
```

## 反模式（不要这么做）

| 反模式 | 为什么不行 |
|--------|-----------|
| 直接删掉上游的 `find_program('swig')` / libpython 那几行 | 等于把「本平台不支持该特性」写成「该特性不存在」，非 OHOS 平台一起失去绑定；且上游升级时补丁必冲突 |
| 伪造一个 `python3-embed.pc` 骗过 configure | 只把失败从配置期推迟到链接期，失败点离原因更远 |
| 「装个 swig / python3-dev 就好」 | OHOS 上装不了宿主发行版包；交叉编译时宿主的 swig/libpython 也不能代替目标平台的（绑定要链目标平台的 libpython） |

## 迁移范围

任何语言、任何构建系统里同一个形状都成立：**「工具链里能找到某个解释器」不等于
「能找到它的开发库」**。Node（`node` vs `node-gyp` + headers）、Ruby
（`ruby` vs `ruby-dev`）、Perl（`perl` vs `libperl-dev`）在离线/精简镜像里
都是同一种形态。判据永远是「上游探测的到底是哪一个」，而不是「机器上有没有它」。
