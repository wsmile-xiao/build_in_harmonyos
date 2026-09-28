# DRAFT：`PKG_CHECK_MODULES` 要求的模块**有真实上游提供者**、但提供者是「另一个包的子库」→ 取上游 tarball 就地编译**最小符号闭包**，而不是伪造 `.pc` 或手写符号桩

> 状态：草稿（待知识库主编 promote）
> 来源：xauth 1.1.4 适配，`archives/x/xauth/1.1.4`（任务 #5922）
> 类别：autotools / configure / pkg-config / conan / dependency / portability

## 错误特征

`configure` 阶段停机，缺失的是 `xmuu` 模块：

```
checking for XAUTH... no
configure: error: Package requirements (x11 xau xext xmuu xproto >= 7.0.17) were not met:

Package 'xmuu', required by 'virtual:world', not found

Consider adjusting the PKG_CONFIG_PATH environment variable if you
installed software in a non-standard prefix.
```

或者在精简 worker 上退化成没有 pkg-config 可执行的形态（同 libXp）：

```
./configure: line 19277: pkg-config: command not found
configure: error: The pkg-config script could not be found. ...
```

**与「模块已被并入其它包、生态里彻底消失」的关键区别在确诊查询**：
这里不是查不到提供者，而是**提供者存在、但制品仓没有它的包**。

```bash
# (a) 制品仓里没有任何包提供它（xmuu 与它的父包 libxmu 都空）
conan list "libxmuu/*" -r ohpcd   # → Found 0 pkg/version recipes
conan list "libxmu/*"  -r ohpcd   # → Found 0 pkg/version recipes

# (b) 但上游**确实**发布过这个模块 —— 它不是一个被撤销的模块，
#     而是 libXmu 这个包里的**并列第二子库**
#     libXmu-<ver>.tar.xz 的构建产物是 libXmu.la + libXmuu.la，
#     xmu.pc 与 xmuu.pc 由同一次构建并列安装。
```

判据：**模块名指向一个真实存在、有官方 tarball 的库/子库，只是这个库没有被适配进制品仓。**
这与 printproto 那种「X.Org 7.7 起独立发行物被撤销、并入 xorgproto」是两码事。

## 触发条件

四条同时成立：

1. 上游 `configure.ac` 用 `PKG_CHECK_MODULES` 列了一个制品仓没有对应 Conan 包的模块；
2. 该模块**有**真实上游提供者（能查到官方发布页 / tarball / sha256），
   不是被并入别处后消失的历史化石；
3. 提供者是某个包的**子库**（一次构建发布多个 `.la` / 多个 `.pc`），
   而不是一个独立顶层项目；
4. 消费者对该子库的引用面**极窄** —— 只用到一两个符号。

第 4 条是可做性的前提。xauth 全树对 Xmu 的引用只有一处：

```
parsedpy.c:40  #include <X11/Xmu/SysUtil.h>
parsedpy.c:76  (void) XmuGetHostname (buf, maxlen);
```

`XmuGetHostname` 定义在 libXmu 的 `src/GetHost.c`，非 WIN32 分支只 include
`<X11/Xosdefs.h>` / `<string.h>` / `<unistd.h>` / `<X11/Xmu/SysUtil.h>`，
且 `config.h` 的引入被 `#ifdef HAVE_CONFIG_H` 守卫 —— 不定义就不需要 config.h，
**也就不需要跑 libXmu 自己的 configure**。

## 根因分析

### (1) `PKG_CHECK_MODULES` 的硬失败语义

`PKG_CHECK_MODULES(PREFIX, MODULES)` 展开成：先看 `$PREFIX_CFLAGS` / `$PREFIX_LIBS`
是否非空；**都为空**才真正调用 `pkg-config`。求解失败即 `AC_MSG_ERROR` 停机。
（这一层与 libXp 的条目完全相同，见 `similar_to`。）

### (2) 「制品仓没有包」≠「上游没有这个模块」

xauth 的 `configure.ac:53` 写的是当时正确的模块列表。X.Org 的拆分方式是：
`libXmu` 与 `libXmuu` 是**同一个源码包的两个子库**（`src/` 下的 `libXmu` 部分与
`libXmuu` 部分各自 `noinst` 汇总成一个 convenience library，最终并列安装
`libXmu.so` / `libXmuu.so`、并列发布 `xmu.pc` / `xmuu.pc`）。适配制品仓时只把
`libXmu` 主体做了包、或干脆两者都没做，就会出现「模块名在生态里合法、
在制品仓里查无此包」。

**这正是容易被误判的两步**：
- 误判一：以为 `xmuu` 是历史化石（像 `printproto`），于是只走 `AC_ARG_VAR` 逃生口 ——
  但这里模块的真实语义（`XmuGetHostname` 的实现）**没有被任何已发布包提供**，
  逃生口只能把「找不到模块」变成「链接期 undefined reference」；
- 误判二：以为制品仓缺的是 `libXmu` 顶层包，于是去适配一个完整 libXmu ——
  但消费者只用一个符号，把整包拉进来是无谓的工作量与依赖面扩大。

### (3) 三个方案的取舍

| 路线 | 做法 | 判定 |
| --- | --- | --- |
| A | 伪造一个 `xmuu.pc` 指向某个空库 / 塞进 `PKG_CONFIG_PATH` | 链接期 undefined reference；且没有任何上游产物支撑，属伪造事实 —— **禁止** |
| B | 手写 `XmuGetHostname` 桩（或等价实现） | 复制上游逻辑，产权不清（`xinit/1.4.4` 手写 `Xlib.h` + `x11_stub.c` 是反面教材）—— **禁止** |
| C | 从 libXmu 官方 tarball 取 libXmuu 的**真实源码**就地编译 | 源码本体即上游产物（sha256 官方值），零改写，静态随包携带 —— **采用** |

选 C 的依据：与仓库既有的 E277 vendored 依赖模式同构（`xeyes/1.3.1` 内建
libICE/libSM/libXt/libXmu/libXi、`clinfo` 内建 OpenCL-ICD-Loader）。
**与 E277 的差别是「源码从哪来」**：

- E277：源码**已经在消费者自己的 tarball 里**（上游 inner tarball / bundled 目录）；
- 本条目：源码在**提供者自己的 tarball 里**，消费者 tarball 内没有。
  所以在 `source()` 阶段额外 `get()` 一份提供者的官方 tarball 放到
  `<source_folder>/vendor-<name>/`，供 build 就地编译。

## 最小闭包选择依据（为什么只编 1 个 .c）

libXmuu 有 5 个源文件（`ClientWin.c` / `CursorName.c` / `DefErrMsg.c` /
`GetHost.c` / `Lower.c`），但 xauth 只引用其中 1 个符号，定义在 `GetHost.c`。

**多编另外 4 个反而会引入新的私有头依赖**：`DefErrMsg.c` include 了
libX11 的私有头 `<X11/Xlibint.h>`。制品仓里确实有 `Xlibint.h`，但那是
X11 的私有头，跨版本不保证；而 xauth 一个符号都用不到它。
按实际需要取最小闭包，是「编译它但因为没链接到所以暂时没事」与
「依赖面保持可证明的最小」之间的选择。

产物命名为 `libXmuu.a`，与上游 `xmuu.pc` 的 `Libs: -L${libdir} -lXmuu` 对齐 ——
若将来改为真依赖，`-lXmuu` 的名字不用改。

## 方案实现要点（Conan 配方侧）

```python
# conandata.yml：两个 source 并列
sources:
  xauth:
    url: "https://xorg.freedesktop.org/archive/individual/app/xauth-1.1.4.tar.xz"
    sha256: "e93181..."
  libxmu:                                    # ← 提供者的官方 tarball
    url: "https://xorg.freedesktop.org/archive/individual/lib/libXmu-1.3.1.tar.xz"
    sha256: "81a99e..."

# source()：消费者 tarball 解到 source_folder，提供者 tarball 解到子目录
get(self, **self.conan_data["sources"]["xauth"], strip_root=True)
vendor = os.path.join(self.source_folder, "vendor-libxmu")
os.makedirs(vendor, exist_ok=True)
get(self, **self.conan_data["sources"]["libxmu"], strip_root=True, destination=vendor)

# build()：编译最小闭包（只编 GetHost.c），头文件直接取 vendor/include
clang -fPIC -O2 -I<vendor>/include -c <vendor>/src/GetHost.c -o GetHost.o
llvm-ar rcs libXmuu.a GetHost.o

# generate()：用 PKG_CHECK_MODULES 的 AC_ARG_VAR 逃生口把 CFLAGS/LIBS 直接喂进去，
# 既不调用 pkg-config、也不需要 xmuu.pc
env.define("XAUTH_CFLAGS", "-I<vendor>/include -I<dep>/include ...")
env.define("XAUTH_LIBS",   "-L<vendor>/lib -lXmuu -L<dep>/lib -lX11 -lXext -lXau")
```

注意这里**两条路是叠加使用而非二选一**：`AC_ARG_VAR` 逃生口负责「不调用
pkg-config」，vendored 编译负责「`-lXmuu` 真有东西可链」。只做前一半会得到
链接期 undefined reference；只做后一半则 configure 仍会因缺 `xmuu.pc` 停机。

## 验证命令

```bash
# 1) 确诊「模块有真实提供者，只是制品仓没有它的包」（双查，避免与 libXp 那类混淆）
conan list "libxmuu/*" -r ohpcd        # → Found 0
conan list "libxmu/*"  -r ohpcd        # → Found 0
# 同时确认上游有官方 tarball 与 sha256（xorg.freedesktop.org/archive/individual/lib/）

# 2) 确认引用面确实只有一个符号（决定最小闭包大小）
grep -rn 'Xmu' --include='*.c' --include='*.h' .        # → 只有 SysUtil.h 与 XmuGetHostname
nm -u <编译出的解析对象> | grep -i xmu                  # → 只有 XmuGetHostname

# 3) 确认逃生口存在（用 tarball 自带的 configure，不要 autoreconf）
grep -n 'if test -n "\$XAUTH_CFLAGS"' configure         # → 命中
grep -n 'if test -n "\$XAUTH_LIBS"'   configure         # → 命中
# 非空即不调用 pkg-config（xauth 1.1.4 实测第 11988 / 12005 行）

# 4) 编译最小闭包并确认符号
llvm-ar t libXmuu.a                                     # → GetHost.o
nm libXmuu.a | grep XmuGetHostname                      # → T XmuGetHostname

# 5) 构建后确认链接结果真的用了 vendored 库
nm -u <pkg>/bin/xauth | grep -i Xmu                     # → 无输出（已静态满足）
readelf -d <pkg>/bin/xauth | grep NEEDED               # → 不含 libXmuu.so（静态随包）
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 伪造一个指向空库 / 任意库的 `xmuu.pc` 塞进 `PKG_CONFIG_PATH` | 伪造一个制品仓里不存在的产物，把「找不到模块」变成「链接期 undefined reference」 | 症状后移且更难定位；知识库被污染（同 libXp 条目） |
| 手写 `XmuGetHostname` 桩或等价实现 | 复制上游实现逻辑，产权不清；且等于对 CLI 工具注入一个自造行为（`xinit/1.4.4` 手写 `Xlib.h` + `x11_stub.c` 是反面教材） | 适配的是「自造的库」而不是上游库；评审不可信 |
| 把 libXMu 的**全部** 5 个 `.c` 都编进来「以防万一」 | 多编的 4 个一个符号都用不到，却引入对 libX11 私有头 `<X11/Xlibint.h>` 的依赖 | 依赖面被人为放大到跨版本不保证的私有头；构建脆弱 |
| 用 `PKG_CONFIG_PATH` 指向 vendored 目录但**不**给 `xmuu.pc` 打补丁 | configure 仍会因缺 `.pc` 停机（模块名不匹配） | 白跑一轮 |

## 关联

- `similar_to` **E277**（库自带 vendored 依赖且 registry 无配方时，在 build() 内编译子项目到 staging）：
  本条目是它的**同族变体** —— 同样是「制品仓无配方 → 就地编译上游真实源码」，
  但源码来源不同：E277 的源码在**消费者自己的 tarball** 里，本条目的源码在
  **提供者自己的 tarball** 里，因此多了一步 `source()` 期的第二个 `get()`。
- `similar_to` **DRAFT-libxp-1.0.4-configure-pkgconfig-printproto-module-removed**：
  区别在**模块是否还有真实提供者**。libXp 的 `printproto` 自 X.Org 7.7 起被
  `xorgproto` 取代、独立发行物正式撤销 → 正确答案是 `AC_ARG_VAR` 逃生口（头文件
  需求已由 xorgproto 满足）。xauth 的 `xmuu` **没有被任何已发布包提供其实现** →
  逃生口只能解决「不调用 pkg-config」，**必须再叠加 vendored 编译**。
  两条的诊断入口相同（看 configure 报哪个模块），但确诊查询和方案不同：
  **先查「提供者还在不在」，再决定走哪条路。**
- `similar_to` **E002**（鸿蒙 `/tmp` 是 erofs 只读挂载）：同批 xauth 适配里的另一条，
  xauth 的测试夹具写 `${DATADIR:-/tmp}`，解法是把 `DATADIR`/`TMPDIR` 作用域内
  指向 `build_folder/test-scratch`（带默认值的环境变量 → 无需改上游测试脚本）。

## 上游可提交性

**不可向上游提交**：`configure.ac` 的模块列表（`x11 xau xext xmuu xproto`）在
上游生态里是正确且可满足的 —— libXmuu 是官方发布的子库。问题出在**制品仓的
覆盖缺口**，不在上游源码。

因此本条目的正解分为两层：

1. **本配方内**（已实施）：vendored 编译最小闭包，保证 `xauth/1.1.4` 自包含可构建；
2. **生态层**（应记录，不在本 PR 内实施）：给 `libxmu/1.3.1` 出独立 Conan 配方，
   发布 `libXmu` + `libXmuu` 两个子库与 `xmu.pc` + `xmuu.pc` 两个模块。
   届时本配方应改为真 `requires` 并删除 vendored 块；`libxaw` 的阻塞
   （依赖 libxmu/1.3.1 未发布）也会一并解除。
