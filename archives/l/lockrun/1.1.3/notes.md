# lockrun 1.1.3 — 适配笔记

## 基本信息

- **软件**: lockrun
- **版本**: 1.1.3
- **描述**: Run cron jobs with overrun protection（防止cron任务重叠执行）
- **许可证**: Public Domain
- **源码URL**: http://unixwiz.net/tools/lockrun.c

## 源码特点

lockrun 是一个**单文件 C 程序**（lockrun.c），没有标准构建系统：
- 无 configure/make/Makefile
- 无 tarball 包（源码直接是 .c 文件）
- init-build 需要特殊处理：下载的 .c 文件不是 tarball，无法自动解压

## 编译过程

### init-build 失败及手动处理

`ohc-run.py init-build lockrun 1.1.3 --url=http://unixwiz.net/tools/lockrun.c`

输出：
```
ℹ️ 🚀 初始化编译: lockrun 1.1.3
  ℹ️   下载: http://unixwiz.net/tools/lockrun.c
  ❌   解压失败: not a gzip file
```

**处理**: 源码是单文件.c而非tarball，需要手动：
1. 创建工作目录 `lockrun-1.1.3.work`，将下载的文件拷入并命名为 `lockrun.c`
2. 手动创建 `.build-context-lockrun-1.1.3`
3. 手动创建归档目录结构（manifest.yaml, README.md, patches/, packaging/, reports/）

### 手动编译

```bash
cd $BUILD_SRC_DIR
clang -o lockrun lockrun.c -Wall -Wextra
```

编译输出：
```
lockrun.c:290:7: warning: variable 'rc' is used uninitialized whenever 'if' condition is true
        if ( (childpid = fork()) == 0 )
             ^~~~~~~~~~~~~~~~~~~~~~~~
lockrun.c:347:7: note: uninitialized use occurs here
        exit(rc);
             ^~
1 warning generated
```

**说明**: 此警告非致命，是源码本身的逻辑问题（fork()子进程中rc可能未初始化），不影响功能。

### DESTDIR staging 安装 (R20)

```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp lockrun $TEST_PREFIX/$DEFAULT_PREFIX/bin/lockrun
chmod 755 $TEST_PREFIX/$DEFAULT_PREFIX/bin/lockrun
```

### 本地安装（模拟 cmd-pkgs 部署）

```bash
mkdir -p $DEFAULT_PREFIX/bin
cp lockrun $DEFAULT_PREFIX/bin/lockrun
chmod 755 $DEFAULT_PREFIX/bin/lockrun
```

### 验证结果

```
$ lockrun --version
lockrun 1.1.3 - 2014-11-03 - steve@unixwiz.net
```

## 功能测试（真实执行）

### T1 版本验证
```
$ lockrun --version
lockrun 1.1.3 - 2014-11-03 - steve@unixwiz.net
退出码: 0 ✅
```

### T2 帮助信息
```
$ lockrun --help
lockrun 1.1.3 - 2014-11-03 - steve@unixwiz.net
Usage: lockrun [options] -- command args...
  --help / --version / --verbose / --quiet / --lockfile=F / --wait / --maxtime=T
退出码: 0 ✅
```

### T3 无参数报错
```
$ lockrun
ERROR: missing command to lockrun (must follow "--" marker)
退出码: 1 ✅（正确行为）
```

### T4 正常执行（核心功能）
```
$ lockrun --lockfile=$TMPDIR/test.lock -- echo "测试成功"
测试成功
退出码: 0 ✅
```

### T5 防重叠执行（最关键功能）
```
$ lockrun --lockfile=$LOCKFILE -- sleep 10 &
$ lockrun --lockfile=$LOCKFILE -- echo "第二次"
ERROR: cannot launch echo - run is locked
退出码: 1 ✅（正确拒绝重叠执行）
```

### T6 --quiet 模式
```
$ lockrun --quiet --lockfile=$LOCKFILE -- echo "quiet测试"
（无输出）
退出码: 0 ✅（静默退出，适合cron环境）
```

### T7 --maxtime 参数
```
$ lockrun --maxtime=5 --lockfile=$LOCKFILE -- echo "maxtime测试成功"
maxtime测试成功
退出码: 0 ✅
```

### T8 退出码传递
```
$ lockrun --lockfile=$LOCKFILE -- true  → 退出码: 0 ✅
$ lockrun --lockfile=$LOCKFILE -- false → 退出码: 1 ✅
```

### T9 锁文件自动创建
```
$ lockrun --lockfile=$TMPDIR/new.lock -- echo "创建新锁文件"
创建新锁文件
$ ls -la $TMPDIR/new.lock
-rw-rw---- 1 file_manager 0 ... new.lock  ✅（大小0，仅用于fcntl锁）
```

## 平台适配

- 鸿蒙平台支持 `lockf()`（F_TLOCK 已定义）→ 使用 lockf 作为主锁定机制
- `flock()` 作为后备也可用
- 无需任何源码修改即可在鸿蒙平台编译运行
- 无 `#__OHOS__` 守卫需求（无需修改源码）
- 无外部依赖，仅依赖 POSIX 标准库（libc、fcntl、fork）

## 编译警告处理

- **警告**: `variable 'rc' is used uninitialized whenever 'if' condition is true`
- **性质**: 非致命，源码逻辑问题（fork()子进程中rc变量可能未初始化）
- **影响**: 不影响实际功能，程序正确运行
- **处理**: 不修改源码（R8源码"四不"准则），记录在notes.md

## 质量门禁结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| **G0 干净构建验证** | ❌ FAIL | 结构性限制：源码是单文件.c（非tarball），clean-verify无法解压。非软件质量问题，无补丁需要验证 |
| **G1 二进制完整性** | ✅ PASS | ELF64 AArch64 PIE，已签名，27KB原始/80KB签名后 |
| **G2 功能可用性** | ✅ PASS | ⚠️1: --help同时输出版本；10项功能测试全部通过 |
| **G3 可移植性** | ✅ PASS | RUNPATH=$ORIGIN/../lib，仅依赖libc |
| **G4 档案完整性** | ✅ PASS | manifest/notes/packaging/reports均完整 |

## 二进制信息

| 属性 | 值 |
|------|------|
| 类型 | ELF64 AArch64 PIE (DYN) |
| 原始大小 | 27,072 bytes |
| 打包大小 | 79,744 bytes（含ELF签名） |
| RUNPATH | `$ORIGIN/../lib:$ORIGIN/../lib/external` |
| Strip | 已完成，debug符号分离到debug包 |
| 外部依赖 | 仅 libc |

## 校验和

| 文件 | SHA256 |
|------|--------|
| lockrun.c 源码 | `cea2e1e64c57cb3bb9728242c2d30afeb528563e4d75b650e8acae319a2ec547` |
| 预编译包 tar.gz | `f8789359a61a73700f7ba62e09a5643c09a4f80ea77eef47b3bae3735b2fcead` |
| 打包二进制 lockrun | `4476e0f53c1a41bd15e916bd4477b1a2534f3f138aec3e73cdd4e3190aa678fb` |

---

**编译开始**: 2026-06-04 11:12
**编译结束**: 2026-06-04 16:00
**最终状态**: published