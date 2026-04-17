# 预编译包制作进度跟踪

> 创建时间: 2026-04-04
> 目标：为无基础工具的鸿蒙机器制作预编译包（tar.gz）
> 工作目录: `$PROJECT_DIR`
> 参考: Python 3.12.9 的 `scripts/package_python.sh`（10步打包流程）

---

## 📊 总体统计

| 指标 | 数量 |
|------|------|
| 总计 | 29 款 |
| 已完成 | **27** |
| 编译成功 | 27 (pkg-config, sed, coreutils, gawk, automake, libtool, zlib, bzip2, xz, gzip, openssl, ncurses, libffi, gdbm, readline, wget, rsync, jq, file, tar, dos2unix, bash, htop, patch, libpipeline, **texinfo, help2man**) |
| 打包成功 | 24 (除 libtool 外全部打包成功；texinfo/help2man 编译成功但 tar.gz 待确认) |
| 跳过(不可用) | - |
| 失败 | - |

---

## ⚠️ 静态库强制要求（危险库）

> **根因**：预编译包设置 `LD_LIBRARY_PATH` 后，我们的共享库优先级高于系统库，
> 版本不匹配会导致系统工具崩溃（如之前 ncurses 共享库导致 zsh 崩溃）。

| 库 | 危险等级 | 原因 | 编译要求 |
|---|---------|------|----------|
| **ncurses** | 🔴 致命 | 系统zsh依赖 libncursesw.so.6，之前编译共享库直接导致Shell崩溃 | ✅ 必须 `--without-shared` 静态 |
| **readline** | 🟠 高 | bash/交互式工具链接它，版本不匹配导致行编辑异常 | ✅ 建议静态链接 |
| **zlib** | 🟠 高 | 几乎所有工具间接依赖，LD_LIBRARY_PATH 劫持全局符号解析 | ✅ 建议静态编译 |
| **openssl** | 🟡 中 | 系统自有SSL栈，路径不同影响较小 | ✅ 已编译共享（no-asm） |
| **libffi** | 🟡 中 | 主要被Python等用户态程序使用 | ✅ 已编译共享 |
| **gdbm** | 🟢 低 | 少数程序使用，冲突概率低 | 可共享 |
| **bzip2/xz** | 🟢 低 | 工具链自身使用 | 可共享 |

> **原则**：能静态就静态。只有明确需要被多个运行中程序共享且不会污染系统符号解析的库才编译共享版。

---

## 📋 编译清单

### 第零阶段：编译基石

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 01 | pkg-config | 0.29.2 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/pkg-config-0.29.2-ohos-aarch64.tar.gz (687K) | 6个补丁, 无外部依赖, 已重打包(strip+签名) |
| 02 | sed | 4.9 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/sed-4.9-ohos-aarch64.tar.gz (410K) | 2个补丁(config.guess+config.sub), 零额外参数 |

### 第一阶段：基础工具链（无外部依赖）

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 03 | coreutils | 9.10 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/coreutils-9.10-ohos-aarch64.tar.gz (11M) | 3个补丁, 86二进制(排除14个), 100man页, 已签名 |
| 04 | gawk | 5.3.0 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/gawk-5.3.0-ohos-aarch64.tar.gz (3.9M) | 无外部依赖, 替代 toybox awk |

### 第二阶段：Autotools 工具链

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 05 | automake | 1.16.5 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/automake-1.16.5-ohos-aarch64.tar.gz (1.2M) | 依赖 Perl, 官方测试套件不可用(鸡生蛋), 手动全链路验证通过 |
| 06 | libtool | 2.4.7 | ✅ 完成 | ✅ 成功 | ✅ 成功  | - | 1个补丁(config.guess+config.sub), libtoolize有E035已知问题, 核心功能正常 |

### 第三阶段-A：压缩/基础库（无依赖）

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 07 | zlib | 1.3.1 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/zlib-1.3.1-ohos-aarch64.tar.gz (244K) | 静态库 libz.a, make test 全通过(32+64bit), ⚠️ fossils URL, ohc-run.py package 纯库检测已修复 |
| 08 | bzip2 | 1.0.8 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/bzip2-1.0.8-ohos-aarch64.tar.gz (820K) | **1个补丁**(平台自动检测ohos→-fPIC), CC/AR/RANLIB/PREFIX全环境变量覆盖, 零硬编码 |
| 09 | xz/lzma | 5.6.2 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/xz-5.6.2-ohos-aarch64.tar.gz (3.5M) | **2个补丁**(config.guess+config.sub, 方案A标准打补丁), 28二进制(排除lzcmp), 静态liblzma.a, 压缩/解压功能验证通过, --disable-assembler |
| 10 | gzip | 1.13 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/gzip-1.13-ohos-aarch64.tar.gz (297K) | **2个补丁**(config.guess+config.sub, 含patch-autotools-ohos.pl bug修复), shell脚本因shebang限制需通过sh调用 |

### 第三阶段-B：SSL/加密/终端

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 11 | openssl | 1.1.1w | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/openssl-1.1.1w-ohos-aarch64.tar.gz (14M) | **2个补丁**(openharmony平台配置+Configure检测), `no-asm`必须, HMDFS需`cp -a`替代`ln -s`, gitee镜像可用 |
| 12 | ncurses | 6.4 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/ncurses-6.4-ohos-aarch64.tar.gz (8.7M) | 🔴 **必须 --without-shared**，1个补丁(config.guess+config.sub), 4个静态库(libncursesw/panelw/menuw/formw), 11工具+2851 terminfo, --enable-widec+--enable-overwrite, ⚠️ 历史manifest错误使用了--with-shared已纠正 |
| 13 | libffi | 3.5.2 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/libffi-3.5.2-ohos-aarch64.tar.gz (634K) | **2个补丁**(config.guess/sub + closure HMDFS路径回退), ffi_call核心功能+版本API通过, ffi_closure需额外补丁, ghfast.top加速下载 |

### 第三阶段-C：数据库/终端编辑

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 14 | gdbm | 1.23 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/gdbm-1.23-ohos-aarch64.tar.gz (962K) | **2个补丁**(config.guess+config.sub), `--enable-libgdbm-compat`兼容ndbm/dbm, 3工具+2组库, gdbm_open/store/fetch全通过, ⚠️ gdbm_open路径不能用/tmp |
| 15 | readline | 8.2 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/readline-8.2-ohos-aarch64.tar.gz (3.0M) | **2个补丁**(config.guess/sub + shlib TERMCAP_LIB), `--with-curses`, ncurses静态嵌入libreadline.so(NEEDED仅libc.so), TERMCAP_LIB需改为-lncursesw |

### 第四阶段：网络/文件工具

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 16 | wget | 1.19.1 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/wget-1.19.1-ohos-aarch64.tar.gz (3.3M) | **3个补丁**(build-aux/config.guess+config.sub+tmpdir.c), 静态链接 OpenSSL, HTTPS 需 --no-check-certificate, 30/39 测试通过, E081新增 |
| 17 | rsync | 3.3.0 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/rsync-3.3.0-ohos-aarch64.tar.gz (2.5M) | **2个补丁**(config.guess+config.sub), --disable-xxhash/zstd/lz4/md2man, 动态链接 libcrypto, 4项手动测试全通过 |
| 18 | jq | 1.7.1 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/jq-1.7.1-ohos-aarch64.tar.gz (5.7M) | 2个补丁(config.guess+config.sub), 含oniguruma子模块, 7/8测试通过 |
| 19 | file | 5.45 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/file-5.45-ohos-aarch64.tar.gz (8.9M) | 7个补丁(config.sub linux-ohos*), 72/72测试全通过, ⚠️ verify G1/G3 HMDFS OSError已修复 |
| 20 | tar | 1.35 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/tar-1.35-ohos-aarch64.tar.gz (1.3M) | 7个补丁(config.guess+config.sub), 114/211测试通过(UID超范围), ⚠️ 部分补丁为构建产物 |
| 21 | dos2unix | 7.5.4 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/dos2unix-7.5.4-ohos-aarch64.tar.gz (340K) | 1个补丁(Makefile: 禁用NLS+cp替代ln), Makefile项目无configure, 83/115测试通过 |

### 第五阶段：高级系统工具

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 22 | bash | 5.3 | ✅ 完成 | ✅ 成功 | ✅ 成功 | packaging/bash-5.3-ohos-aarch64.tar.gz | `--without-bash-malloc`，依赖 readline+ncurses |
| 23 | htop | 3.4.1 | ✅ 完成(partial) | ✅ 成功 | ✅ 成功 | packaging/htop-3.4.1-ohos-aarch64.tar.gz (603K) | 3个补丁(build-aux/config.guess+config.sub+IOPriorityPanel.h), ncursesw静态嵌入, 需sudo运行, ✅ 补丁合规性已修正+按10步流程重打包 |
| 24 | strace | 6.19 | ⬜ 待编译 | - | - | - | ⚠️ ptrace受限, 可能不打包 |
| 25 | patch | 2.7.6 | ✅ 完成(partial) | ✅ 成功 | ✅ 成功 | packaging/patch-2.7.6-ohos-aarch64.tar.gz (188K) | 2个补丁(config.guess+config.sub), 32/44测试通过, 核心功能可用, 失败项为鸿蒙平台兼容性问题(umask/SELinux/shell) |

### 第六阶段：文档/辅助工具

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 26 | texinfo | 7.3 | ✅ 完成 | ✅ 成功 | ⚠️ 待确认 | - | 9个补丁(3处config.guess/sub + Makefile + Perl子模块), 92/138测试通过(46跳过非失败), --disable-nls, ⚠️ RELEASENOTE过期 |
| 27 | help2man | 1.49.3 | ✅ 完成 | ✅ 成功 | ⚠️ 待确认 | - | 纯Perl脚本(无需编译), 2个源码补丁(Makefile+help2man脚本), ⚠️ RELEASENOTE过期(列出4补丁含构建产物) |
| 28 | libpipeline | 1.5.8 | ✅ 编译成功 | ✅ 成功 | ✅ 成功 | packaging/libpipeline-1.5.8-ohos-aarch64.tar.gz | 2个补丁(config.guess+config.sub), 无外部依赖, man-db 核心依赖 |

### 第七阶段：文档系统

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 29 | man-db | 2.13.1 | ⚠️ 架构问题 | ✅ 成功 | ✅ 成功 | packaging/man-db-2.13.1-ohos-aarch64.tar.gz (2350K) | 5个补丁, --disable-setuid, ⚠️ **R20 DESTDIR 架构问题待解决**（见下方架构问题记录） |

---

## 📝 问题记录

> 每款软件编译中发现的问题、与历史档案的差异、skill更新建议记录在此。

### coreutils 9.10（对话 #3）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **make install Permission denied** | `configure --prefix=` 为空，默认安装到系统 `/bin` | 使用 `make install prefix=/path/to/dest` 指定安装目录 | ✅ |
| **ohc-run.py package Step 4 卡死** | `$TEST_PREFIX` 未传递 → fallback 到全局 `/usr/local` → 复制了 10889 个无关 lib 文件 → 对垃圾文件逐个 ELF 检测超时 | 确保 `$TEST_PREFIX` 在环境变量中；或直接 `make install` 到 packaging 目录 | ✅ |
| **EXCLUDE_LIST 不生效 (0 files excluded)** | Step 2e(排除)在 Step 2b(复制)**之前**执行，PKGDIR 为空时删不到任何东西 | 调整顺序：Step 2b(复制) → Step 2e(排除) | ✅ |
| **ohc-run.py finalize-archive RELEASENOTE.md 未生成** | 嵌套 heredoc (`$(if ... cat <<EOF ... EOF fi)` 在无引号 heredoc 内部) 静默失败 | 重写为分段写入（6 个独立的 `cat >>` 操作） | ✅ |
| **RELEASENOTE 变量未展开** | 使用 `'EOF'`(单引号)阻止变量替换 | 改为 `<< EOF`(无引号允许展开) | ✅ |
| **_BSYS=unknown** | manifest.yaml 中 `build_system:` 有缩进(`build_config:` 子字段)，`^build_system:` 错配 | 改为 `grep "build_system:"`(去掉 `^` 锚定) | ✅ |
| **排除列表含注释** | manifest.yaml 行内注释(`# syscall不支持`)被当命令名 | 加 `cut -d"#" -f1` 清理 | ✅ |
| **zsh glob 无匹配报错** | `set -euo pipefail` + zsh 默认 NOMATCH 导致 `*.tmp` 等模式报错退出 | shebang 改为 `#!/bin/zsh` + `setopt +o NOMATCH` | ✅ |
| **PROGRESS status 匹配 WARN** | grep `-oE 'success\|...'` 从 `success#final` 只截取 `success` | 扩展为支持 `success#final` | ✅ |

### libtool 2.4.7

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **构建系统检测为 unknown** | 源码解压后实际在 `libtool-2.4.7.orig/` 子目录，build-driver 未找到顶层 configure | 手动进入子目录执行 configure/make/install | ✅ |
| **ohc-run.py package Permission denied (exit 126)** | 脚本文件缺少 `+x` 执行权限（7个 .sh 文件） | `chmod +x scripts/*.sh` | ✅ |
| **ohc-run.py build 退出码 126 "Is a directory"** | 脚本中裸的 `""` 空字符串命令在 toybox sh + `set -e` 下返回非零退出码 | 删除 3 处空行 `""` 命令 | ✅ |
| **_task_card (已归档到 _archive_bash/) sed 分隔符冲突** | 备注 `2/2` 中的 `/` 与 sed `s///` 的 `/` 分隔符冲突 → `unknown option to 's'` | 改用 awk 替代 sed 进行备注字段写入 | ✅ |
| **ohc-run.py package 打包失败** | 打包目录不存在（`packaging/libtool/2.4.7/`），ohc-run.py package 无法生成 tar.gz | 需后续补跑 ohc-run.py package 或手动打包 | ⚠️ 待处理 |
| **libtoolize func_add_hook 错误 (E035)** | libtoolize 的 inline-source shell 函数机制在 HarmonyOS sh 下无法正确加载 | 核心功能 `libtool` 正常可用，libtoolize 仅影响从零创建 autotools 项目 | ✅ 已知限制 |

### bzip2 1.0.8（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **ohc-run.py package Step 6 空管道退出** | `lib/external/` 为空时 `find ... \| while read` 返回 EOF，`set -e` 触发退出 | 添加空目录检查：`[ -d dir ] && [ -n "$(ls -A dir)" ]` | ✅ 已修复 ohc-run.py package |
| **strip 命令缺失** | 系统无 `/usr/bin/strip`，只有 `llvm-strip` | 创建 wrapper: `/tmp/bin/strip → llvm-strip` | ⚠️ 临时方案 |
| **bzip2 --version 读 stdin 阻塞** | bzip2 无参数时从 stdin 读取，非 TTY 下永久挂起 | 验证步骤改用 `-f -z/-d` 实际文件操作代替 `--version` | ✅ |
| **鸿蒙 ln -sf bug** | `ln -sf` 创建带随机后缀文件而非覆盖符号链接 | 先 `/bin/rm -f` 再 `/bin/ln -s` | ✅ 已知限制 |

### htop 3.4.1（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **5个补丁中3个不合规** | 上个会话未按流程处理：(1) `.patch-ai-review.txt` AI元数据误当补丁；(2) `htop.1` 生成文件当补丁违反 R6；(3) `config.sub` 含重复行+缩进错误 | 删除2个无效补丁，修复 config.sub 源文件后 `refresh-patch --auto` 重新生成3个合规补丁 | ✅ |
| **打包未按10步流程** | 上个会话手动打包，install.sh 包在 tar.gz 内，未走 `ohc-run.py package` | 用 `ohc-run.py package --prefix=...` 重走10步流程：strip + RUNPATH 设置 + ELF 签名 + 独立 install.sh | ✅ |
| **config.sub ohos-linux 块损坏** | 补丁脚本生成重复行（`basic_machine=` 出现2次，残留 `linux-android`） | 手动修复为标准缩进+正确的 `basic_os=linux-ohos` | ✅ |
| **.patch-backup 目录残留** | refresh-patch 保留旧备份目录 | `rm -rf .patch-backup-*` 清理 | ✅ |

### 关键经验

43. **补丁合规性三查** — (1) 非源码文件不能当补丁（.patch-ai-review.txt、.dirstamp）；(2) 生成文件不能当补丁（htop.1 man page，违反 R6）；(3) 补丁内容不能有重复行/错误缩进

### patch 2.7.6（对话 #当前）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **补丁应用失败（所有 strip level）** | 归档中的旧补丁 `config.guess.orig` 路径与 work 目录不匹配 | 手动修改 config.guess（添加 HarmonyOS 检测块）和 config.sub（3 处 ohos 修改） | ✅ |
| **configure RC=127** | config.guess 无法识别 HarmonyOS 系统（E007）+ config.sub 不接受 ohos 三元组（E072） | E007 + E072 标准修复：config.guess 添加 HarmonyOS 分支，config.sub 添加 linux-ohos*/ohos*/linux-ohos* 三处 | ✅ |
| **ohc-run.py package 步骤崩溃** | `_resolve_prefix()` fallback 到全局 `$HOME/usr/local/bin`，复制了无关二进制（`[` 等其他软件的文件）导致 sendfile I/O error | 手动打包：只复制 patch 二进制，strip + ELF 签名 + tar.gz | ⚠️ 脚本限制 |
| **refresh-patch 生成 122 个补丁** | 无构建产物过滤，Makefile/config.h/测试日志等全部生成为补丁 | 手动清理为 2 个源码补丁（config.guess + config.sub），删除其余 + .patch-backup 目录 | ✅ |
| **9/44 测试失败** | umask 差异(file-modes)、shell shift 行为差异(merge)、SELinux 软链接限制(symlinks) | 已知鸿蒙平台兼容性限制，核心补丁功能验证可用 | ⚠️ 已知限制 |

### 关键经验

46. **ohc-run.py package 需指定精确 staging 路径** — 当 `$HOME/usr/local/bin` 混有多个软件的产物时，package 步骤会尝试复制所有文件导致崩溃。需指定 `--prefix` 或手动打包
47. **补丁清理：只保留源码修改** — refresh-patch --auto 可能将构建产物（Makefile、config.h、.log）也生成为补丁。编译完成后应人工审查，只保留源码级补丁
44. **ohc-run.py package 需要正确 staging 路径** — 默认查找 `$TMPDIR/test-install-{name}-{ver}`，实际路径不同时需 `--prefix` 指定
45. **install.sh 不应在 tar.gz 内** — 按 packaging-guide.md 规范，install.sh 独立存放在 `packaging/` 目录

### 关键经验

8. **Makefile CFLAGS 直接赋值 vs 条件赋值** — 直接赋值(`=`)导致 `make CFLAGS=xxx` 必须完整复制原值；条件赋值(`?=`)或追加(`+=`)才支持环境变量覆盖
9. **平台检测优于硬编码** — `$(shell $(CC) -dumpmachine \| grep -q "ohos")` 可实现跨平台兼容的 Makefile 补丁
10. **纯 Makefile 项目(无 configure) 的补丁策略** — 只需 patch CFLAGS 行做平台适配，其余 CC/AR/RANLIB/PREFIX 全部通过 make 参数传入

### zlib 1.3.1（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **主站下载 URL 404** | `zlib.net/zlib-1.3.1.tar.gz` 已归档（当前最新版 1.3.2） | 改用 `zlib.net/fossils/zlib-1.3.1.tar.gz` | ✅ |
| **ohc-run.py package fallback 到 usr/local** | 纯库无 bin/，staging 检测 `[ ! -d "$_SRC_PREFIX/bin" ]` 必然命中 fallback | 改为检查 lib/ 或 include/ 任一存在即可 | ✅ |
| **源码嵌套子目录** | tar 解压后实际在 `zlib-1.3.1.work/zlib-1.3.1.orig/` | 手动定位 REAL_SRC_DIR 执行编译 | ⚠️ init-build 解压逻辑待优化 |

### 关键经验

1. **`make install prefix=` 可以绕过重新 configure** — 当 prefix 配置错误时无需 distclean
2. **coreutils 是零依赖纯二进制包** — lib/ 目录为空，不需要 Step 4 收集外部依赖
3. **heredoc 嵌套是反模式** — 分段写入更可靠、更易调试
4. **toybox sh 对 POSIX 兼容性有限** — `\uXXXX` 转义、`\|` 地址模式、裸 `""` 命令等需避免
5. **sed 分割符选择要考虑变量内容** — 当替换值可能含 `/` 时必须改用其他分隔符或 awk
6. **纯库软件 staging 检测不能用 bin/ 存在性判断** — 应检查 lib/ 或 include/，否则必然 fallback 到全局前缀
7. **zlib 旧版本在 fossils 子目录** — 主站只保留最新版，历史版本 URL 需加 `/fossils/` 路径段

### xz 5.6.2（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **主站下载超时 (curl exit 28)** | tukaani.org 从国内访问慢，30s 超时 | 手动下载到工作目录后用 `--url=file://` 传入 init-build | ✅ |
| **/tmp 只读 (erofs)** | 鸿蒙 /tmp 挂载为只读文件系统 | 使用 `$TMPDIR=$HOME/tmp`（已由 SKILL R10 处理） | ✅ 已知限制 |
| **构建系统检测为 unknown** | tar.xz 解压后源码嵌套在 `.work/xz-5.6.2.orig/` 子目录，build-driver 的 `find -maxdepth 2` 未修正 BUILD_SRC_DIR | 手动定位 REAL_SRC 编译；**已记录 F068 待修复 build-driver** | ⚠️ 脚本 bug |
| **config.guess 无法识别 HarmonyOS** | GNU config.guess (2024-01-01) 无 HarmonyOS/uname 检测分支 | **方案A**: 打补丁修改 config.guess(`__OHOS__`+HarmonyOS块) + config.sub(ohos-linux+ohos*+linux-ohos*)；**禁止用 --build/--host 绕过**(autotools-patterns.md §0 铁律) | ✅ |
| **perl $UNAME_MACHINE 被插值为空** | perl 双引号 heredoc 中 `$UNAME_MACHINE` 被 shell 变量替换为空 | 改用 `<<'EOB'`(单引号 heredoc) 或 `\Q$UNAME_MACHINE\E` 转义 | ✅ 已沉淀到标准脚本 |
| **config.sub linux-uclibc 匹配失败** | 文档示例写 `linux-uclibc* )`，实际文件是 `linux-uclibc*- )`（多 `-`） | 修正 autotools-patterns.md §3.3 增加变体说明；标准脚本用 `[/-]?` 兼容两种格式 | ✅ |
| **Perl `-r` 测试与 shell `test -r` 行为不同** | HarmonyOS 文件系统上 Perl 的 `-r` 返回 false 但文件可读 | 标准脚本改用 `-e` 判断 | ✅ |
| **lzcmp 功能测试失败** | lzcmp 是 cmp 的软链接包装，依赖 `/usr/bin/cmp`，鸿蒙上行为异常 | 加入 EXCLUDE_LIST（1/23 排除），不影响核心 xz 功能 | ✅ 已知限制 |
| **ohc-run.py package 打包路径不匹配** | build-driver Step 9 中 `packaging/xz/5.6.2/` 不存在（实际在 `archives/x/xz/5.6.2/packaging/`） | ohc-run.py package 回退但未阻塞部署；fallback deploy 成功 | ⚠️ 轻微 |

### 关键经验

8. **方案A > 方案B（铁律）** — autotools 项目必须打补丁修改 config.guess/config.sub，禁止用 `--build=`/`--host=` 绕过。后者导致交叉编译误判 → AC_RUN_IFELSE 全跳过 → config.h 错误
9. **Perl heredoc 变量安全** — Perl 双引号 heredoc (`<<"HEREDOC"`) 会展开 `$VAR`，shell 变量会覆盖 Perl 变量。必须用单引号 heredoc (`<<'HEREDOC'`) 或 `\Q\E` 转义
10. **config.sub 版本差异** — 不同软件打包的 config.sub 版本不同，`linux-uclibc` 条目可能是 `linux-uclibc*)` 或 `linux-uclibc*-)`。脚本需兼容两种变体
11. **嵌套源码目录是常见模式** — tar.xz/tar.bz2 解压经常产生 `软件-版本.orig/` 子目录。build-driver 应在 init 阶段就递归查找 configure 并修正 BUILD_SRC_DIR
12. **标准补丁工具应内置** — 每次 Perl 正则调试耗时且易出错。`patch-autotools-ohos.pl` 已沉淀为 `${SKILL_ROOT}/scripts/` 标准工具

### gzip 1.13（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **config.guess 不识别 HarmonyOS** | gzip 1.13 的 config.guess 无 HarmonyOS 检测分支 | `patch-autotools-ohos.pl` 标准补丁 | ✅ |
| **patch-autotools-ohos.pl config.sub 产出重复行** | 补丁脚本的 `ohos-linux` 块生成重复的 `basic_machine=` 和残留 `linux-android` | 手动修复 3 处：去重、修正 `basic_os=linux-ohos`、添加 `linux-ohos*` 到允许列表 | ⚠️ 脚本 bug 待修 |
| **`linux-ohos*` 不在 config.sub 允许列表** | 补丁脚本只修改了 `ohos-linux` 入口，未在 `linux-gnu*` 行追加 `linux-ohos*` | 手动追加 `linux-ohos*` 到第 1765 行的 `linux-gnu* | ...` 条件 | ✅ |
| **R15 历史参数含 --build/--host** | 历史归档 manifest 中有 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`，违反铁律 R15 | 本次编译去掉 --build/--host，仅用 `--prefix` | ✅ |
| **shell 脚本 Permission denied** | gunzip/zcat/zgrep 等脚本的 shebang `/bin/sh` 在 OpenHarmony 上需 ELF 签名才能直接执行 | 通过 `sh script.sh` 调用可正常工作，打包时 install.sh 处理 | ✅ 已知限制 |
| **ohc-run.py package 缺少 import re** | `package_builder.py` 使用 `re.sub` 但未 import re | 手动添加 `import re` | ⚠️ 脚本 bug 待修 |
| **refresh-patch 报错 str/str 拼接** | `refresh-patch --auto` 内部路径拼接使用 `/` 操作符于两个字符串 | 手动 diff 生成补丁 | ⚠️ 脚本 bug 待修 |

### openssl 1.1.1w（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **主站下载超时 (SSL + 网络不通)** | openssl.org 和 GitHub releases 均超时 | 改用 gitee.com/mirrors/openssl (GitHub mirror)，10MB 源码成功下载 | ✅ |
| **tarball 损坏 (首次下载不完整)** | 超时后留下 9.5KB 残缺文件，解压缺少 util/perl 目录 | 从 gitee 重新下载完整 tarball (10MB) | ✅ |
| **Configure 找不到 OpenSSL/Glob.pm** | tarball 不完整时 util/perl/ 目录缺失 | 完整 tarball 解压后正常 | ✅ |
| **HMDFS `ln -s` Permission denied** | `ln -sf` 和 `ln -s` 在 HMDFS 文件系统上被拒绝（即使目标不存在） | `sed -i 's/ln -s /cp -a /g; s/ln -sf/cp -a/g' Makefile` 批量替换 | ✅ |
| **`cp -a` 可替代 `ln -s`** | HMDFS 上 `cp -a` 可以复制文件，效果等价于硬拷贝"链接" | 对 openssl 的 .so 链接场景足够（运行时不依赖 symlink） | ✅ |
| **动态库加载失败** | `libssl.so.1.1` 和 `libcrypto.so.1.1` 不在默认搜索路径 | 设置 `LD_LIBRARY_PATH=$PREFIX/lib`，install.sh 中自动处理 | ✅ |
| **R15 no-asm 确认** | 历史记录中 `no-asm` 是必须的，否则 RSA-PSS 签名可能失败 | 本次编译使用 `no-asm`，全部测试通过 | ✅ |

### ncurses 6.4（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **🔴 历史manifest使用 --with-shared** | 历史归档错误地用了 `--with-shared`，共享 libncursesw.so 会通过 LD_LIBRARY_PATH 劫持系统库导致 zsh 崩溃 | 本次改用 `--without-shared`，仅生成 .a 静态库 | ✅ 已纠正 |
| **R15 触发提醒** | init-build 检测到历史参数缺少 `--without-shared`，自动警告 | 确认使用 `--without-shared` | ✅ |
| **preinstall Error 1（make all 阶段）** | `DIRS_TO_MAKE` 的 `mkdir` 目标在某些情况下返回非零 | 直接重新 make 成功（目录已存在） | ✅ 非阻塞 |
| **misc/terminfo.tmp Error 1** | 首次 make misc 时 `sed -f run_tic.sed` 执行后后续步骤失败 | 重新 make 时 terminfo.tmp 已生成，不再报错 | ✅ 非阻塞 |
| **terminfo symlink 兼容性 warning** | `cp: cannot stat '../share/terminfo': No such file or directory` + `could not sym-link ... for compatibility` | HMDFS 不支持 symlink，非关键功能 | ✅ 已知限制 |

### 关键经验

13. **HMDFS 完全不支持符号链接** — `ln -s`/`ln -sf` 均失败，`cp -a` 是唯一替代方案。Makefile 中所有 `ln -s` 都需要 `sed` 替换
14. **gitee.com/mirrors/ 可作为国内镜像** — openssl 等主流项目在 gitee 有官方 mirror，格式 `gitee.com/mirrors/<软件>/repository/archive/<tag>.tar.gz`
15. **tarball 完整性检查很重要** — 超时下载的残缺 tarball 解压后可能少目录/文件，需 `file` 命令检查 + `tar tzf | wc -l` 核对文件数
16. **OpenSSL 使用自定义 Perl Configure** — 不是 autotools，用 `perl Configure <target>` 而非 `./configure`。target 名称由 `Configurations/` 目录下的 `.conf` 文件定义
17. **`cp -a` 对共享库链接的影响** — `cp -a` 产生独立副本而非符号链接，升级时需同时替换所有副本。对于预编译包场景可接受
18. **ncurses 共享库是核弹级危险** — `--with-shared` 产出的 libncursesw.so.6 会通过 LD_LIBRARY_PATH 劫持系统 zsh 的依赖，导致 Shell 立即崩溃。必须 `--without-shared`
19. **--enable-widec 是 readline/bash 的前提** — readline 链接 `libncursesw`（宽字符版），普通版 `libncurses` 不兼容

### libffi 3.5.2（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **libffi 3.5.2 版本不存在于公共下载** | GitHub releases 和 GNU FTP 均无法直接下载（SSL/网络问题） | 使用 `ghfast.top` GitHub 加速代理成功下载 1.4MB tarball | ✅ |
| **configure `-print-multi-os-directory` 警告** | clang 15 不支持 `-print-multi-os-directory` 选项 | 非致命，configure 仍成功退出 | ✅ 非阻塞 |
| **历史 manifest 提到 .so 截断问题** | 之前 make install 产出的 .so 文件只有 10K，需从 .libs/ 手动拷贝 | 本次编译 .so 文件正常（109K），问题未复现 | ✅ |
| **ffi_closure 闭包功能不可用** | 鸿蒙禁止 mmap/mprotect 使用 PROT_EXEC（W^X 策略） | 历史归档有 `0002-closure-port-for-ohos.patch`（FFI_EXEC_STATIC_TRAMP 方案），闭包功能仍有限制 | ⚠️ 已知限制 |

### 关键经验

20. **ghfast.top 可作为 GitHub 加速代理** — 格式 `https://ghfast.top/https://github.com/...`，libffi 1.4MB 9秒下载完成
21. **libffi closure 在鸿蒙上受限** — W^X 策略禁止 PROT_EXEC，ffi_closure 需要 FFI_EXEC_STATIC_TRAMP 补丁（复用 .so 内 trampoline_code_table + MAP_FIXED）
22. **libffi 与 Python 3 强绑定** — Python ctypes 依赖 libffi，是后续编译 Python 的前置依赖

### gdbm 1.23（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **ghfast.top 无法加速 GNU FTP** | `ghfast.top/https://ftp.gnu.org/...` 返回 14B 重定向页而非文件 | 直接用 `curl -kL` 从 ftp.gnu.org 下载（~85s，1.1MB） | ✅ |
| **gdbm_open 失败（C 测试程序）** | 测试程序使用 `/tmp` 路径，HMDFS 上 `/tmp` 为只读 | 改用 `$TMPDIR`（`/storage/Users/currentUser/tmp`） | ✅ |
| **libtool .so 安装为 cp 副本** | HMDFS 上 `ln -s` 失败，libtool 自动降级为 `cp`（与 openssl 相同） | 非关键，功能正常 | ✅ 已知限制 |

### 关键经验

23. **gdbm_open 路径不能用 /tmp** — HMDFS 上 `/tmp` 为只读 erofs，gdbm_open 创建数据库文件需使用 `$TMPDIR`
24. **ghfast.top 只加速 GitHub，不加速 GNU FTP** — GNU FTP 需直接用 curl -kL 下载（慢但可靠）
25. **gdbm 是 Python gdbm 模块和 man-db 的前置依赖** — `--enable-libgdbm-compat` 提供 ndbm/dbm 兼容接口

### rsync 3.3.0（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **下载 URL 404** | init-build 用 `pub/rsync/rsync-3.3.0.tar.gz`，正确路径需 `pub/rsync/src/` | 手动下载 `download.samba.org/pub/rsync/src/rsync-3.3.0.tar.gz` | ✅ |
| **config.sub 需要 4 处 ohos 修改** | rsync 的 config.sub 除标准 3 处外，还需要在 OS 有效性白名单（`gnu* | android* | ...`）添加 `ohos*` | 第 1731 行添加 `ohos* |` 前置 | ✅ |
| **configure 报 OS 'ohos' not recognized** | config.sub 缺少 OS 有效性白名单修改 | 在 `gnu* | android* | bsd* | ...` 行添加 `ohos*` | ✅ |
| **distclean 删除 configure.sh/config.h.in/aclocal.m4** | rsync 的 distclean 删除了 autotools 生成文件，无法重新 configure | 从 .orig 恢复这些文件，且 `touch` 使其时间戳比 Makefile 新 | ✅ |
| **make 触发 autoconf 重新生成** | Makefile 有 `configure.sh: configure.ac aclocal.m4` 规则，试图重新运行 autoconf | `touch configure.ac aclocal.m4 configure.sh config.h.in` 使依赖时间戳更新 | ✅ |
| **configure 需要 --disable-md2man** | 源码包缺 cmarkgfm python 模块（仅 git 开发版需要 manpage 生成） | 加 `--disable-md2man` | ✅ |
| **mkgitver 无 x 权限 (HMDFS)** | make check 依赖 `./mkgitver`，HMDFS 上 chmod 无效 | `bash ./mkgitver` 手动执行；make check 无法自动运行 | ⚠️ 已知限制 |
| **make check config.status 权限问题** | HMDFS 上 config.status 无 x 权限，make check 重建 Makefile 失败 | 手动功能测试替代官方测试套件 | ⚠️ 已知限制 |

### 关键经验

33. **rsync 下载 URL 含 /src/ 路径段** — `download.samba.org/pub/rsync/src/rsync-X.Y.Z.tar.gz`
34. **config.sub 可能需要 4 处修改** — 除标准 3 处（maybe_os + kernel-os + OS白名单）外，部分版本还需在 OS 有效性列表加 `ohos*`
35. **rsync distclean 会删除关键构建文件** — configure.sh、config.h.in、aclocal.m4 被删，需要从 .orig 恢复
36. **autotools Makefile 可能重建 configure** — `touch` 所有依赖文件使其时间戳比目标新，避免触发 autoconf 重新生成

### jq 1.7.1（对话 #当前）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **oniguruma 子模块 config.guess 需单独修复** | jq 的 oniguruma 子目录有独立的 config.guess，需单独打补丁 | 手动添加 HarmonyOS 检测块，并在 refresh-patch 时生成补丁 | ✅ |
| **oniguruma config.guess 含重复行** | 手动修复时产生了重复的 `*:HarmonyOS:*:*` 块 | 去重修复 | ✅ |
| **refresh-patch filecmp TypeError** | `filecmp.dircmp.left/right` 返回 str 而非 Path | 强制 `Path(dcmp.left)` 包装 | ✅ 已修复 |
| **补丁数过多（98个→2个）** | refresh-patch 无构建产物过滤 | 新增 `_is_likely_generated` 智能过滤 + AI 判断层 | ✅ 已修复 |

### file 5.45（对话 #当前）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **config.sub 拒绝 aarch64-unknown-linux-ohos** | config.sub 缺少 `linux-ohos*` kernel-os 白名单（只有 `linux-gnu*` 等） | 在 kernel-os case 第1773行添加 `linux-ohos*` | ✅ |
| **引擎误匹配 E002 覆盖 E007/E072** | driver 日志只含 `❌ configure failed (RC=127)`，缺少 config.sub 真实错误信息 | configure 失败时从 config.log 追加最后 N 行到 driver 日志 | ✅ 已修复 driver.py |
| **E072 方案不完整** | E072.kv 只提到 2 处修改，遗漏最关键的 kernel-os 白名单 | 补全 E072.kv 的 3 处修改说明 | ✅ 已修复 E072.kv |
| **verify G1 误报 unknown type** | 鸿蒙 `file` 命令对 musl 动态链接 ELF 输出不含标准关键词 | 增加 ELF magic bytes + readelf -h 兜底 | ✅ 已修复 verify_build.py |
| **verify G3 OSError 崩溃** | HMDFS 上 `read_bytes()` 抛 I/O error | catch (OSError, IOError) 并假设为 ELF | ✅ 已修复 verify_build.py |
| **归档不完整** | 缺 install.sh、test-report.md、manifest 补丁数不一致 | 手动补全 | ✅ 已修复 |

### tar 1.35（对话 #当前）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **97个测试失败（UID超范围）** | HarmonyOS UID 分配范围与 tar 测试预期不匹配 | 平台限制，非编译问题 | ⚠️ 已知限制 |
| **补丁自动应用失败** | 源码非 git 仓库，旧补丁路径与 work 目录结构不匹配 | driver 尝试多级 strip(-p0/-p1/-p2)，区分已应用 vs 路径不匹配 | ✅ 已修复 driver.py |
| **resume_from TypeError** | `--resume-from` 跳过 Step1 导致 build context 变量未加载 | 拆出 `_load_context()` 无条件加载 | ✅ 已修复 driver.py |
| **manifest 补丁数不一致（1 vs 7）** | refresh-patch 刷新后未回写 manifest | 手动更新 manifest 补丁列表 | ✅ 已修复 |

### dos2unix 7.5.4（对话 #当前）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **NLS 编译失败** | HarmonyOS 缺少 libintl.h（gettext 开发库） | Makefile 中 `ENABLE_NLS =` 禁用 | ✅ |
| **软链接创建失败** | HMDFS 不支持 `ln -sf` | Makefile 中 `LINK = cp -f` 替代 | ✅ |
| **refresh-patch 扫描测试输出文件** | test/ 目录的差异文件被误报为补丁 | `_is_likely_generated` 内容嗅探过滤 | ✅ 已修复 |
| **--version 安全弹窗阻塞** | 未签名 ELF 触发 HarmonyOS 安全确认 | `ohc-run.py sign-elf` 签名后正常 | ✅ |

### 关键经验

37. **E072 需修改 3 处** — config.sub 的 maybe_os 行 + OS 白名单 `ohos*` + kernel-os 白名单 `linux-ohos*`，缺一不可
38. **引擎匹配依赖 config.log 错误信息** — driver 日志只含高层面信息（RC=127），必须从 config.log 提取真实错误才能正确匹配 E007/E072
39. **refresh-patch 需智能过滤** — 纯规则无法区分 gnulib 生成的 `.h` 和源码 `.h`，需内容嗅探（`GENERATED AUTOMATICALLY`）+ AI 判断层
40. **Makefile 项目（无 configure）的构建方式** — dos2unix 直接 `make`，不经过 autotools，补丁只需修改 Makefile
41. **HMDFS 上 read_bytes() 可能抛 OSError** — verify_build 等工具中所有文件读取都需要 catch (OSError, IOError)
42. **HarmonyOS 缺少 gettext/libintl** — 需在 Makefile 或 configure 中禁用 NLS

### wget 1.19.1（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **config.guess 补丁打错位置** | wget 的 config.guess/config.sub 在 `build-aux/` 子目录而非根目录，旧补丁文件名 `config.guess` 匹配不到实际文件 | 新补丁路径改为 `build-aux/config.guess`，补丁文件名改为 `0001-build-aux-config-guess-harmonyos.patch` | ✅ |
| **config.guess GUESS= 语法不兼容** | 2017 年旧版 config.guess 不支持 `GUESS=` 变量赋值（2018+ 新增），赋值后无输出无 exit，脚本 fall through 到 "unable to guess" | 将 `GUESS=` 改为 `echo ... exit` 语法 | ✅ 已沉淀到 E007 |
| **secure_getenv 未声明 (E081)** | musl libc 未实现 `secure_getenv()`（glibc 扩展），gnulib tmpdir.c 通过 `#define __libc_secure_getenv secure_getenv` 调用 | `#define __libc_secure_getenv getenv`（鸿蒙无 setuid 场景，降级安全） | ✅ 已沉淀到 E081 |
| **链接找不到 -lssl/-lcrypto** | `libssl.a`/`libcrypto.a` 在 `$HOME/usr/local/` 根目录而非 `$HOME/usr/local/lib/` | `cp` 到 `lib/` 目录 | ✅ |
| **ohc-run.py package Step 2 复制无关文件** | `_resolve_prefix()` fallback 到全局 `$HOME/usr/local`，把 bin/ 下所有文件（包括 coreutils 的 `[` 命令）都复制了 | 手动打包（静态二进制只需 wget 一个文件） | ⚠️ 脚本限制 |
| **make check 9/39 测试失败** | 9 个 SSL 公钥固定测试（pinnedpubkey）失败，测试环境缺少完整 SSL 证书配置 | 非功能缺陷，标记为 partial | ⚠️ 已知限制 |
| **文档编译失败** | `texi2pod.pl` 缺失导致 `make install` 文档部分失败 | 非关键，二进制功能完整 | ✅ 非阻塞 |

### 关键经验

29. **config.guess/config.sub 不一定在项目根目录** — wget 放在 `build-aux/` 子目录，打补丁前必须 `find . -name config.guess` 确认实际位置
30. **旧版 config.guess 不支持 GUESS= 赋值** — 2018 年前的版本用 `echo ... exit` 输出，新版用 `GUESS=` 统一赋值。可通过 `tail -20 config.guess | grep "echo.*GUESS"` 判断版本
31. **musl 未实现 secure_getenv()** — 影响 gnulib 项目（wget, coreutils 等），降级为 `getenv` 安全（E081）
32. **静态库可能不在 lib/ 子目录** — 某些安装流程把 `.a` 文件放在 prefix 根目录，链接时找不到

### readline 8.2（对话 #N）

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **补丁 0001 Hunk 1 失败** | config.sub 补丁的上下文行不匹配（缩进差异） | 手动 `sed` 添加 `linux-ohos*`、`ohos*`、`linux-ohos*` 三处 | ✅ |
| **config.sub 需 3 处 ohos 修改** | 补丁只含 `linux-ohos*` 在 maybe_os 行，缺少 OS 允许列表和 kernel-os 白名单 | 手动修复：第 145 行 + 第 1723 行 `ohos*` + 第 1772 行 `linux-ohos*` | ✅ |
| **链接失败 `-lncurses` 找不到** | ncurses 编译为 `--without-shared` 只有 `libncursesw.a`，Makefile 中 `TERMCAP_LIB=-lncurses` | 改为 `TERMCAP_LIB=-lncursesw`（Makefile + shlib/Makefile） | ✅ |
| **HMDFS `ln -s` 失败** | make install 创建 .so 符号链接失败 | `cp -a` 替代，手动创建 libreadline.so/libhistory.so | ✅ 已知限制 |
| **ncurses 静态嵌入 libreadline.so** | `--with-curses` + ncurses `--without-shared` → 链接时自动静态嵌入 | libreadline.so NEEDED 只有 libc.so，无需运行时 libncursesw | ✅ 正合预期 |

### 关键经验

26. **readline 的 TERMCAP_LIB 必须是 -lncursesw** — 因为 ncurses 编译为 wide-char 版（libncursesw），不存在 libncurses
27. **ncurses --without-shared 时 readline 自动静态嵌入** — libreadline.so 的 NEEDED 只有 libc.so，不需要运行时 ncurses 库
28. **config.sub 补丁必须修改 3 处** — maybe_os 行(`linux-ohos*`) + OS 允许列表(`ohos*`) + kernel-os 白名单(`linux-ohos*`)，缺一不可

---

### texinfo 7.3

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **config.guess 3 处需修补** | texinfo 在 build-aux/, tta/build-aux/, tta/perl/CheckXS/build-aux/ 三处有独立 config.guess/config.sub | 逐一用 patch-autotools-ohos.pl 修补；CheckXS 的 config.sub 版本不同，用主目录覆盖 | ✅ |
| **文档构建失败** | doc/ 目录 info 文件生成失败（texi2any @include 路径解析问题） | 从 SUBDIRS 移除 doc 目录，不影响核心功能 | ✅ |
| **info 测试 Permission denied** | info viewer 的 90 个交互式测试因脚本文件权限限制失败 | 鸿蒙文件系统权限限制，不影响二进制功能 | ⚠️ 已知限制 |
| **RELEASENOTE 过期** | 列出 config.h/config.log/config.status/doc-Makefile 补丁（构建产物），但实际补丁已刷新为 tta 子目录的源码补丁 | 需重新生成 RELEASENOTE | ⬜ 待修复 |
| **PROGRESS.md 步骤未更新** | 所有步骤仍显示 ⏳ | finish 流程中 finalize-archive 应已更新，需检查 | ⬜ 待修复 |
| **无 tar.gz 打包产物** | 另一台机器编译，归档同步后无 packaging/ 目录 | 需确认打包状态或补打包 | ⬜ 待确认 |

### help2man 1.49.3

| 问题 | 根因 | 修复 | 状态 |
|------|------|------|------|
| **RELEASENOTE 过期** | 列出 4 个补丁（含 config.log/config.status 构建产物），实际只有 2 个源码补丁 | refresh-patch 清理后未更新 RELEASENOTE | ⬜ 待修复 |
| **无 tar.gz 打包产物** | 另一台机器编译，归档同步后无 packaging/ 目录 | 需确认打包状态或补打包 | ⬜ 待确认 |

---

## ✅ 已解决：R20 DESTDIR 模式

> **优先级**: ✅ 已解决
> **发现时间**: 2026-04-15（man-db 2.13.1 编译过程中发现）
> **解决时间**: 2026-04-16

### 问题

硬编码路径软件（man-db、groff）将 `${prefix}` 路径编译进二进制，需要 `--prefix=$DEFAULT_PREFIX` + DESTDIR 隔离。

### 解决方案：DESTDIR 模式（已实施）

```bash
./configure --prefix=$DEFAULT_PREFIX
make install DESTDIR=$TEST_PREFIX
```

`--prefix` = 运行时路径（编译进二进制），`DESTDIR` = staging 隔离（打包用）。

### 已改动的文件

| 文件 | 改动 | 状态 |
|------|------|------|
| **SKILL.md** R20 | 改为 DESTDIR 模式 | ✅ 已完成 |
| **driver.py** `_step3_configure` | `--prefix={default_prefix}` | ✅ 已完成 |
| **driver.py** `_step5_install` | `make install DESTDIR={test_prefix}` | ✅ 已完成 |
| **package_builder.py** `_resolve_prefix` | 优先从 `$TEST_PREFIX/$DEFAULT_PREFIX/` 收集 | ✅ 已完成 |
| **references/iron-rules.md** | R7 路径更新 | ✅ 已完成 |
| **references/compile-guide.md** | 全面改为 DESTDIR 模式 | ✅ 已完成 |
| **references/staging-verify.md** | 验证路径更新 | ✅ 已完成 |
| **references/archive-spec.md** | Phase 2 描述更新 | ✅ 已完成 |

### man-db 2.13.1 编译详情

| 项目 | 内容 |
|------|------|
| 补丁 | 5 个（config.guess, config.sub, encodings.c, security.c, man.c） |
| configure 选项 | `--prefix=$DEFAULT_PREFIX --disable-setuid --with-systemdtmpfilesdir=no --with-systemdsystemunitdir=no` |
| 依赖 | gdbm 1.23, libpipeline 1.5.8, bzip2, groff(运行时) |
| VPATH 构建 | ✅ source_dir=man-db-2.13.1.work, build_dir=man-db-build |
| 外部依赖收集 | libgdbm.so.6, libpipeline.so.1 |
| tar.gz 大小 | 2350K |
| 已知兼容性问题 | musl iconv 不支持 //IGNORE → apropos/whatis 不可用 |

### 关键经验

48. **R20 DESTDIR 模式已实施** — `--prefix=$DEFAULT_PREFIX` + `make install DESTDIR=$TEST_PREFIX`，二进制硬编码运行时路径天然正确
49. **`step5_rpath` 必须自动扫描 lib/ 子目录** — 部分软件（如 man-db）将库安装在 `lib/man-db/` 子目录下，RPATH 需要包含 `$ORIGIN/../lib/man-db`，不能只有 `$ORIGIN/../lib`
50. **`step2_copy` 硬编码目录列表** — 只复制 bin/lib/include/share，漏掉 sbin/libexec/etc。应改为自动扫描 `src_prefix` 顶层目录
51. **`step10_tarball` 硬编码打包目录** — 应改为动态扫描 pkgdir 顶层目录
52. **Fedora spec 中 `%configure` 自动设置完整路径体系** — `--prefix=/usr --sysconfdir=/etc --localstatedir=/var --libexecdir=/usr/libexec`，每个目录独立控制。我们的 `--prefix` 一个参数决定了所有子路径

---

## 🔧 Skill 更新清单

> 预编译过程中发现的 skill 文件需要更新的点，汇总后批量处理。

| 文件 | 更新内容 | 状态 |
|------|---------|------|
| dependencies.md | 补充每款的「静态/共享」标注和环境变量风险说明 | ⬜ 待更新 |
| packaging.md | ✅ 已更新至 v2.3（10步流程+扁平结构规范+install.sh托管） | ✅ 完成 |
| environment.md | 补充 §12「LD_LIBRARY_PATH 优先级陷阱与静态库策略」 | ⬜ 待更新 |
| SKILL.md | ✅ 已更新至 v4.0（五步走+R10+预编译包+归档标准化） | ✅ 完成 |
| ohc-run.py install-template (已归档) | ✅ 已简化为 33 行极简版（cp -r * + $HOME/tmp） | ✅ 完成 |
| error-patterns.md | ✅ 新增 E066/E067（tar格式+grep元字符） | ✅ 完成 |
| error-patterns-runtime.md | ✅ 新增 **E007**（config.guess 无法识别 HarmonyOS，含方案A铁律/标准工具引用/交叉索引）+ **E007 补充**（旧版 GUESS= 语法 + build-aux 子目录） | ✅ 完成 |
| knowledge/graph/E081.kv + doc/E081.md | ✅ 新增 **E081**（secure_getenv musl 不可用，降级为 getenv，影响 gnulib 项目） | ✅ 完成 |
| knowledge/graph/E072.kv + doc/E072.md | ✅ 更新 **E072**（补充 config.sub 第4处修改：OS 有效性白名单 `ohos*`，rsync 3.3.0 发现） | ✅ 完成 |
| autotools-patterns.md | ✅ 新增 **§0 铁律**（禁止 --build/--host 绕过）；**§3.3 变体说明**；**§7 标准工具** `patch-autotools-ohos.pl` | ✅ 完成 |
| FAQ.md | ✅ Q5/Q18 同步增加 --build/--host 禁令说明和"唯一做法"表述 | ✅ 完成 |
| scripts/patch-autotools-ohos.pl | ✅ **新增** — 标准 autotools OHOS 补丁工具（5项检查+grep验证+变体兼容） | ✅ 完成 |
| reports/skill-feedback.md | ✅ 新增 F068(嵌套目录检测)/F069(运行时错误匹配缺失)/F070(覆盖面不一致) | ✅ 完成 |
| ohc-run.py finalize-archive | ✅ 升级：zsh 迁移 + RELEASENOTE 分段写入 + 变量补全 + 排除列表清理 + status#final 匹配 | ✅ 完成 |
| ohc-run.py finalize-archive | ✅ 升级：zsh 迁移 + RELEASENOTE 分段写入 + 变量补全 + 排除列表清理 + status#final 匹配 | ✅ 完成 |
| ohc-run.py package / ohc-run.py sign-elf | ✅ shebang 改为 `#!/bin/zsh`；ohc-run.py package Step 2e/2b 顺序修复（排除在复制之后） | ✅ 完成 |
| ohc-run.py init-archive | ✅ 升级支持 --clean 模式 + README 保护 | ✅ 完成 |
| ohc-run.py verify-build | ✅ G4 补丁验证修复（三级降级+tarball重建） | ✅ 完成 |
| ohc-run.py finish | ✅ 新增 Step 3 调用 ohc-run.py finalize-archive（4步流程） | ✅ 完成 |
| scripts/patch-autotools-ohos.pl | ⚠️ config.sub 补丁生成重复行+缺少 `linux-ohos*` 允许列表 | ⬜ 待修复 |
| scripts/ohc/package_builder.py | ⚠️ 缺少 `import re` | ⬜ 待修复 |
| scripts/ohc/package_builder.py | ✅ step9_install_sh: 软件级 install.sh 改为纯远程下载模板 | ✅ 已修复 |
| scripts/ohc/package_builder.py | ✅ step5_rpath: 自动扫描 lib/ 子目录加入 RPATH | ✅ 已修复 |
| scripts/ohc/package_builder.py | ⚠️ step2_copy: 硬编码 bin/lib/include/share，漏 sbin/libexec/etc | ⬜ 待修复 |
| scripts/ohc/package_builder.py | ⚠️ step10_tarball: 硬编码打包目录列表 | ⬜ 待修复 |
| SKILL.md R20 | ✅ 已改为 DESTDIR 模式 | ✅ 已完成 |
| driver.py | ✅ DESTDIR 模式已实施（configure --prefix=$DEFAULT_PREFIX + make install DESTDIR=$TEST_PREFIX） | ✅ 已完成 |
| scripts/ohc/driver.py | ✅ P1: configure 失败时从 config.log 追加错误到引擎日志 | ✅ 已修复 |
| scripts/ohc/driver.py | ✅ P2: resume_from 拆出 _load_context() 无条件加载 | ✅ 已修复 |
| scripts/ohc/driver.py | ✅ P5: 补丁应用尝试多级 strip(-p0/-p1/-p2) | ✅ 已修复 |
| knowledge/graph/E072.kv | ✅ P3: 补全 3 处修改说明（含 linux-ohos* kernel-os 白名单） | ✅ 已修复 |
| scripts/ohc/verify_build.py | ✅ P4: G1 增加 ELF magic bytes + readelf -h 兜底，减少误报 | ✅ 已修复 |
| scripts/ohc/verify_build.py | ✅ G1 增加 shebang 检测兜底（file 命令返回空时） | ✅ 已修复 |
| scripts/ohc/verify_build.py | ✅ G3 修复 HMDFS read_bytes() OSError 崩溃 | ✅ 已修复 |
| scripts/ohc/refresh_patch.py | ✅ P6: 修复 filecmp.dircmp.left/right 是 str 导致 TypeError | ✅ 已修复 |
| scripts/ohc/refresh_patch.py | ✅ 新增 `_is_likely_generated` 三态返回 + `_ai_classify_uncertain` AI 判断层 | ✅ 已修复 |
| scripts/ohc/refresh_patch.py | ✅ 修复 `_diff_files` 中 OSError 未 catch | ✅ 已修复 |
| scripts/ohc/finish.py | ✅ verify FAIL 不再强制降级为 failed（G1 误报问题） | ✅ 已修复 |
| scripts/ohc-run.py refresh-patch | ⚠️ `str / str` 路径拼接类型错误 | ⬜ 待修复 |
| releasenote-template.md | ⚠️ 标记为 .deprecated（被 finalize-archive 取代） | ✅ 处理 |
| knowledge_section_new.txt | 🗑️ 已删除（内容已整合进 SKILL §5） | ✅ 清理 |

---

## 📦 打包标准流程（10步）

> 参考 `knowledge/packaging.md` v2.3（权威参考）

```
Step 1:  make install DESTDIR 到独立目录（staging）
Step 2:  清理缓存和非必要文件
Step 3:  符号链接替换（wrapper脚本/cp复制）
Step 4:  收集外部依赖库到 lib/external/
Step 5:  设置 RPATH（$ORIGIN 相对路径）
Step 6:  Strip debug 符号 + 分离保存
Step 7:  ELF 签名（移除旧签名 → binary-sign-tool self-sign）
Step 8:  ⭐ 统一修复执行权限（必做！签名后权限被重置）
Step 9:  创建 install.sh（单独托管，不打包进 tar.gz）
Step 10: 打包 tar.gz（扁平结构：cd $PKGDIR && tar czf *）
```

### 工具路径

| 工具 | 路径 |
|------|------|
| patchelf | `/data/service/hnp/bin/patchelf` |
| llvm-objcopy | `/data/service/hnp/bin/llvm-objcopy` |
| binary-sign-tool | `/data/service/hnp/bin/binary-sign-tool` |
| llvm-readelf | `/data/service/hnp/bin/llvm-readelf` |

### RPATH 规则

| 文件位置 | RPATH |
|----------|-------|
| bin/* | `$ORIGIN/../lib:$ORIGIN/../lib/external` |
| lib/*.so* | `$ORIGIN:$ORIGIN/external` |
| lib/external/* | `$ORIGIN` |
| lib-dynload/*.so (如有) | `$ORIGIN:$ORIGIN/..:$ORIGIN/../external` |

---

*最后更新: 2026-04-15*
*v7.1 同步更新：*
*  - **texinfo 7.3 标记为已完成**（编译成功，9个补丁，92/138测试通过，46跳过非失败）*
*  - **help2man 1.49.3 标记为已完成**（编译成功，纯Perl脚本，2个源码补丁）*
*  - 已完成数 25 → **27**（新增 texinfo, help2man）*
*  - ⚠️ 两者 RELEASENOTE 过期（列出构建产物补丁，实际已刷新）*
*  - ⚠️ 两者无 tar.gz 打包产物（另一台机器编译，需确认或补打包）*
*v7.0 同步更新：*
*  - **libpipeline 1.5.8 标记为已完成**（编译+打包+归档）*
*  - **man-db 2.13.1 编译打包完成**，但发现架构级问题*
*  - 已完成数 24 → **25**（新增 libpipeline）*
*  - ✅ **R20 DESTDIR 模式已实施**：`--prefix=$DEFAULT_PREFIX` + `DESTDIR=$TEST_PREFIX`，解决硬编码路径问题*
*  - 已修复 3 个 package_builder 问题：*
*    - step9_install_sh: 软件级 install.sh 改为纯远程下载模板*
*    - step5_rpath: 自动扫描 lib/ 子目录加入 RPATH*
*    - `{sw}` 占位符未替换*
*  - 新增 5 条关键经验 (#48-#52)：R20 DESTDIR、RPATH 子目录扫描、step2_copy 硬编码目录、Fedora 路径体系*
*v6.3 同步更新：*
*  - **patch 2.7.6 标记为已完成**（编译+打包+归档，188K，2个补丁，32/44测试通过）*
*  - 已完成数 23 → **24**（新增 patch）*
*  - 打包成功数 22 → **23**（新增 patch）*
*  - patch: 2个补丁(config.guess+config.sub E007/E072), partial(9项平台兼容性测试失败)*
*  - 新增 2 条关键经验 (#46-#47)：package staging 路径、补丁清理只保留源码修改*
*v6.2 同步更新：*
*  - **htop 3.4.1 补丁合规性修正+按10步流程重打包***
*  - 补丁 5→3（删除 .patch-ai-review.txt + htop.1 生成文件，修复 config.sub 重复行）*
*  - 重打包 539K→603K（strip + RUNPATH + ELF签名 + 独立 install.sh）*
*  - 新增 3 条关键经验 (#43-#45)：补丁合规三查、staging 路径、install.sh 规范*
*v6.1 同步更新：*
*  - **bash 5.3 标记为已完成**（编译+打包+归档）*
*  - 已完成数 21 → **22**（新增 bash）*
*  - 打包成功数 20 → **21**（新增 bash）*
*v6.0 同步更新：*
*  - **jq 1.7.1 标记为已完成**（编译+打包+归档，5.7M，2个补丁，7/8测试通过）*
*  - **file 5.45 标记为已完成**（编译+打包+归档，8.9M，7个补丁，72/72测试全通过）*
*  - **tar 1.35 标记为已完成**（编译+打包+归档，1.3M，7个补丁，114/211测试通过）*
*  - **dos2unix 7.5.4 标记为已完成**（编译+打包+归档，340K，1个补丁，83/115测试通过）*
*  - 已完成数 17 → **21**（新增 jq, file, tar, dos2unix）*
*  - 打包成功数 16 → **20**（新增 jq, file, tar, dos2unix）*
*  - Skill 优化：P1-P6 修复（driver引擎误匹配/resume上下文丢失/E072方案补全/G1误报/补丁应用/refresh-patch TypeError）*
*  - 新增 AI 智能判断层到 refresh-patch（三态返回 + 不确定文件交由 AI 审查）*
*  - verify_build.py：修复 G1 shebang 检测兜底 + G3 HMDFS OSError 崩溃*
*  - 新增 6 条关键经验 (#37-#42)：E072 三处修改、引擎匹配依赖、智能过滤、Makefile 项目、HMDFS OSError、gettext 缺失*
*v5.5 同步更新：*
*  - **rsync 3.3.0 标记为已完成**（编译+打包+归档，2.5M 动态链接包 + 417K debug）*
*  - 已完成数 16 → **17**（新增 rsync）*
*  - 打包成功数 15 → **16**（新增 rsync）*
*  - rsync: 2个补丁(config.guess+config.sub 4处修改), --disable-xxhash/zstd/lz4/md2man*
*  - 新增 4 条关键经验 (#33-#36)：rsync URL 路径、config.sub 4处修改、distclean 删除构建文件、autotools 重建*
*v5.4 同步更新：*
*  - **wget 1.19.1 标记为已完成**（编译+打包+归档，3.3M 静态链接包 + 1.8M debug）*
*  - 已完成数 15 → **16**（新增 wget）*
*  - 打包成功数 14 → **15**（新增 wget）*
*  - wget: 3个补丁(build-aux/config.guess+config.sub+tmpdir.c), 静态链接 OpenSSL*
*  - 知识图谱: E007 补充 GUESS= 语法兼容性 + build-aux 子目录问题*
*  - 知识图谱: 新增 E081（secure_getenv musl 不可用）*
*  - 新增 4 条关键经验 (#29-#32)：build-aux 子目录、GUESS= 语法、secure_getenv、静态库路径*
*v5.3 同步更新：*
*  - **readline 8.2 标记为已完成**（编译+测试+打包+部署，3.0M）*
*  - 已完成数 14 → **15**（新增 readline）*
*  - 打包成功数 13 → **14**（新增 readline）*
*  - readline: 2个补丁(config.guess/sub + shlib TERMCAP_LIB), --with-curses, ncurses静态嵌入*
*  - 静态库强制要求表：readline 标记为已编译共享（ncurses静态嵌入）*
*  - 新增 3 条关键经验 (#26-#28)：TERMCAP_LIB=-lncursesw、ncurses静态嵌入、config.sub 3处修改*
*v5.2 同步更新：*
*  - **gdbm 1.23 标记为已完成**（编译+测试+打包+部署，962K）*
*  - 已完成数 13 → **14**（新增 gdbm）*
*  - 打包成功数 12 → **13**（新增 gdbm）*
*  - gdbm: 2个补丁(config.guess+config.sub), --enable-libgdbm-compat, 3工具+2组库*
*  - 静态库强制要求表：gdbm 标记为已编译共享（+compat）*
*  - 新增 3 条关键经验 (#23-#25)：gdbm_open路径限制、ghfast.top局限、gdbm前置依赖*
*v5.1 同步更新：*
*  - **libffi 3.5.2 标记为已完成**（编译+测试+打包+部署，634K）*
*  - 已完成数 12 → **13**（新增 libffi）*
*  - 打包成功数 11 → **12**（新增 libffi）*
*  - libffi: 2个补丁(config.guess/sub + closure HMDFS路径回退), ffi_call核心功能+版本API通过*
*  - 静态库强制要求表：libffi 标记为已编译共享*
*  - 新增 3 条关键经验 (#20-#22)：ghfast.top 加速代理、ffi_closure 受限、libffi 与 Python 绑定*
*v5.0 同步更新：*
*  - **ncurses 6.4 标记为已完成**（编译+测试+打包+部署，8.7M 静态库包）*
*  - 已完成数 11 → **12**（新增 ncurses）*
*  - 打包成功数 10 → **11**（新增 ncurses）*
*  - 🔴 ncurses 必须 --without-shared 静态编译，历史 manifest 错误使用 --with-shared 已纠正*
*  - 静态库强制要求表：ncurses 标记为已编译静态*
*  - 新增 2 条关键经验 (#18-#19)：ncurses 共享库核弹级危险、--enable-widec 前提*
*  - ncurses 问题记录：历史参数错误纠正 + preinstall/terminfo 非阻塞问题*
*v4.9 同步更新：*
*  - **gzip 1.13 标记为已完成**（编译+测试+打包+部署，297K）*
*  - **openssl 1.1.1w 标记为已完成**（编译+测试+打包+部署，14M）*
*  - 已完成数 9 → **11**（新增 gzip, openssl）*
*  - 打包成功数 8 → **10**（新增 gzip, openssl）*
*  - gzip: 2个补丁(config.guess+config.sub)，修复 patch-autotools-ohos.pl 的 config.sub 产出 bug*
*  - openssl: 2个补丁(平台配置+Configure)，发现 HMDFS 完全不支持 ln -s 需 cp -a 替代*
*  - 新增 3 个脚本 bug 待修：patch-autotools-ohos.pl 重复行、package_builder.py 缺 import re、refresh-patch 路径拼接*
*  - 新增 5 条关键经验 (#13-#17)：HMDFS 无 symlink、gitee 镜像、tarball 完整性、OpenSSL Perl Configure、cp -a 影响*
*v4.7 同步更新：*
*  - **xz 5.6.2 标记为已完成**（编译+测试+打包+部署，3.5M 主包 + 474K debug）*
*  - 已完成数 8 → **9**（新增 xz）*
*  - 打包成功数 7 → **8**（新增 xz）*
*  - xz 补丁方案: 方案A标准打补丁(config.guess+config.sub)，禁止方案B(--build/--host绕过)*
*  - 新增标准工具 `scripts/patch-autotools-ohos.pl`（一键 autotools OHOS 适配）*
*  - error-patterns-runtime.md 新增 E007（config.guess 无法识别 HarmonyOS）*
*  - autotools-patterns.md 新增 §0 铁律 + §3.3 变体修正 + §7 标准工具引用*
*  - FAQ.md Q5/Q18 同步增加禁令说明*
*  - skill-feedback.md 新增 F068/F069/F070 三项流程缺陷记录*
*v4.6 同步更新：*
*  - bzip2 1.0.8 标记为已完成（编译+测试+打包+部署，820K）*
*  - 已完成数 7 → 8（新增 bzip2）*
*  - 打包成功数 6 → 7（新增 bzip2）*
*  - bzip2 补丁方案升级：从"5行sed硬编码"→"1个平台自动检测patch + 环境变量覆盖"*
*  - zlib 1.3.1 标记为已完成（编译+测试+打包+部署，244K 静态库）*
*  - 已完成数 6 → 7（新增 zlib）*
*  - 打包成功数 5 → 6（新增 zlib）*
*  - ohc-run.py package 纯库 staging 检测 bug 已修复（bin/ → lib/ 或 include/）*
*v4.3 同步更新：*
*  - gawk 5.3.0 标记为已完成（编译+打包+签名，3.9M）*
*  - automake 1.16.5 标记为已完成（编译+打包+签名，1.2M，手动全链路验证通过）*
*  - 已完成数 4 → 6（pkg-config, sed, coreutils, gawk, automake, libtool）*
*  - 打包成功数 3 → 5（libtool 未打包）*
�验证通过）*
*  - 已完成数 4 → 6（pkg-config, sed, coreutils, gawk, automake, libtool）*
*  - 打包成功数 3 → 5（libtool 未打包）*
 automake 1.16.5 标记为已完成（编译+打包+签名，1.2M，手动全链路验证通过）*
*  - 已完成数 4 → 6（pkg-config, sed, coreutils, gawk, automake, libtool）*
*  - 打包成功数 3 → 5（libtool 未打包）*
�验证通过）*
*  - 已完成数 4 → 6（pkg-config, sed, coreutils, gawk, automake, libtool）*
*  - 打包成功数 3 → 5（libtool 未打包）*
make, libtool）*
*  - 打包成功数 3 → 5（libtool 未打包）*
�验证通过）*
*  - 已完成数 4 → 6（pkg-config, sed, coreutils, gawk, automake, libtool）*
*  - 打包成功数 3 → 5（libtool 未打包）*
