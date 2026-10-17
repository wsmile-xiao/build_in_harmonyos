# DRAFT-pd-external-host-sdk-header-resolution — 宿主应用装了 SDK 头却不暴露：插件外部对象怎么拿 m_pd.h / 定扩展名

> 场景：宿主运行时（Pure Data）以 Conan `application` 单独打包，插件（Pd external
> 集合）用宿主自带构建器 `pd-lib-builder` 编成宿主运行时加载的模块。本稿解决
> **插件找不到宿主 SDK 头**、以及**目标扩展名从哪来**这两个反直觉点。

## 错误特征（可粘贴的真实日志）

```
m_pd.h: No such file or directory
fatal error: 'm_pd.h' file not found
# （若依赖未暴露 includedirs，消费者不会自动获得 -I）
```

以及对象装好了却加载不到：

```
couldn't create object: divide
```

## 触发条件

- 平台：OHOS aarch64 / SDK clang 15（本仓 `ohos-aarch64` profile）。
- 构建系统：`pd-lib-builder`（`Makefile.pdlibbuilder`），需要一个**显式的**
  `PDINCLUDEDIR` 指向宿主 API 头。
- 宿主依赖：`puredata/0.54.1`（Conan `application`）。

## 根因分析（机制 + 实测数字）

有两个反直觉点，只看一半都会误判。

### 1. 头「装进了包」但「没经 Conan 暴露」

`puredata/0.54.1` 的 `package()` 直接跑上游 `make install DESTDIR=<pkg>`，所以**包目录里
确实有** `include/m_pd.h` 以及 `include/pd/{m_imp.h,s_stuff.h,...}`：

```
$ conan cache path puredata/0.54.1
/storage/Users/currentUser/.conan2/p/pured.../e          # 配方 export 目录（无头）
$ grep -n 'include/m_pd.h' <package>/conanmanifest.txt
include/m_pd.h: d54f78cbc0ca70ca25c1f0f8943e7dcd          # 头在包目录里
```

但同一个配方把依赖接口关掉了：

```python
def package_info(self):
    self.cpp_info.bindirs = ["bin"]
    self.cpp_info.libdirs = []
    self.cpp_info.includedirs = []        # ← 依赖不给消费者任何 -I
```

于是 `self.dependencies["puredata"]` 既不提供 `-I`，也不提供 CMake 目标；`pd-lib-builder`
又**只认 `PDINCLUDEDIR`**（不会去用编译器的默认搜索路径找 `m_pd.h`）。两件事叠加，直接在
插件编译期报 `m_pd.h file not found`。

> 关键判据：**「包目录里有头」和「依赖接口暴露头」是两回事**。查证要同时看
> `conanmanifest.txt`（物理文件）与配方 `package_info()`（接口）。

### 2. 扩展名由 `$(CC) -dumpmachine` 决定，落 generic Linux 分支

`pd-lib-builder` 用编译器三元组选平台：

```
Makefile.pdlibbuilder:473   target.triplet := $(subst -, ,$(shell $(CC) -dumpmachine))
Makefile.pdlibbuilder:486   ifneq ($(filter darwin%, $(target.triplet)),) ...
Makefile.pdlibbuilder:490   ifneq ($(filter mingw% cygwin%, $(target.triplet)),) ...
Makefile.pdlibbuilder:559   extension = pd_linux
```

OHOS SDK clang 报：

```
$ clang -dumpmachine
aarch64-unknown-linux-ohos
```

三段里没有 `ohos` 分支，`linux-ohos` 落 generic Linux → `extension = pd_linux`。
这**正是** Pd 在 OHOS 上加载对象用的扩展名（`pd` 按平台扩展名搜索 `-path` 目录），所以
无需自定义扩展名、也不要改成 `.so`。实测两库产物：

| 库 | 上游 | `.pd_linux` 数 | 说明 |
|----|------|:---:|------|
| pd-maxlib | 1.6.0（Debian orig） | **58** | `net*` 类上游已注释排除（依赖 `m_imp.h`/`s_stuff.h`） |
| pd-mjlib | 0.2.0（Debian orig） | **8** | 独立上游仓，第二库验证 |

## 解决方案

1. **显式给 `PDINCLUDEDIR`**（按优先级）：
   - 先查宿主包目录：`<host_dep>.package_folder/include`（本仓 puredata 已装 `m_pd.h`，可直接用）；
   - 若宿主包没有，再取**同版本上游源码树**（回退方案见下）。
2. **显式传 `CC`**，让 `pd-lib-builder` 自行按 `$(CC) -dumpmachine` 判定扩展名，不要硬编码。
3. 插件包 `package_info()` 里 `includedirs/libdirs/bindirs` 全空——它只对外交付
   `lib/pd-externals/*.pd_linux` 与帮助补丁，宿主头是**构建期输入**，不是它对外提供的头。

### 推荐方案命令

```sh
make -j1 CC="<clang>" PDINCLUDEDIR="<host_dep>/include"
```

### 回退方案（宿主包无头时）

```python
# source(): 额外拉同版本宿主源码树
get(self, url="https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1",
    sha256="19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353",
    filename="pure-data-0.54-1.tar.gz", strip_root=True, destination="pd-api")
```

## 禁止做法（实测依据）

- ❌ 断言「依赖会给 `-I`」：`puredata` 的 `includedirs=[]`，不显式传 `PDINCLUDEDIR`
  必 `m_pd.h file not found`。
- ❌ 自造 stub `m_pd.h` 顶替：`m_pd.h` 定义了 `t_symbol`/`t_atom`/`t_class` 等**宿主 ABI
  结构体**，尺寸/布局不符会在 `pd` 加载对象时崩。
- ❌ 硬编码扩展名 `.so`/`pd_ohos`：`pd` 按平台扩展名找对象，改错就 `couldn't create object`。

## 通用性证据（独立第二库）

同机制在**另一个独立上游仓**上复现：`pd-mjlib 0.2.0`（Debian `pd-mjlib_0.2.0.orig.tar.gz`，
sha256 `53d52bdf…29779`）同样以 `pd-lib-builder` + `PDINCLUDEDIR` 构建，产出 **8** 个
`.pd_linux`，机型 OHOS clang 三元组同为 `aarch64-unknown-linux-ohos`。两库各自 `conan create`
`CREATE_RC=0`、消费者无头加载通过（见配套第二稿）。

## 查重反证（vs 已有条目）

- **E442**（host-loaded plugin 未解析符号 → 去 `-no-undefined` / 去 in-tree 宿主库）：
  其根因是**链接期符号契约**，本稿是**编译期头目录 + 目标扩展名**，且实测事件不同
  （本任务链接期无 undefined host symbol）。`readelf --dyn-syms` 本库无宿主未解析符号。
- **「install_headers 漏装被引用头」类草稿**（如 `DRAFT-delaunay-…-missing-referenced-header`、
  `DRAFT-collections-c-…-public-header`）：那是**包自己的安装清单**漏项；本稿是**宿主依赖包的
  cpp_info 未暴露已安装头**，根因在依赖接口而非本包安装清单。
- 关键词族 0 命中证据（main tip）：
  `grep -rilE 'm_pd\.h|PDINCLUDEDIR|pd-lib-builder|pd_linux' knowledge/graph knowledge/doc | wc -l` → **0**；
  `... knowledge/drafts | wc -l` → **0**；
  `grep -rilE 'includedirs\s*=\s*\[\]|does not expose.*(header|include)' knowledge/{graph,doc,drafts}` → **0**。

## 证据（PR/分支/配方/日志）

- 分支 `feat/pd-maxlib-1.6.0`，PR #13770；第二库 `feat/pd-mjlib-0.2.0`，PR #13771。
- 配方 `archives/p/pd-maxlib/1.6.0/conanfile.py` 的 `source()`（PD 源码树）与
  `build()`（`make CC=… PDINCLUDEDIR=…`）。
- 宿主：`archives/p/puredata/0.54.1/conanfile.py` 的 `package()`/`package_info()`。
- `clang -dumpmachine` = `aarch64-unknown-linux-ohos`；`Makefile.pdlibbuilder:473/559`。

## 元信息

- authors: `frj__`（contributor_id: `frj__`）
- source_event: pd-maxlib 1.6.0 + pd-mjlib 0.2.0 OHOS aarch64 适配（2026-09-29）
- draft: true —— 待主编审核后 promote 为正式 E 条目
