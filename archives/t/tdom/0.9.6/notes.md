# tdom 0.9.6 — 适配说明

## 这是什么

**tDOM** 是 Tcl 语言的 XML 处理库（纯 C 实现）：

| 能力 | 说明 |
|---|---|
| XML 解析 | 自带 expat（`Using bundled expat`），支持 DTD、实体、编码转换、Pullparser |
| DOM | 完整 `domNode` API：增删改查、属性、文本节点、文档片段 |
| XPath 1.0 | 路径/谓词/函数（`count`/`sum`/`string`/`position`/…）、命名空间前缀映射 |
| XSLT 1.0 | `$node xslt $styleDoc resultVar` 形式的变换实现 |
| JSON | `dom parse -json` 把 JSON 映射成 DOM |
| 其它 | schema（RELAX NG）、HTML（无 gumbo 时走内置解析器） |

它是 **TEA（Tcl Extension Architecture）** 扩展：构建出 `libtdom0.9.6.so`，由 tclsh
在运行时 `load` 进解释器，Tcl 侧脚本 `tdom.tcl` + `pkgIndex.tcl` 配合提供
`package require tdom`。

## 交付内容（TEA 布局）

```
lib/tdom0.9.6/libtdom0.9.6.so      ← 扩展本体（C + bundled expat + XPath/XSLT）
lib/tdom0.9.6/libtdomstub0.9.6.a   ← tcl stub 库（构建其它 TEA 扩展时用）
lib/tdom0.9.6/tdom.tcl             ← Tcl 侧实现（34KB）
lib/tdom0.9.6/pkgIndex.tcl         ← package require tdom 0.9.6 的注册入口
lib/tdomConfig.sh                  ← TEA 配置（供其它扩展探测）
include/tdom.h                     ← 公开头（C 扩展/嵌入用）
licenses/LICENSE                   ← MPL-2.0
```

> 消费者用法：`lappend auto_path <pkg>/lib/tdom0.9.6; package require tdom`
> （配方通过 runenv 暴露了 `TDOM_TCL_DIR` 便于脚本引用。）

## 关键适配决策

### 1. 依赖只有 tcl，且刻意不用外部 expat

* tdom 链接 tcl 的 **stub 库**（`libtclstub8.6.a`）——TEA 的跨版本加载机制，运行期
  tcl 符号由宿主 `tclsh` 提供 → conan 里 `requires("tcl/8.6.16")` 即可（仓库已发布）。
* expat **随源码分发**，configure 实测走 bundled 版本 → 不需要外部 expat 包，
  也避免 tdom 与宿主 expat 的符号冲突。
* HTML5 需要 gumbo（仓库未发布）→ 保持上游默认 `--disable-html5`。

### 2. TEA configure 的三个关键参数

```
--with-tcl=<tcl 包内含 tclConfig.sh 的目录>   # conan tcl 包在 lib/
--with-tclinclude=<tcl 包>/include          # tdom 显式支持，避免 tclConfig.sh 里写死路径
--disable-html5
tcl_cv_sys_version=Linux-6.6 / ac_cv_prog_cc_works=yes
```
（tkpng 0.9 用同样的方式接 tcl 包；后两个缓存变量是 TEA configure 在沙箱里需要的。）

### 3. 上游 Makefile 的 `TCLSH_ENV` 在 conan 场景下是坏的

上游：

```make
TCLSH_ENV = TCL_LIBRARY=`@CYGPATH@ $(TCL_SRC_DIR)/library`
TCLSH     = $(TCLSH_ENV) $(PKG_ENV) $(TCLSH_PROG)
```

`TCL_SRC_DIR` 来自 tclConfig.sh，指向安装时已不存在的构建目录 → tclsh 会找不到
`init.tcl`。解法（redis 6.2 同款）：

```python
self.run('make check TCLSH_ENV="TCL_LIBRARY=%s" > "%s" 2>&1' % (tcl_library, log),
         env="conanrun")
```

### 4. HMDFS / 沙箱三处适配

1. `configure` 里的 `umask 077` → `umask 022`（E011：HMDFS 下 0600 临时目录不可写）；
2. 时间戳摆平：`configure.ac`/`tdom.m4` = now-5，`configure`/`Makefile.in`/`aclocal.m4`
   = now，避免 make 误判要 automake 重生成（否则报
   `newly created file is older than distributed files`，与 worker OOM 同文案）；
3. `make install` 的 install-sh 会把 `exec_prefix` 解析成 `/usr`（与 `--prefix` 不一致）
   → `package()` 先 `make install DESTDIR=<stage>` 再按 TEA 布局显式收集
   （tkpng 0.9 先例），避免出现 `<package>/usr/lib/...` 这种畸形布局。

### 5. 补丁（1 个）

`patches/0001-add-make-check-target.patch`：给 `Makefile.in` 加一个

```make
check: test
```

别名。上游只有 `make test`，而 autotools 惯例是 `make check`；补上别名后 CI 的 L1c
门禁能识别「上游测试真跑」，测试内容一个字没改。

## 测试证据（平台 rule12）

### ① 上游官方测试套件：build() 内 `make check` 真跑

```
all.tcl:	Total	2459	Passed	2392	Skipped	67	Failed	0
Sourced 27 Test Files.
Number of tests skipped for each constraint:
	11	Tcl9   23	html5   9	knownBug   10	need_uri   10	nonetest   4	beyondBMP
```

2459 个用例全部执行（27 个测试文件：dom / domNode / xpath / xslt / schema / json /
pullparser / parser / i18n / tdomcmd …，含 OASIS XML 一致性套件），**Failed = 0**，
完全无头（不碰 X11/GPU/声卡/网络）。解析该汇总行为硬门禁：取不到汇总行或 Failed ≠ 0
都让 `build()` 直接失败，并输出 `HMBS_UPSTREAM_TEST_RESULT total=… passed=… failed=…`。

### ② 完整消费者用例（端到端业务流程，21 项）

`test_package/test_tdom.tcl`：只用交付物（`package require tdom` 真实走
pkgIndex.tcl → tdom.tcl → `load .so`），流程与核对结果：

1. `package require tdom` 得到 0.9.6；交付物含 .so / tdom.tcl / pkgIndex.tcl；
2. XML 解析 + DOM 结构（根节点 `catalog`、2 个子元素）与属性读取（`id`/`lang`）；
3. XPath 1.0：谓词 `book[@id='b2']/title` → 鸿蒙；`count()` = 2；`sum(price)` = 192；
   命名空间前缀映射 `//dc:creator[.='开放原子']` → 开放原子；
4. DOM 增删改：追加节点后 `count()` = 3，删除后回到 2；
5. `asXML` 序列化（278 字节）后**再解析**，书目数据一致（往返无损）；
6. XSLT 1.0 变换输出 `HarmonyOS|,鸿蒙|`（for-each + value-of + position/last）；
7. JSON 解析：`dom parse -json` → XPath 取到 `name=tdom`，序列化含 `nested` 键；
8. 500 节点大文档：`count()` = 500、`position() mod 100 = 0` 命中 5 个、
   按属性取第 250 个节点文本 = n250；
9. 错误路径：非法 XML（`<a><b></a>`）必须报错。

实测输出：`tdom 消费者用例结果：21 项检查，0 项失败`。

### ③ 适配自检（M = 17 条，非上游用例）

`test_package/test_layout.py`：TEA 布局四件套、ELF magic + `ET_DYN` + 体积、
pkgIndex 注册 0.9.6、tdom.tcl 非空壳、`include/tdom.h`、`tdomConfig.sh`、MPL-2.0
LICENSE、无 `bin/`（故不需要 commands.json）、无 `usr/` 前缀、无构建中间产物、
无隐藏文件（JC5）、未夹带上游 `tests/`。实测 17/17 通过。

## 版本与来源

* 上游：<http://tdom.org>（TEA 扩展的标准分发就是这份 `-src.tgz`，上游无 GitHub tag）
* tarball：`https://tdom.org/downloads/tdom-0.9.6-src.tgz`
* sha256：`6d24734aef46d1dc16f3476685414794d6a4e65f48079e1029374477104e8319`
  （1530711 字节；下载双校验：sha256 + `tar tzf | wc -l` = 274；
  与 Debian orig `tdom_0.9.6.orig.tar.gz` 字节一致）
* 许可：MPL-2.0（`LICENSE` 随包交付）
