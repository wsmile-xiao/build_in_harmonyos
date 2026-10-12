# DRAFT-tta-2.2-hmdfs-autoconf-as-tmpdir-umask-mkdir-fallback

> HMDFS 上 autoconf AS_TMPDIR 用 `mktemp -d ./conf*` 生成的暂存目录不可写（chmod 0/umask 077）时以 mkdir fallback 或 umask 022 修复

## 问题特征（真实日志片段/标记）

真机 compile 阶段 configure 尾声报错（HMBS 平台诊断 `[unsafe_local_mktemp]`）：


./config.status: can't create ./conf*/subs1.awk: Permission denied
./config.status: error: could not setup config files machinery


随后出现目录名形如 `confhJcLnj` / `conf38147-4383` 的 mktemp/PID-RANDOM 随机后缀，证明 AS_TMPDIR 已执行并落盘出一个 config.status 无法写入的目录。平台能力标记：


HMBS_PLATFORM_CAPABILITIES={"chmod":0,"symlink":1,"local_mktemp":1,...}


（`HMBS_CAP_CHMOD=0`，chmod 能力被禁用。）

同系列还伴随 autoconf 在 HMDFS 上 `getcwd(2)` 失败（工具链 bash 场景下 `shell-init: error retrieving current directory: getcwd: cannot access parent directories` 后 `configure: error: working directory cannot be determined`）。

## 根因

autoconf 的 `AS_TMPDIR` 在 configure/config.status 中默认用 `(umask 077 && mktemp -d "./confXXXXXX")` 在构建目录创建暂存目录。在 HMDFS 上存在两层不可写问题：

1. **mktemp 落盘目录 owner 不可写**：平台 `HMBS_CAP_CHMOD=0`，无法靠 chmod 修正；若依赖 build-only `mktemp` shim（靠 `os.chmod(shim, 0o755)` 置可执行），chmod 不支持会让 shim 从未挂上，mktemp 照常运行。
2. **即使走了 mkdir fallback 也失败**：`(umask 077 && mkdir "$tmp")` 在 HMDFS 的 setgid 目录上创建的暂存目录 owner 不可写（E011/已记于 zzuf/liblzf 的同类问题），config.status 仍写不了 `subs1.awk` → Permission denied。

即真正病灶不是 mktemp 本身，而是 HMDFS 上 `umask 077` 使生成目录 owner 不可写，叠加 chmod 能力缺失。

## 修复方案（rec）

推荐**确定性打补丁改走 mkdir fallback 并放开 umask 为 022**（不依赖 mktemp、chmod、symlink、环境变量，全宿主可用）：

1. `patches/0003-configure-as-tmpdir-mkdir.patch`：修改生成 `configure` 的 AS_TMPDIR 分支，去掉 mktemp 分支，恒定走 `(umask 022 && mkdir "$conf$$-$RANDOM")`，使 config.status 生成的 `./conf*` 暂存目录 owner 可写。
2. `conanfile.py` `build()`：用 `umask 022` 前缀运行 configure，让 configure/config.status 子进程继承可写 umask；make 追加 `SHELL=/bin/sh`。
3. `CONFIG_SHELL=/bin/sh`：以内联前缀 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh "<source>/configure" ...` 运行 configure，绕开工具链 buildenv 指向的、在 HMDFS 上 `getcwd(2)` 失败的 bash，覆盖同类 autotools 库的通用 getcwd 内核。
4. `conandata.yml` + `notes.md`：登记 0003 补丁与 umask/决策记录，保持一致。

备选（无法改 configure 时）：build-only `mktemp` shim 仅对 `./conf*` 模板返回失败以触发 autoconf 自带 mkdir fallback；但 shim 必须可执行，`HMBS_CAP_CHMOD=0` 下不能依赖 `os.chmod(..., 0o755)`。

验证：真机 configure 阶段不再出现 Permission denied / could not setup config files machinery，config.status 能向 `./conf*` 暂存目录正常写入并产出 Makefile。

## 禁止策略

- 禁止保留 `(umask 077 && mkdir ...)` 或 `(umask 077 && mktemp -d ...)`：HMDFS 上 umask 077 使 setgid 目录 owner 不可写，chmod 能力为 0 无法修正，会复现 Permission denied。
- 禁止假设 `HMBS_CAP_CHMOD=1`（能 chmod 修正）或依赖 `os.chmod` 置 shim 可执行。
- 禁止仅靠 `mktemp` shim 而不处理 umask；shim 只解决 mktemp 分支，不解决 mkdir fallback 的 umask 077 病灶。

## 与相近条目的边界（查重）

- `DRAFT-alberta-cyrus-sasl-*`：同为 HMDFS 上 mktemp shim 触发 Autoconf mkdir fallback 的可复用机制；本条目进一步定位到 mkdir fallback 内部 `umask 077` 的 owner 不可写病灶并切换到 `umask 022`，且不限 tta、覆盖一类 autotools 库。
- `DRAFT-zzuf-liblzf-*`：zzuf/liblzf 在 zzuf 侧记录 E011/HMDFS 的 umask 077→022 放宽；本条目落在 autoconf `AS_TMPDIR` 的 configure/config.status 落盘写权限场景，故障签名（`subs1.awk Permission denied`）相邻但不相同。
- `getcwd` 相关条目：本条目附带 `CONFIG_SHELL=/bin/sh` 修复 HMDFS 上 autoconf `getcwd(2)` 失败的通用内核，属相邻但独立维度，不影响 mktemp/umask/AS_TMPDIR 主主题。

以上查重命中条目均无法单独覆盖本任务的 mktemp/umask/AS_TMPDIR 落盘写权限场景，本条目为知识库扩展。

## 适用判断

适用于在 HMDFS/HMFS 构建目录上运行 autoconf 系 configure/config.status、使用 AS_TMPDIR 暂存目录且遭遇 `./conf*` 落盘不可写的 autotools 类 C/C++ 库。满足如下任一特征即应命中：configure 阶段 `Permission denied` 写入 `./conf*`、`could not setup config files machinery`、`subs1.awk` 写入失败，或平台标记 `HMBS_CAP_CHMOD=0` 叠加 `umask 077`。
