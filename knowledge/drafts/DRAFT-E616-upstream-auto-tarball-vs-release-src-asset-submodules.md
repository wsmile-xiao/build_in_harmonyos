# E616（草稿）：上游发布 tarball 的 vendored 子模块边界——自动 tarball 为空、`patch_ng` 行号语义、以及 OHOS 测试工具面

> 状态：**草稿**（libvcflib 1.0.12 适配实测；读数见文末"实证"）。
> 一条主发现（发布 tarball 的子模块边界）+ 三条同批确认的连带发现，都属于「下一个任务还会用到」：
> ①子模块边界 ②手工拆补丁在 `patch_ng` 下的行号语义 ③OHOS 的 `diff` 是 toybox ④子项目的 `add_test` 会进本包 N。

## 错误特征

```
# 用 https://github.com/<org>/<proj>/archive/refs/tags/v<X.Y.Z>.tar.gz 构建时：
CMake Error ... Cannot find source file:
  contrib/fastahack/Fasta.cpp
  contrib/smithwaterman/SmithWatermanGotoh.cpp
  contrib/filevercmp/filevercmp.c
  contrib/fsom/fsom.c
No such file or directory
# 或链接期：
cannot find -lwfa2
# 而 `ls contrib/*/` 每个目录 0 个条目
```

同时 `search-url` / `init-build --auto` 会把**已下线/同名异源**的 URL 标成 `✅ [Official]`：

```
✅ [freedesktop/Savannah] https://download.savannah.nongnu.org/releases/<proj>/<proj>-<ver>.tar.gz
# HEAD 只看到 302 → mirror 的 404（真实响应），目录列表本身 404
```

## 根因

GitHub 的 `/archive/refs/tags/<tag>.tar.gz`（以及 `/archive/<sha>.tar.gz`）是 `git archive` 产物，**只导出被跟踪的文件**：`.gitmodules` 里登记的子模块在 tarball 里是**空目录**（连 gitlink 都没有）。凡把 vendored 依赖放在子模块里的上游，自动 tarball 一定**不可构建**——而这一点在 `CMakeLists.txt` 里看不出来（它照样 `include_directories(contrib/...)`、照样把 `contrib/**/*.cpp` 列进 `add_library` 源清单），失败点在 CMake 配置期才炸，且措辞是「Cannot find source file」，极易被误判成本地解压不全/SHA 不符。

对 vcflib 1.0.12 的实测边界（三类，必须分开数）：

| 类别 | 例子 | 自动 tarball | release `-src` 资产 |
|---|---|---|---|
| 真子模块（vendored 且构建必用） | `contrib/{tabixpp,fastahack,smithwaterman,filevercmp,fsom,intervaltree,multichoose,WFA2-lib}`、`src/simde` | **空**（0 条） | 有（12–22 条/目录） |
| 仓库内自带（非子模块） | `contrib/c-progress-bar`、`src/multichoose.h` | 有 | 有 |
| 只在 CI 拉取、与发布包无关 | `googletest`（根目录，仅在 `.gitmodules`） | 无 | 无（`CMakeLists.txt` 不引用，构建不需要） |

## 解法（推荐）

**优先取上游 release 里附带的「自带子模块」源码资产**，而不是 `archive/refs/tags`：

```sh
# 1) 先看 release 资产列表（自动 tarball 也在里面，注意区分）
curl -sL https://github.com/<org>/<proj>/releases/expanded_assets/v<X.Y.Z> \
  | grep -oE 'href="[^"]+"'
#   /<org>/<proj>/releases/download/v<X.Y.Z>/<proj>-<X.Y.Z>-src.tar.gz   ← 自带子模块
#   /<org>/<proj>/archive/refs/tags/v<X.Y.Z>.tar.gz                      ← 子模块为空
# 2) 下载并核对「子模块目录非空」+ sha256
curl -sL -o src.tar.gz https://github.com/<org>/<proj>/releases/download/v<X.Y.Z>/<proj>-<X.Y.Z>-src.tar.gz
sha256sum src.tar.gz
python3 -c "import tarfile;tarfile.open('src.tar.gz').extractall('.')"
for d in <top>/contrib/*/; do printf '%-40s %s\n' "$d" "$(ls -A "$d" | wc -l)"; done   # 任一为 0 → 该资产不可用
```

**不要**改用发行版（Debian `+dfsg`）的 `orig.tar.xz` 顶替：同样是子模块剥离版（实测 `contrib/*` 同样 0 条），且它是**改写过的 repack**，与上游版本声明不是同一份源码。

## 禁止事项

- ❌ 见 `search-url` 打了 `✅ [Official]` 就采信 URL（HEAD 只代表可达；302→404、停放页、同名异源项目都会通过）
- ❌ 用 `archive/refs/tags/<tag>.tar.gz` 当「上游发布 tarball」而不检查 `contrib/*` 是否为 0 条
- ❌ 把「Cannot find source file: contrib/...」判成本地解压/网络问题去重下
- 后果：配方在 CI 配置期即失败，且失败点离根因（选错 tarball）很远

## 实证

- libvcflib 1.0.12（feat/libvcflib-1.0.12，2026-09-20）：
  - `archive/refs/tags/v1.0.12.tar.gz` 23,543,176 B，sha256 `7ab5b6a87a39105107029f5e0da52ece612c71095ab2aec69a00320f44bc5300`（2026-09-20 复取复算）；`contrib/*` 9 个目录全部 0 条，`src/simde` 0 条，无 `googletest`
  - `releases/download/v1.0.12/vcflib-1.0.12-src.tar.gz` 124,959,767 B，sha256 `cb1e78d675f06ae3b22ffed7e1dea317e4c7f826e51e5b5dabd80240efbe1019`；`contrib/` 9 个目录 5–22 条、`src/simde` 20 条
  - `search-url libvcflib 1.0.12` 报 4 个可用 URL：savannah 两条（目录列表 404）+ `waterlan.home.xs4all.nl` 两条（同名异源，与本包无关）
- 通用性：任何 `.gitmodules` 非空的上游都命中；判据是「release 资产里有没有 `-src`/`-with-submodules` 一类名字的包」或「tarball 内子模块目录条目数 > 0」

## 连带发现 1：手工拆分的补丁必须按 `patch_ng` 的行号语义生成（`patch -p1` 全绿会给假信心）

把同一个 `diff -u` 的 hunk 拆成多个补丁文件时：

- `patch(1)`（GNU）会**搜索偏移**，所以任意行号都能套用 → 本地自测「通过」；
- conan 的 `apply_conandata_patches()` 用 `patch_ng`（`strip=0`，`patch_ng.py:1129-1146`），它
  在「**本补丁开始时的文件状态**」下用 `@@ -<start>,<len> @@` **精确匹配**每个 hunk：
  不搜索偏移，也**不把本补丁自身更早 hunk 的位移算进去**。

正确规则（三轮试错才确定，期间 `patch -p1` 一直"通过"）：

```
start = 原始行号 + Σ(此前【已应用补丁】中、位置在本 hunk 之前的 hunk 净增行数)
```

即：只累计"更早的补丁"的位移，**本补丁自身**的位移不要加；`+start` 与 `-start` 同值即可。
实测三种写法：只用原始行号 → 第 2、3 个补丁 FAIL；把本补丁位移也算进去 → 第 1 个补丁也 FAIL；
只算此前补丁位移 → 全部 OK 且逐字节还原目标树。

装置（本任务手写 12 行）：解出原始树 → `for p in sorted(patches): patch_ng.fromfile(p).apply(strip=0, root=tree)`
→ 与目标树逐字节 diff。**`tools/` 目前没有这个自测**，已在 `feedback/pending/2026-09-20-libvcflib-1.0.12.md` F5 立案。
相关既有条目：E475（patch_ng 需要精确 hunk 偏移）、E515（strip=0 与 a/b 前缀）。

## 连带发现 2：OHOS 的 `/system/bin/diff` 是 toybox，且 OHOS Python 给子进程 PATH **前置** `/system/bin`

- `type diff` 在 Python 拉起的 bash 里 → `/system/bin/diff`；`diff --version` → `toybox 0.8.12`，
  其**默认且唯一**输出格式是 unified（`--- a` / `+++ b` / `@@`），与 GNU diffutils 默认的
  normal 格式（`NcM` / `<` / `---` / `>`）不同。
- 前置是**进程启动层**做的，不是 bash：`env -i PATH=/data/service/hnp/bin python3 -c "import os;print(os.environ['PATH'])"`
  读回 `/system/bin:/usr/bin:/bin:/data/service/hnp/bin` → 任何"用 shell `diff` 比对 GNU 格式期望值"
  的上游测试在 OHOS 上**必然不一致**，且 `PATH=` 前置 GNU 工具目录救不了。
- 判据：凡 doctest/脚本把 `diff`/`grep`/`sed` 交给 shell 并比对**逐字期望输出**，先确认期望值是用哪套
  工具录的；不一致时按"测试工具面差异"记 NOT_RUN（不得写 PASS），不要改上游期望值。

## 连带发现 3：**子项目**的 `add_test` 会进本包的 ctest 注册面 → N 少报的隐蔽来源

`add_subdirectory()` 会连带把子项目 CMakeLists 里的 `enable_testing()`/`add_test()` 带进**同一个**
ctest 注册面。vcflib 用 `-DWFA_GITMODULE=ON` 引入 vendored WFA2，于是 WFA2 的
`add_wfa_test()`（跑 `tests/wfa.utest.sh`）成为本包第 11 个 ctest 用例——**只数主项目的
`add_test` 会少报 1 个**（恰是 rule4 判据「实测 N > 声明 N」的触发形态）。
清点 N 时必须两种都数：主项目注册项 + 所有 `add_subdirectory` 进来的子项目注册项，
并在 PR 正文里逐项归因。

## 连带发现 4：85 个可执行目标 + thin-LTO = 串行构建超预算

上游 `check_ipo_supported()` + `set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ${ipo_supported})` 打开
thin-LTO 后，**每个**可执行文件的链接都要对整库重跑一次 LTO 代码生成（实测 ~19 s/链接，
85 个链接合计 ~28 min），叠加 ~50 min 的编译后在 `jobs=1` 下必然超过 `conan create` 的
3600 s 内建超时。判据：`grep -c '^add_executable' CMakeLists.txt` 很大（>50）且
`check_ipo_supported` 存在时，先估链接预算，必要时显式关 IPO。


## 连带发现 5：`test_package` 的消费者程序可以在**不跑 conan** 的前提下先验证一遍

大包（本例：85 个可执行、串行构建 ~50 min、`conan create` 内建 3600 s 超时）一旦在
`test_package` 阶段失败，代价是一整轮重建。可在本地用 20 行装置把这一步提前：

1. 用一次 `cmake --install <build> --prefix <tmp>` 得到**真实安装树**（头文件+静态库）；
2. 手写一个 `<pkg>-config.cmake`，把 `IMPORTED_LOCATION` 指向安装树里的归档、
   `INTERFACE_INCLUDE_DIRECTORIES` 指向安装出的头文件目录（**别忘传递依赖的头文件目录**）、
   `INTERFACE_LINK_LIBRARIES` 指向依赖的归档/共享库；
3. `cmake -S <test_package 目录> -D<pkg>_DIR=<装置目录> && make && ./<consumer> <fixture>`。

本例实测这一步抓出 6 个必然让正式轮失败的问题：`VariantCallFile::open()` 收的是
**非 const** `string&`（传 `const string` 直接编译错）、头文件里声明的
`countMismatches` 在库里**根本没有定义**（悬空声明）、`is_pure_indel()` 是**非 const**
成员、`parsedAlternates()` 的 key 含**参考等位基因**且 indel 的 vector 同时含参考等位基因
（"size()==1" 式的断言必错）、`reverse_complement` **保留大小写**、`allATGCN` **允许 N**。
**6 个问题里 0 个**能在配方自测里发现，全部只在链接/运行期暴露。

## 连带发现 6：公开头文件 include 了依赖的头 → `requires(..., transitive_headers=True)`（否则"自建全绿、只有消费者红"）

Conan 2 的 `requires()` 默认 **`transitive_headers=False`**：CMakeDeps 给**传递依赖**生成的
`<dep>-release-<arch>-data.cmake` 里 `INCLUDE_DIRS` 是**空的**（逐字复核：
`set(htslib_INCLUDE_DIRS_RELEASE )`），只有**直接** require 该依赖时才写 `<pkg>/include`。

后果形态最阴：本包自己**全绿**（库 + 85 个可执行 + 上游 ctest 6/6 全过），**只有消费者编译会红**：

```
include/vcflib/tabix.hpp:6:10: fatal error: 'htslib/bgzf.h' file not found
```

本例的链路是 `src/Variant.h` → `<tabix.hpp>` → `<htslib/*.h>`，所以消费者必须看得见 htslib 的头。

判据与修法：
- 自检：`grep -rn '#include' <已安装的公开头文件> | grep -E '<dep>/'` 命中即需该 trait；
  或在消费者图上读 `<dep>-*-data.cmake` 的 `INCLUDE_DIRS` 是否为空。
- 修法：`self.requires("<dep>/<ver>", transitive_headers=True)`。
- 1 分钟合成验证（不花构建预算）：造一个 `midprobe/1.0`（只 requires htslib + 该 trait、无 build()），
  `conan create … --build="midprobe/*"`，再让一个消费者 install 并 `grep INCLUDE_DIRS_RELEASE
  htslib-*-data.cmake` —— 从空变成 `${htslib_PACKAGE_FOLDER_RELEASE}/include` 即生效。
- 代价：traits 进 `package_id`，改了就要重建包。

## 红线

- 「上游发布 tarball」= 构建期真正使用的那一份；**必须**在配方 `conandata.yml` 的 `sources.url` 里逐字写清，不得用自动 tarball 的 URL 配 `-src` 资产的 sha256。
- 拆补丁后**必须**用 `patch_ng`（而不是 `patch(1)`）串行套用并逐字节比对目标树；`patch -p1` 通过不构成证据。
- 子项目注册的 ctest 用例**必须**计入本包 N，并在正文逐项归因；不得只数主项目。
- 因测试工具面（toybox diff、缺 `/bin/bash`）跑不了的用例记 **NOT_RUN**，不得写 PASS，也不得改上游期望值。
