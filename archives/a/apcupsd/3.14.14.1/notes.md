# apcupsd 3.14.14.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build apcupsd 3.14.14 --url=https://downloads.sourceforge.net/project/apcupsd/apcupsd%20-%20Stable/3.14.14/apcupsd-3.14.14.tar.gz
```

2. 应用补丁（config.guess/config.sub, configure, apcexec.c）

3. 解决 HMDFS 临时文件问题（补丁 0003-configure.patch）
```bash
mkdir -p .tmp && chmod 1777 .tmp
# configure 补丁已处理 mktemp 路径和 umask 077
```

4. 配置和编译
```bash
export CC=clang CXX=clang++
export SHUTDOWN=/bin/poweroff
export PATH=$DEFAULT_PREFIX/bin:$PATH  # wall/mail/man/col wrappers
./configure --prefix=$DEFAULT_PREFIX --sbindir=${exec_prefix}/sbin --sysconfdir=${prefix}/etc/apcupsd
# 修复 variables.mak（configure 会覆盖补丁）
make -j1
```

5. 安装
```bash
make install DESTDIR=$TEST_PREFIX STRIP=
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 临时文件权限问题 | autotools 使用 `./confXXXXXX`，HMDFS SELinux 限制 | 使用 `.tmp` 目录 + 去掉 umask 077 |
| 2 | config.guess 无法识别 HarmonyOS | 2014 版本过旧 | 替换为支持 HarmonyOS 的版本 |
| 3 | pthread_cancel 未声明 | HarmonyOS 不支持 pthread_cancel | 添加 `#ifdef HAVE_PTHREAD_CANCEL` 功能检测宏（R8 合规） |
| 4 | sbindir 硬编码为 /sbin | apcupsd configure 特殊逻辑 | 传 `--sbindir` 参数 + configure 后修改 variables.mak |
| 5 | HALPOLICYDIR 硬编码 | 系统目录权限问题 | 修改为 ${datadir}/hal/fdi/policy/20thirdparty |
| 6 | man/col 命令不存在 | 文档生成依赖缺失 | 创建 man/col wrapper 脚本 |
| 7 | configure 需要 shutdown 命令 | HarmonyOS 无 shutdown | 设 `SHUTDOWN=/bin/poweroff` 环境变量 |
| 8 | configure 需要 wall/mail 命令 | HarmonyOS 无 wall/mail | 创建 wrapper 脚本 |
| 9 | STRIP=llvm-strip 导致 install 失败 | install 命令将 strip 程序名当参数 | make install STRIP= 覆盖 |
| 10 | configure 覆盖 variables.mak | configure 从模板重新生成 | configure 后重新修改 sbindir/HALPOLICYDIR |

## 源码修改

**4 个补丁文件**：
1. `0001-autoconf-config.guess.patch` - 替换为支持 HarmonyOS 的版本
2. `0002-autoconf-config.sub.patch` - 替换为支持 linux-ohos 的版本
3. `0003-configure.patch` - HMDFS 临时文件修复（使用 .tmp 目录）
4. `0004-src-lib-apcexec.c.patch` - pthread_cancel 功能检测宏（`#ifdef HAVE_PTHREAD_CANCEL`，R8 合规）

> 注：variables.mak 的 sbindir/sysconfdir 修复在 conanfile.py 的 `_fix_variables_mak()` 方法中处理，
> 因为 configure 会从 variables.mak.in 重新生成 variables.mak，覆盖任何补丁。

## 依赖版本

- clang 15.0.4
- make 4.4.1
- autoconf 2.72

## 验证结果

```bash
$ apcupsd --version
apcupsd 3.14.14 (31 May 2016) unknown
```

## 交付物

| 文件 | 说明 |
|------|------|
| apcupsd | UPS 电源管理守护进程 |
| apcaccess | UPS 状态访问工具 |
| apctest | UPS 测试工具 |
| smtp | SMTP 邮件发送工具 |

## 注意事项

### HMDFS 临时文件兼容性（核心发现）

**问题**：HMDFS 文件系统有 SELinux 策略限制，autotools 的临时文件创建方式会失败：
- `mktemp -d "./confXXXXXX"` 创建的目录权限过于严格（`drwx--S---`）
- `umask 077` 导致新创建的目录无法写入文件

**解决方案**：
1. 使用源码目录内的 `.tmp` 目录（与源码同 SELinux 上下文）
2. **去掉 `umask 077`**，使用默认权限（`drwxrws--x`）

### pthread_cancel 功能检测（R8 合规）

HarmonyOS/musl 不支持 `pthread_cancel`，通过功能检测宏 `HAVE_PTHREAD_CANCEL` 条件编译：
```c
#ifdef HAVE_PTHREAD_CANCEL
         pthread_cancel(thread_id[i]);
#endif
```
conanfile.py 在 build() 中通过编译测试检测 `pthread_cancel` 是否可用，可用时定义 `HAVE_PTHREAD_CANCEL`。

### configure 覆盖 variables.mak

apcupsd 的 configure 从 `variables.mak.in` 模板重新生成 `variables.mak`，会覆盖任何预先应用的补丁。
需要在 conanfile.py 的 `build()` 方法中，在 configure 之后修改生成的 `variables.mak`。

---

**编译结束**: 2026-08-05
**最终状态**: built
