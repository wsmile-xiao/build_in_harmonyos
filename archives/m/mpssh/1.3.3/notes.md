# mpssh 1.3.3 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure，install 目标不可用）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4
- 状态: built

## 软件概述

mpssh（Mass Parallel SSH）并行 spawn 多个 ssh 进程，对 hosts 文件中的
主机列表批量执行同一命令。hosts 文件支持 `user@host:port` 逐行格式与
`%label` 分组。无任何外部依赖（仅 libc），运行时 exec 外部 ssh/scp 二进制。

- 上游: https://github.com/ndenev/mpssh
- License: BSD-3-Clause
- 构建产物: 单一二进制 `mpssh` + man page `mpssh.1`

## 编译步骤

1. 源码下载：从 GitHub 下载 v1.3.3 tag 的 tar.gz（SHA256 两次下载验证一致）
2. 编译（Makefile 硬编码 CC=gcc/LD=gcc，OHOS 需显式覆盖）：
   ```bash
   make CC=clang LD=clang SSHPATH=/usr/bin/ssh SCPPATH=/usr/bin/scp -j1
   ```
3. 手动安装（install 目标用 GNU install + /usr/local/bin，鸿蒙不可用）：
   ```bash
   cp mpssh $PACKAGE/bin/ && cp mpssh.1 $PACKAGE/share/man/man1/
   ```
4. ELF 签名（鸿蒙必需）：
   ```bash
   binary-sign-tool sign -inFile mpssh -outFile mpssh.signed -selfSign 1
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真实任务 100% SIGSEGV (rc=139) | 无 passwd 条目的系统（如 OHOS 服务账号）上 `getpwuid(getuid())` 返回 NULL，`user = pw->pw_name` 无守卫解引用（E338） | 补丁 0001：所有 POSIX 平台无条件 NULL 守卫，回退 `$USER` → `$LOGNAME` → `"nobody"`（strdup 避免悬垂） |
| 2 | make 失败: gcc: No such file or directory | Makefile 硬编码 `CC = gcc`、`LD = gcc`，OHOS 工具链只有 clang（E053 set-env-var 问题族） | build() 显式传 `CC=clang LD=clang`（从 `tools.build:compiler_executables` 获取，R33） |
| 3 | SSHPATH 烘焙错误路径 | Makefile 用 `` `which ssh` `` 在编译期求值，交叉环境可能取错 | 显式传 `SSHPATH=/usr/bin/ssh SCPPATH=/usr/bin/scp` 烘焙标准位置 |
| 4 | make install 不可用 | 使用 GNU coreutils install、strip、`-o root`、/usr/local/bin | conanfile.py 用 Conan `copy()` 手动安装 |
| 5 | ELF 签名 | 鸿蒙要求 ELF 必须签名才能执行 | package() 中 binary-sign-tool 签名（R38/E082） |
| 6 | 偶发 SIGSEGV (~8%)：SIGCHLD 竞态 | `reap_child` 中 `pslot_bypid()` 找不到 pid 时返回 NULL，`ps->pid = 0` 解引用 NULL；且 `ps = pslot_del(ps)` 移动全局游标，主 select 循环遍历已释放节点（use-after-free）。`pslot_del` is_last 分支 `pslots++` 方向写反。上游真实缺陷（glibc 同样存在，musl 上更易触发） | 补丁 0002：reap 用局部 `done_ps` + NULL continue；不动全局游标；修正 pslots 计数方向 |

## 正反验证（E338 补丁）

**反向（原版崩溃）**：本机（OHOS PC，uid 无 passwd 条目）构建未打补丁版本：
```
$ env -u USER -u LOGNAME ./mpssh-original -f hosts.txt -p 1 true
Signal 11 (core dumped)     # EXIT=139
```

**正向（补丁版正常）**：
```
$ env -u USER -u LOGNAME ./mpssh-patched -f hosts.txt -p 1 true   # EXIT=0
```

**回退用户名验证**（outdir 文件名含 `user@host`，直接观察实际生效用户名）：
- 无 USER/LOGNAME → `nobody@127.0.0.1.err`
- USER=testuser → `testuser@127.0.0.1.err`
- `-u explicituser` → `explicituser@127.0.0.1.err`（-u 优先级最高，不进回退分支）

## 并行性实测

本地慢监听器（每连接保持 2s），8 主机：
- `-p 8`：wall 2.13s，8 个连接 0.04s 内全部到达（真并行）
- `-p 1`：wall 16.26s，连接到达间隔 14.21s（串行）

结论：并行调度真实有效，`-p` 参数真实生效。

## 源码修改

补丁 `patches/0001-fix-getpwuid-null-deref.patch`：
- 位置：`mpssh.c` main() 中 `user` 默认值获取处
- 方式：getpwuid NULL 检查 + 三级回退（USER → LOGNAME → "nobody"），所有 POSIX 平台无条件生效（无平台条件编译）
- 原 `user = pw->pw_name` 路径在 getpwuid 命中时保持不变

补丁 `patches/0002-fix-sigchld-race-and-pslot-count.patch`：
- 位置：`mpssh.c` reap_child() + `pslot.c` pslot_del()
- 方式：reap 循环改用局部 `done_ps` 指针（不动全局游标 `ps`，消除 use-after-free）；`pslot_bypid` 返回 NULL 时 continue（消除 NULL 解引用）；`pslot_del` is_last 分支计数 `pslots++` → `pslots--`
- 平台无关 bugfix（无条件生效，无任何平台条件编译，所有 POSIX 平台受益）

### 正反验证（0002 竞态补丁）

同一压测循环（单主机 `-p 1 -b true` × 60 次，`env -u USER -u LOGNAME`）：
- 仅 0001（conan 包二进制）：**5/60 崩溃**（rc=139，`ssh failure` 后 SIGSEGV）
- 0001+0002：**0/60 崩溃**，全部正常打印 `Done. 1 hosts processed.` 退出

崩溃机理（trace 定位）：SIGCHLD 在 fork 返回与 `ps->pid = pid` 赋值间送达 →
`pslot_bypid` 遍历不到目标 pid 返回 NULL → `ps->pid = 0` 解引用 NULL。同时
`ps = pslot_del(ps)` 改写全局游标，主 select 循环用 `ps` 遍历链表时访问已
free 节点。glibc 上同样存在（上游缺陷），musl 信号语义下更易触发。

## 依赖说明

无外部依赖。仅 libc；运行时通过 execv 调用外部 ssh/scp（路径编译期烘焙为
`/usr/bin/ssh`、`/usr/bin/scp`）。

## 构建系统说明

mpssh 使用纯 Makefile 构建：
- 目标：`all`、`$(PROG)`、`%.o`、`clean`、`install` — **无 test/check 目标**
- 上游无任何自动化测试（无 tests/ 目录，debian/ 打包无 test runner）
- 上游正式测试数为 0，经源码及 Makefile 核查；已在 test_package/MANIFEST.yml
  中以 `upstream_tests_exist: false` + `upstream_test_audit` 包内声明
  （不在 ci/config/no_official_test.txt 全局白名单中）

## 版本验证

```bash
$ mpssh -V
mpssh-1.3.3
```

## 退出码语义（测试断言依据）

| 场景 | 退出码 |
|------|--------|
| usage（无参数/-h） | 0 |
| hosts 文件不存在/为空 | 1 |
| 正常完成（含所有 ssh 失败） | 0 |
| 打补丁前真实任务（OHOS 无 passwd） | 139 (SIGSEGV) — 已修复 |

## 交付物

| 文件 | 说明 |
|------|------|
| mpssh/1.3.3/conanfile.py | Conan 配方（Makefile 构建 + ELF 签名） |
| mpssh/1.3.3/conandata.yml | 源码 URL + sha256 + 补丁声明 |
| mpssh/1.3.3/patches/0001-*.patch | getpwuid NULL 守卫补丁（E338） |
| mpssh/1.3.3/patches/0002-*.patch | SIGCHLD reap 竞态 + pslot 计数修复（上游缺陷） |
| mpssh/1.3.3/test_package/test.sh | 功能测试（并行性/参数解析/退出码/getpwuid 回退） |
| mpssh/1.3.3/test_package/test_ohos_mpssh.py | 鸿蒙特有测试（ELF64 AArch64/musl/.codesign/无RPATH/无宿主路径） |
| mpssh/1.3.3/test_package/MANIFEST.yml | 上游测试声明（上游 0 测试+证据） |
| mpssh/commands.json | 命令行工具声明（R38） |

## 注意事项

- Makefile 的 `SSHPATH = \`which ssh\`` 在编译期展开，交叉构建必须显式传值
- `-u` 参数指定用户时不走 getpwuid 路径，但默认路径（无 -u）在 OHOS 上必须打补丁
- hosts 文件条目自带的 `user@` 前缀优先于全局用户名
- outdir（-o）生成的文件名为 `%s/%s@%s.out/.err` 格式，可作为用户名生效证据
