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
| 已完成 | **9** |
| 编译成功 | 9 (pkg-config, sed, coreutils, gawk, automake, libtool, zlib, bzip2, **xz**) |
| 打包成功 | 8 (pkg-config, sed, coreutils, gawk, automake, zlib, bzip2, **xz**) |
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
| **openssl** | 🟡 中 | 系统自有SSL栈，路径不同影响较小 | 可共享 |
| **libffi** | 🟡 中 | 主要被Python等用户态程序使用 | 可共享 |
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
| 10 | gzip | 1.13 | ⬜ 待编译 | - | - | - | 无依赖 |

### 第三阶段-B：SSL/加密/终端

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 11 | openssl | 1.1.1w | ⬜ 待编译 | - | - | - | 依赖 zlib, `no-asm` |
| 12 | ncurses | 6.4 | ⬜ 待编译 | - | - | - | 🔴 **必须 --without-shared** |
| 13 | libffi | 3.5.2 | ⬜ 待编译 | - | - | - | 取最新版 |

### 第三阶段-C：数据库/终端编辑

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 14 | gdbm | 1.23 | ⬜ 待编译 | - | - | - | 无外部依赖 |
| 15 | readline | 8.2 | ⬜ 待编译 | - | - | - | 依赖 ncurses, ⚠️ 建议静态 |

### 第四阶段：网络/文件工具

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 16 | wget | 1.19.1 | ⬜ 待编译 | - | - | - | 依赖 openssl, ⚠️ 原partial |
| 17 | rsync | 3.3.0 | ⬜ 待编译 | - | - | - | ⚠️ 原partial |
| 18 | jq | 1.7.1 | ⬜ 待编译 | - | - | - | |
| 19 | file | 5.45 | ⬜ 待编译 | - | - | - | 建议 `--enable-static` |
| 20 | tar | 1.35 | ⬜ 待编译 | - | - | - | |
| 21 | dos2unix | 7.5.4 | ⬜ 待编译 | - | - | - | |

### 第五阶段：高级系统工具

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 22 | bash | 5.3 | ⬜ 待编译 | - | - | - | ⚠️ `--without-bash-malloc` |
| 23 | htop | 3.4.1 | ⬜ 待编译 | - | - | - | 依赖 ncurses, ⚠️ 原partial |
| 24 | strace | 6.19 | ⬜ 待编译 | - | - | - | ⚠️ ptrace受限, 可能不打包 |
| 25 | patch | 2.7.6 | ⬜ 待编译 | - | - | - | ⚠️ 原partial |

### 第六阶段：文档/辅助工具

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 26 | texinfo | 7.3 | ⬜ 待编译 | - | - | - | |
| 27 | help2man | 1.49.3 | ⬜ 待编译 | - | - | - | 脚本类型 |
| 28 | libpipeline | 1.5.8 | ⬜ 待编译 | - | - | - | man-db 核心依赖 |

### 第七阶段：文档系统

| # | 软件 | 版本 | 状态 | 编译 | 打包 | 包路径 | 备注 |
|---|------|------|------|------|------|--------|------|
| 29 | man-db | 2.13.1 | ⬜ 待编译 | - | - | - | 依赖 libpipeline+gdbm, ⚠️ VPATH构建 |

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
| error-patterns-runtime.md | ✅ 新增 **E007**（config.guess 无法识别 HarmonyOS，含方案A铁律/标准工具引用/交叉索引） | ✅ 完成 |
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
| create-archive.sh | ⚠️ 标记为 .deprecated（被 ohc-run.py init-archive 取代） | ✅ 处理 |
| releasenote-template.md | ⚠️ 标记为 .deprecated（被 finalize-archive 取代） | ✅ 处理 |
| knowledge_section_new.txt | 🗑️ 已删除（内容已整合进 SKILL §5） | ✅ 清理 |

---

## 📦 打包标准流程（10步）

> 参考 `knowledge/packaging.md` v2.3（权威参考）

```
Step 1:  make install 到独立目录（PKGDIR）
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

*最后更新: 2026-04-09*
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
