# DRAFT-buildtorrent-0.9.1-autoconf-umask-tmpdir-readonly-fix
> HMFS下Autoconf因umask 077与toybox mktemp导致config.status临时目录只读的通用修复
## 问题特征（真实日志片段/标记）
- 真机compile阶段硬失败：`config.status: error: could not setup config files machinery`，前序为`configure: creating ./config.status -> ./confHbjCiq/subs1.awk: Permission denied`，门禁标记`v2:compile:temporary_directory_readonly`及诊断`readonly_tmp`。
- 平台能力：`HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/50c22647d720/runtime/buildtorrent-0.9.1/tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}`，即`hmbs_platform_capabilities`显示`hmbs_cap_chmod=0`且`local_mktemp=1`。
- configure已执行到config.status收尾阶段，证明可执行位不是主因；机械关键词`readonly_tmp`、`temporary_directory_readonly`、`hmbs_platform_capabilities`、`hmbs_cap_chmod`在upstream/main@dfe3d3ac语料零命中，现有技能库无法解决。
## 根因
- HMFS上toybox `mktemp -d`按`umask 077`创建`drwx--S---`目录并拒绝后续写入，Autoconf `AS_TMPDIR`首选mktemp路径命中该受限目录即硬失败，无法写入`subs1.awk`等临时文件。
- 通用模式：任何configure本体及内嵌config.status模板中保留`umask 077`的Autotools库在HMFS下均可复现，跨库可复用本条。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在`archives/b/buildtorrent/0.9.1/conanfile.py`新增`_patch_configure_umask()`：正则移除configure本体及内嵌config.status模板中`umask 077`/`umask 077 &&`前缀（覆盖mktemp/mkdir两处）。
2. 在`build()`首部将`TMPDIR/TMP/TEMP`统一指向HMBS注入可写tmpdir（`/tmp`或空时回退`build_folder`），仅重定向临时文件根目录，不改安装前缀。
3. 规范`SHELL/CONFIG_SHELL`为`/bin/sh`，`chmod +x`改为容错写法以兼容`HMBS_CAP_CHMOD=0`。
4. 有意不用`mktemp exit-1` shim：`chmod=0`下shim不可执行且`mkdir` fallback自身仍带`umask 077`，不能根治。验证：真机复跑`temporary_directory_readonly`消失并进入后续编译（attempt 399 resolved）。
## 禁止策略
- 禁止用`mktemp exit-1` shim替代umask根因修复；HMBS_CAP_CHMOD=0下shim不可执行且mkdir回退仍带umask 077，仍会复现`config.status: error: could not setup config files machinery`，导致temporary_directory_readonly未消除退回修复循环。
- 禁止忽略config.status错误强行make；禁止非容错`chmod +x`假设chmod可用。
## 与相近条目的边界（查重）
- 本条仅覆盖`temporary_directory_readonly/config.status只读`通用修复；同PR后续`versionsort回退alphasort`属OHOS SDK缺GNU符号的单库语义回退，`package()缺失回退拷贝`属install-sh在HMFS未落盘的安装修复，均不属本条范围。
- 判定为知识库扩展依据：通用模式跨Autotools可复用；零命中增量全部机械关键词在upstream/main@dfe3d3ac无出现。
## 适用判断
- 适用：Autoconf configure含`umask 077`、真机报`subs1.awk: Permission denied`/`could not setup config files machinery`、平台能力`chmod:0`+`local_mktemp:1`+`readonly_tmp`时。
- 不适用：非Autoconf构建、tmpdir可写但报其他权限错误、缺失SDK符号或安装缺失问题，应分流到对应条目。
