# libxdg — freedesktop.org XDG Base Directory Specification 的 C 实现

libxdg-basedir 是 freedesktop.org **XDG Base Directory Specification** 的轻量 C
实现：把规范里"配置/数据/缓存/运行时文件该放哪儿"的规则（`$XDG_CONFIG_HOME`、
`$XDG_DATA_DIRS`、缺省值、搜索顺序、空变量视为未设等）封装成几个可直接调用的
函数，并提供 `xdgConfigFind` / `xdgDataFind` 这类按搜索路径查找文件的辅助接口。

## 功能概述

- **句柄模型**：`xdgInitHandle()` 一次性把环境变量读进 `xdgHandle`（不透明
  `void*` 单指针），之后所有查询走句柄，进程内改环境变量需 `xdgUpdateData()` 重读。
- **Home 查询**：`xdgConfigHome` / `xdgDataHome` / `xdgCacheHome` /
  `xdgRuntimeDirectory`，带规范规定的回退（`$HOME/.config`、`$HOME/.local/share`、
  `$HOME/.cache`；`$XDG_RUNTIME_DIR` 无缺省，未设返回 `NULL`）。
- **目录列表查询**：`xdgConfigDirectories` / `xdgDataDirectories` 按 `:` 切分
  `$XDG_CONFIG_DIRS` / `$XDG_DATA_DIRS`（缺省 `/etc/xdg`、
  `/usr/local/share:/usr/share`），`xdgSearchableConfigDirectories` 等把 home 前置。
- **文件查找/打开**：`xdgConfigFind` / `xdgDataFind` 沿搜索路径返回首个命中的
  绝对路径（双层 NUL 结尾的列表），`xdgConfigOpen` / `xdgDataOpen` 直接 `fopen`。
- **文件系统辅助**（`basedir_fs.h`）：`xdgMakePath()` 递归建目录（类似
  `mkdir -p`），`xdgWriteFile` 等写入辅助。
- 公开头文件只有两个：`basedir.h`、`basedir_fs.h`。

## OHOS 适配要点

- **tarball 不含 configure**：上游只发 `configure.ac` + `m4/`，配方用
  `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")` 在
  `build()` 里 `autoreconf -fi` 现场生成 configure / Makefile.in / config.guess /
  config.sub / ltmain.sh。
- **config.guess/config.sub 不认 HarmonyOS（E007）**：OHOS 上 `uname -s` 字面量是
  `HarmonyOS`，且 `__OHOS__` 下 libc 需识别为 ohos。因这两个文件是 autoreconf
  **生成**的，修复做成 `build()` 内联等价 `scripts/patch-autotools-ohos.pl`
  （4 类共 5 处编辑），不落 `patches/`；改完必须 `chmod 0755`，否则 configure 报
  `cannot run .../config.sub`。
- **HMDFS setgid 与 umask 077（E114/E011）**：生成 configure 里的
  `umask 077 && mktemp -d` 在 HMDFS 上产出 drwx--S--- 目录，连属主都不可写，
  config.status 因 `Permission denied` 失败。`build()` 运行时把所有 `umask 077`
  替换为 `umask 022`（a52dec / adcli / univalue 同款）。
- **SELinux 禁 jobserver FIFO（E074）**：configure/make/make check 一律 `-j1`。
- **out-of-tree(VPATH) 构建下上游用例拼错期望路径**：`tests/querycf.2`、
  `tests/querydf.2` 用 `wd="$(pwd)"` 拼 `"$wd/${top_srcdir}/tests/$basename"`，
  只有当 `${top_srcdir}` 是相对路径时才成立；Conan 始终以绝对路径调用 configure，
  这 2 个用例必失败（29/31）。`patches/0001` 改用
  `td="$(cd "${top_srcdir}/tests" && pwd -P)"`，修后 31/31。该补丁与 HarmonyOS
  无关，属通用可上游修复。
- **安装产物**：静态库 `lib/libxdg-basedir.a` + `include/{basedir.h,basedir_fs.h}`；
  安装后删除 `lib/*.la`（libtool 包装脚本内嵌绝对构建路径）。
- **TMPDIR 必须可写**：OHOS 上 `/tmp` 只读。构建期由 `_prepare_build_env()` 把
  `TMPDIR` 指向 `build_folder/tmp`（`generate()` 与 `build()` 各调一次），否则
  autoreconf 的 autom4te 无法建临时文件；测试期由 `test_package/conanfile.py`
  注入 `TMPDIR=<build_folder>` 后再跑文件系统断言。

## 依赖关系

### 编译依赖
- automake 1.18、libtool 2.5.4（仅 tool_requires，用于 `autoreconf -fi` bootstrap）
- 无第三方运行时库依赖（standalone）

### 运行依赖
- `libc.so`（POSIX `mkdir`/`stat`/`access`/`getenv`/`fopen`）
- `libc++_shared.so` 不涉及（纯 C）

## 版本

| Version | Status |
| --- | --- |
| 1.2.3 | built |

## 参考链接

- 上游仓库：https://github.com/devnev/libxdg-basedir
- release tag：`libxdg-basedir-1.2.3`（无 `v` 前缀）
- XDG Base Directory Specification：https://specifications.freedesktop.org/basedir-spec/latest/
- 许可证：MIT
