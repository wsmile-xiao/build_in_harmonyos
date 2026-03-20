# 鸿蒙开发环境缺失工具清单

> **生成日期**: 2026-03-19  
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **目的**: 记录当前开发环境相较于标准 Linux 开发环境的缺失项，按优先级排列

---

## 🔴 第一层：严重影响日常开发

| # | 缺失项 | 现状 | 影响 | 编译指南 | 状态 |
|---|--------|------|------|----------|------|
| 1 | cc/c++ | PATH 中不存在，只有 clang/clang++ | configure/cmake 硬编码 cc 时找不到编译器 | SKILL.md 问题20 | ✅ 已通过软链解决 |
| 2 | automake | 缺失（仅有 autoconf 2.72） | Autotools 项目无法完成 generate → configure 流程 | build_in_harmonyos/a/automake/1.16.5/ | ✅ 已编译安装 |
| 3 | libtool | 缺失 | 大量库项目的 Autotools 构建依赖 | build_in_harmonyos/l/libtool/2.4.7/ | ✅ 已编译安装（libtoolize 在 zsh 下有兼容问题） |
| 4 | GNU tar | 使用 toybox 版（/bin/tar） | v7 格式 UID 超限、xattrs 不支持、功能受限 | build_in_harmonyos/t/tar/1.35/ | ✅ 已编译并软链到 PATH |
| 5 | GNU sed | 已编译安装到 $HOME/usr/local/bin/sed | — | build_in_harmonyos/s/sed/4.9/ | ✅ 已完成 |
| 6 | GNU awk (gawk) | 已编译安装到 $HOME/usr/local/bin/gawk | — | build_in_harmonyos/g/gawk/5.3.0/ | ✅ 已完成 |
| 7 | GNU coreutils | ls/cp/mv/rm/cat/chown 等全是 toybox | 权限处理、路径解析、选项兼容性有差异 | build_in_harmonyos/c/coreutils/9.10/ | ⚠️ 已编译，ls/cp/mv/rm/chown/ln/install 无法覆盖系统 toybox（仅作记录） |
| 8 | Python 3 | 不可用 | 大量开发脚本、meson 构建系统、pip 生态依赖 | build_in_harmonyos/python/ | ⚠️ 主程序可用，60个扩展模块因签名限制失败 |

## 🟡 第二层：影响开发效率但不阻塞

| # | 缺失项 | 现状 | 影响 | 编译指南 | 状态 |
|---|--------|------|------|----------|------|
| 9 | strace | 缺失 | 无法追踪系统调用，排查程序行为困难 | 待补充 | ❌ 待完成 |
| 10 | rsync | 缺失 | 文件同步只能靠 scp，不支持增量传输 | 待补充 | ❌ 待完成 |
| 11 | jq | 缺失 | JSON 处理无趁手工具 | 待补充 | ❌ 待完成 |
| 12 | GNU patch | 使用 toybox 版 | 复杂补丁（context/diff 格式）可能不兼容 | 待补充 | ❌ 待完成 |
| 13 | GNU file | 使用 toybox 版 | 文件类型检测功能受限 | 待补充 | ❌ 待完成 |
| 14 | htop | 缺失，仅有 toybox top | 进程查看极其简陋 | 待补充 | ❌ 待完成 |

## 🟢 第三层：锦上添花

| # | 缺失项 | 现状 | 影响 | 编译指南 | 状态 |
|---|--------|------|------|----------|------|
| 15 | man | 缺失，man 命令不存在 | 无法查看命令文档 | 待补充 | ❌ 待完成 |
| 16 | valgrind | 缺失 | C/C++ 内存泄漏检测 | 待补充 | ❌ 待评估（移植难度大） |
| 17 | ltrace | 缺失 | 库调用追踪 | 待补充 | ❌ 待完成 |
| 18 | nano | 缺失 | 轻量编辑器（已有 vim） | 待补充 | ❌ 低优先级 |

---

## 系统级兼容性问题

这些不是工具缺失，而是鸿蒙系统本身的限制，需要通过环境配置绕过：

| 问题 | 影响 | 临时方案 | SKILL.md 参考 |
|------|------|----------|---------------|
| `/tmp` 不可写 | Autotools 等工具硬编码 /tmp 会崩溃 | `export TMPDIR=$HOME/tmp` | — |
| `mkfifo` 不支持 | Autotools jobserver 失效，make -j 降级 | touch aclocal.m4 跳过 / make -j1 | — |
| `libomp.so` 缺失 | 系统 msgmerge 等工具无法运行 | 用户安装 gettext 工具链绕过 | 问题19 |
| SELinux 限制 | 符号链接访问、部分文件操作受限 | 视具体场景处理 | 问题17 |

---

## 已就绪工具

以下工具已预装在系统中，功能完整可用：

| 工具 | 版本/路径 | 备注 |
|------|-----------|------|
| clang/clang++ | 15.0.4 (/data/service/hnp/bin/) | CC/CXX 环境变量已预设 |
| make | GNU Make 4.4.1 | — |
| cmake | 4.1.2 | — |
| autoconf | 2.72 | — |
| pkg-config | 0.29.2 | — |
| git | 2.45.2 | — |
| gdb | 可用 | 首次运行需确认签名 |
| perl | 5.42.0 | — |
| curl | 8.8.0-DEV | — |
| ssh/scp/sftp | 可用 | — |
| vim | 9.0 | — |
| less | 可用 | — |
| OpenSSL | 1.1.1w（用户安装） | — |
| libtool | 2.4.7（用户安装） | libtoolize 在 zsh 下有兼容问题，详见问题23/24 |
| gettext | 0.22.5（用户安装） | 含 msgmerge/msgfmt 等 |

---

## 建议编译顺序

```
1. cc/c++ 软链（5分钟）                    ✅ 已完成
2. automake + libtool（30分钟）             ✅ 均已完成
3. GNU tar + sed 软链（5分钟）              ✅ 已完成
4. GNU coreutils（无法覆盖系统 toybox，仅记录）
5. gawk（15分钟）                           ← 下一步
6. Python 3 扩展模块修复                    ← 阻塞点：签名机制限制
7. strace（30分钟）                         ← 待编译
8. jq + rsync（各15分钟）                   ← 待编译
9. GNU patch + file（各15分钟）             ← 待编译
10. htop + 其他效率工具                      ← 待编译
```

---

*此文件由环境摸底自动生成，随着工具编译完成逐步更新状态。*
*最后更新：2026-03-19 23:30*
