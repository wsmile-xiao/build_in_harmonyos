# riece 9.0.0 适配笔记

## 编译环境
- 构建系统: autotools（外壳）+ Emacs 字节编译（实际动作）
- 编译日期: 2026-10-01
- 编译器: 不适用（纯 Emacs Lisp 包；工具链 = conan `emacs/29.1` 提供的 `emacs -batch`）
- 状态: built

## 上游与产物
- 上游: GNU Savannah (nongnu) 项目 `riece` —— https://www.nongnu.org/riece/
- 发布源: https://download.savannah.nongnu.org/releases/riece/riece-9.0.0.tar.gz
- sha256: `88928dc21df3f3b15158e64b77268882544e6afa1d93f3545435ce430837fd2d`
- 源码构成为 100% Emacs Lisp（88 个 `.el`，无任何 `.c/.h/.cc/.cpp`）
- 产物: Emacs Lisp 包（`.el` / `.elc`），安装到 `share/emacs/site-lisp/riece/`

## 编译步骤
```bash
# 依赖：conan 提供 emacs/29.1（emacs 二进制 + 字节编译器）
./configure --prefix=<package_folder> EMACS=<conan emacs>   # OHOS 下经系统 shell 执行
make          # lisp/Makefile: all: elc —— 经 $(EMACS) 字节编译全部模块
make check    # 上游测试：lisp/test/*.el（lunit 框架，经 COMPILE -f riece-test）
# 打包（package()）：经 Emacs 直接驱动上游 riece-install（规避 HMDFS install-sh）
emacs -batch -q -no-site-file -l lisp/COMPILE -f riece-install <src>/lisp <pkg>/share/emacs/site-lisp
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 失败：`config.status[..]: can't create ./confXXXXXX/subs1.awk: Permission denied`；`could not setup config files machinery` | automake 的 `config.status` 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录；HMDFS 强制 setgid 且忽略 chmod，目录权限固定，owner 自己也写不进（知识库 E129） | 补丁 `configure`：两处 `umask 077` → `umask 022`（`patches/0001-configure.patch`） |
| 2 | **三处同源**：`riece-highlight.el:197`、`riece-history.el:68`、`riece-unread.el:63` 的 `(make-face '名 "文档串")` 两参数调用在 GNU Emacs 29 下报 `Wrong number of arguments: (1 . 1), 2` | GNU Emacs 29 的 `make-face` 只接受 1 个参数（`faces.el`：`(defun make-face (face)`，arity `(1 . 1)`）；上游用 XEmacs 风格双参写法。这是 GNU Emacs 29 上游 API 不兼容，**非 OHOS 特有**（Linux + Emacs 29 同样触发） | 补丁 `0003`（riece-highlight）/ `0004`（riece-history）/ `0005`（riece-unread）：三处均改为单参调用，文档串经 `face-documentation` 属性保留 |
| 3 | `make` 失败：`texinfo formatting riece-ja.texi ... Error: (error "@( is not handled by texinfo")`，且 `doc/version-ja.texi`、`doc/version-en.texi` 被整段环境变量表污染 | automake 的 `doc/stamp-vti`、`doc/stamp-1` 规则调用 `mdate-sh`，而 HarmonyOS 的 `ls`（toybox 0.8.12）输出 ISO-8601 日期（无月份名），`mdate-sh` 解析失败（exit 1）；该规则把整段命令组重定向进 `vti.tmp`，`mdate-sh` 失败后其中的裸 `set` 打印全部环境变量，覆盖 `version-*.texi`（知识草稿 DRAFT-11103） | 补丁 `doc/Makefile.in`：将 `stamp-vti` / `stamp-1` 配方改为 `@:`（no-op），使用发行 tarball 自带的 `version-*.texi` 与预编译 info（`patches/0002-doc-Makefile.in.patch`） |
| 4 | `make check` 中 `test-riece-log-display-message-function` 报 `permission-denied "Permission denied" "true"`，且收尾时 emacs 访问 `.`（dired）报 `"ls" Permission denied` | Emacs 经 `exec-path`（由 PATH 派生）查找外部程序；构建 PATH 中 `/usr/bin` 先于 `/system/bin`，`/usr/bin/ls` 指向的 toybox 被构建沙箱拒绝 execve（知识草稿 DRAFT-10038 同源：按解释器路径划分的 exec 域） | 配方 `generate()` 在 OHOS 下把 `/system/bin` 前置到 build PATH，使 emacs 找到可执行的 `/system/bin/ls`、`/system/bin/true` |
| 5 | conan 构建中 `./configure` 报 `Permission denied`，`make install` 报 `install-sh: bad interpreter` | 由 HMDFS 解释器启动的进程，其子进程**直接 execve HMDFS 上的脚本被拒**（DRAFT-10038） | 配方经系统 shell 执行 `configure`；`package()` 经 Emacs 驱动上游 `riece-install`（避开 automake 的 `install-sh`） |

> **关于问题 #2 的关键点（首轮漏修原因）**：三处调用完全同构，且都在顶层 `(unless (riece-facep '…) …)` 块内。字节编译期只会产生 **Warning**（`make-face' called with 2 arguments`），`.elc` 照常产出、`make` 返回 0，因此构建"绿"；但**加载期是硬错误**。`riece-history` / `riece-unread` 均在 `riece-options.el` 的 `riece-addons` 默认列表中，`riece.el` 的 `riece` 入口会 `riece-resolve-addons` 逐个 `require`，任一失败即中断 `M-x riece` 启动。故必须三处全修。

## 源码修改（补丁）

| 补丁 | 目标 | 内容 |
|------|------|------|
| `0001-configure.patch` | `configure` | `umask 077` → `umask 022`（HMDFS 兼容，E129） |
| `0002-doc-Makefile.in.patch` | `doc/Makefile.in` | `stamp-vti` / `stamp-1` 配方改为 `@:`（DRAFT-11103） |
| `0003-lisp-riece-highlight.el.patch` | `lisp/riece-highlight.el` | `make-face` 单参数（Emacs 29 兼容，站点 1/3） |
| `0004-lisp-riece-history.el.patch` | `lisp/riece-history.el` | `make-face` 单参数（Emacs 29 兼容，站点 2/3） |
| `0005-lisp-riece-unread.el.patch` | `lisp/riece-unread.el` | `make-face` 单参数（Emacs 29 兼容，站点 3/3） |

## 依赖版本
- `emacs/29.1`（唯一强制第三方依赖；同时是构建工具链与运行期宿主）
- `ncurses/6.5`（emacs/29.1 的 conan 传递依赖）
- `ruby` / `lsdb` / `XEmacs`：上游可选组件，不参与默认构建，非阻塞

## 验证结果
```bash
# 上游测试（真实执行，构建内嵌 make check）
$ make check
29 runs, 69 assertions, 0 failures, 0 errors      # EXIT=0
# 报告: lisp/lunit-report.xml

# 加载期验证（三处 make-face 站点 + addon 装载路径）
$ emacs -Q --batch -L <lisp> -l verify.el
riece-highlight  => :ok
riece-ctcp       => :ok
riece-rdcc       => :ok
riece-unread     => :ok
riece-history    => :ok
RESOLVE => "ok (17 addons)"        # 等价于 `M-x riece` 的 addon 解析路径
```

## 注意事项
- riece 无任何 C/C++ 依赖，R38 不适用（纯库包，无 commands.json）。
- 运行期可选组件 `ruby`（rirce 代理）、`lsdb`（昵称登记 add-on）不在本包范围内。
- 测试套件中的 `test-riece-log-display-message-function` 与收尾 dired 依赖 emacs 子进程可执行外部程序；在 OHOS 上须保证 `/system/bin` 在 PATH 中优先于 `/usr/bin`（见问题 #4），否则会因沙箱 exec 域限制误报失败。
- 0003/0004/0005 属 GNU Emacs 29 API 不兼容，非 OHOS 特有；`manifest.yaml` 的 `patch_classification` 已据此标注 `platform_only: False`。
