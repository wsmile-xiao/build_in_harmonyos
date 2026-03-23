# 鸿蒙开发环境缺失工具清单

> **验证日期**: 2026-03-22  
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **目的**: 记录当前开发环境相较于标准 Linux 开发环境的缺失项，按优先级排列

---

## ✅ 已完成工具（第一层）

| # | 工具 | 版本 | 路径 | 状态 |
|---|------|------|------|------|
| 1 | clang/clang++ | 15.0.4 | /data/service/hnp/bin/ | ✅ 系统预装 |
| 2 | cc/c++ | 15.0.4 | $HOME/usr/local/bin | ✅ **已完成** |
| 3 | autoconf | 2.72 | 系统预装 | ✅ 完成 |
| 4 | automake | 1.16.5 | $HOME/usr/local/bin | ✅ 完成 |
| 5 | libtool | 2.4.7 | $HOME/usr/local/bin | ✅ 完成 |
| 6 | GNU tar | 1.35 | $HOME/usr/local/bin | ✅ 完成 |
| 7 | GNU sed | 4.9 | $HOME/usr/local/bin | ✅ 完成 |
| 8 | GNU gawk | 5.3.0 | $HOME/usr/local/bin | ✅ 完成 |
| 9 | **Python 3.9** | 3.9.0 | $HOME/usr/local/bin | ✅ **完成** |
| 10 | **GNU wget** | 1.19.1 | $HOME/usr/local/bin | ✅ **新增** |

### Python 3.9 详细状态

| 项目 | 状态 |
|------|------|
| python3.9 | ✅ /storage/Users/currentUser/usr/local/bin/python3.9 |
| python3 | ✅ 软链指向 python3.9 |
| pip | ✅ 20.2.3 |
| 核心模块 | ✅ 20/20 测试通过 |
| ssl | ✅ 可用 |
| readline | ✅ 可用 |
| curses | ✅ 可用 |
| sqlite3 | ✅ 可用 |
| zlib | ✅ 1.3.1 |
| ctypes | ✅ 可用 |

---

## ⚠️ 部分完成

| 工具 | 状态 | 说明 |
|------|------|------|
| GNU coreutils 9.10 | ⚠️ 部分 | 仅 cat/basename/rmdir 已编译，ls/cp/mv/rm/chown/ln/install 仍用 toybox |

---

## ❌ 待完成工具

### 🟡 第二层：影响开发效率

| # | 工具 | 现状 | 影响 | 状态 |
|---|------|------|------|------|
| 1 | strace | 缺失 | 无法追踪系统调用 | ❌ 待编译 |
| 2 | rsync | 缺失 | 文件同步不支持增量 | ❌ 待编译 |
| 3 | jq | 已安装 1.7.1 | — | ✅ 已完成 |
| 4 | GNU patch | 2.7.6 | $HOME/usr/local/bin | ✅ **已完成** |
| 5 | GNU file | toybox 0.8.10 | 文件类型检测受限 | ❌ 待编译 |
| 6 | htop | 缺失 | 进程查看简陋 | ❌ 待编译 |

### 🟢 第三层：锦上添花

| # | 工具 | 现状 | 影响 | 状态 |
|---|------|------|------|------|
| 7 | man | 缺失 | 无法查看命令文档 | ❌ 待完成 |
| 8 | valgrind | 缺失 | 内存泄漏检测 | ❌ 待评估 |
| 9 | ltrace | 缺失 | 库调用追踪 | ❌ 待完成 |
| 10 | nano | 缺失 | 轻量编辑器 | ❌ 低优先级 |

---

## 📦 已安装库

| 库 | 版本 | 用途 |
|------|------|------|
| OpenSSL | 1.1.1w | SSL/TLS 加密 |
| zlib | 1.3.1 | 压缩库 |
| ncurses | 6.4 | 终端 UI |
| readline | 8.2 | 交互式输入 |
| gettext | 0.22.5 | 国际化工具 |
| gdbm | 1.23 | 数据库 |

---

## 🛠️ 系统预装工具

| 工具 | 版本 |
|------|------|
| make | GNU Make 4.4.1 |
| cmake | 4.1.2 |
| pkg-config | 0.29.2 |
| git | 2.45.2 |
| gdb | 16.3 |
| perl | 5.42.0 |
| curl | 8.8.0-DEV |
| vim | 9.0 |
| less | 633 |

---

## 📋 建议操作顺序

```
【待编译 - 第二层】
1. strace（30分钟）                    ← 高优先级
2. rsync（15分钟）                     ← 高优先级
3. GNU patch + file（各15分钟）        ← 中优先级
4. htop                               ← 中优先级

【可选】
5. GNU coreutils 补充编译              ← 无法覆盖 toybox，仅记录
```

---

## 系统级兼容性问题

| 问题 | 影响 | 临时方案 |
|------|------|----------|
| `/tmp` 不可写 | Autotools 硬编码 /tmp 会崩溃 | `export TMPDIR=$HOME/tmp` |
| `mkfifo` 不支持 | make -j jobserver 失效 | make -j1 或 touch aclocal.m4 |
| SELinux 限制 | 符号链接访问受限 | 视具体场景处理 |

---

## 📊 完成度统计

| 层级 | 完成数 | 总数 | 完成率 |
|------|--------|------|--------|
| 第一层 | 10/10 | 10 | **100%** |
| 第二层 | 2/6 | 6 | 33% |
| 第三层 | 0/4 | 4 | 0% |
| **总计** | **12** | **20** | **60%** |

---

## 已编译软件档案

| 软件 | 版本 | 档案路径 |
|------|------|----------|
| automake | 1.16.5 | archives/a/automake/1.16.5/ |
| bash | 5.3 | archives/b/bash/5.3/ |
| bzip2 | 1.0.8 | archives/b/bzip2/1.0.8/ |
| coreutils | 9.10 | archives/c/coreutils/9.10/ |
| gawk | 5.3.0 | archives/g/gawk/5.3.0/ |
| gdbm | 1.23 | archives/g/gdbm/1.23/ |
| jq | 1.7.1 | archives/j/jq/1.7.1/ |
| libffi | 3.4.4 | archives/l/libffi/3.4.4/ |
| libtool | 2.4.7 | archives/l/libtool/2.4.7/ |
| ncurses | 6.4 | archives/n/ncurses/6.4/ |
| openssl | 1.1.1w | archives/o/openssl/1.1.1w/ |
| patch | 2.7.6 | archives/p/patch/2.7.6/ |
| python | 3.9.0 | archives/p/python/3.9.0/ |
| readline | 8.2 | archives/r/readline/8.2/ |
| sed | 4.9 | archives/s/sed/4.9/ |
| tar | 1.35 | archives/t/tar/1.35/ |
| wget | 1.19.1 | archives/w/wget/1.19.1/ |
| zlib | — | archives/z/zlib/ |

---

*最后更新：2026-03-23 10:40（GNU wget 1.19.1 编译完成，替换 toybox wget）*