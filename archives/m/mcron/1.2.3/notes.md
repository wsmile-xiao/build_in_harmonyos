# mcron 1.2.3 适配笔记

## 编译环境
- 构建系统: autotools (VPATH)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: ✅ **成功**

## 编译步骤

1. 安装所有依赖库：
   - guile 3.0.11 (VPATH 构建 + HMDFS 修复)
   - libffi 3.4.6
   - libunistring 1.3 (链接 libiconv)
   - bdwgc 8.2.8
   - readline 8.2
   - ncurses 6.4
   - gmp 6.3.0

2. 使用 VPATH 构建绕过 HMDFS 临时目录限制：
   ```bash
   mkdir -p ~/tmp/builds/mcron-1.2.3.vbuild
   cd ~/tmp/builds/mcron-1.2.3.vbuild
   ~/tmp/builds/mcron-1.2.3.work/configure --prefix=$HOME/usr/local
   ```

3. 修改 config.status 第 565 行，修复 HMDFS 临时目录问题：
   ```bash
   # 原始: tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
   # 修改: tmp="$HOME/tmp/config-tmp-mcron" && mkdir -p "$tmp" &&
   ```

4. 运行 config.status 生成 Makefile

5. 应用源码补丁修复 OHOS 用户管理不兼容问题：
   - 修改 `src/mcron/job-specifier.scm`
   - 为 `getpw(getuid)` 添加 fallback

6. 执行 make 编译

7. 执行 make install 安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: Permission denied | HMDFS 不支持在当前目录创建临时子目录 | VPATH 构建 + 修改 config.status |
| 2 | getpw: entry not found | OHOS 用户 UID 不在 /etc/passwd 中 | 修改 job-specifier.scm 添加 fallback |
| 3 | libunistring pkg-config 缺失 | 编译时未生成 .pc 文件 | 手动创建 libunistring.pc |

## 源码修改

### patches/job-specifier-getpw-fallback.patch

```scheme
;; 原始代码:
(define configuration-user (box (getpw (getuid))))

;; 修改后:
(define configuration-user
  (box (or (false-if-exception (getpw (getuid)))
           ;; OHOS fallback: create a fake passwd entry
           (vector (format #f "user~a" (getuid))
                   "x"
                   (getuid)
                   (getuid)
                   ""
                   (or (getenv "HOME") "/tmp")
                   "/bin/sh"))))
```

## 依赖版本

**必需依赖**：
| 库 | 版本 | pkg-config |
|---|---|---|
| guile | 3.0.11 | guile-3.0 |
| libffi | 3.4.6 | libffi |
| libunistring | 1.3 | libunistring |
| bdwgc | 8.2.8 | bdw-gc |
| readline | 8.2 | readline |
| ncurses | 6.4 | ncursesw |
| gmp | 6.3.0 | gmp |

## 验证结果

```bash
$ mcron --version
mcron 1.2.3
Copyright © 2003 - 2023  Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.

$ ls ~/usr/local/bin/mcron ~/usr/local/sbin/cron ~/usr/local/sbin/crontab-access
# 所有文件存在

$ find ~/usr/local/share/guile/site/3.0/mcron -name "*.scm" | wc -l
15  # Scheme 模块

$ find ~/usr/local/lib/guile/3.0/site-ccache/mcron -name "*.go" | wc -l
15  # 编译模块
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `packaging/mcron-1.2.3-ohos-aarch64.tar.gz` | 3.1MB | 预编译包 |
| `patches/job-specifier-getpw-fallback.patch` | 1KB | OHOS 用户管理补丁 |
| `manifest.yaml` | 2KB | 元数据文件 |
| `notes.md` | 4KB | 编译笔记 |

## 上库检查清单

- [x] G0: 编译成功
- [x] G1: 二进制文件存在 (bin/mcron, sbin/cron)
- [x] G2: 依赖已解决 (所有依赖库已编译)
- [x] G3: 基本运行 (--version 正常)
- [ ] G4: 功能测试 (待完成)

## 注意事项

**运行要求**：
- 需要 guile 3.0.11 及所有依赖库
- 需要 `GUILE_AUTO_COMPILE=0` 禁用自动编译
- 需要 `LD_LIBRARY_PATH` 包含 ~/usr/local/lib

**平台限制**：
- crontab-access 需要 setuid 权限
- cron 守护进程需要 root 权限运行
- 定时任务功能需要创建 /var/cron/tabs 目录