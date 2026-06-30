# apcupsd 3.14.14 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build apcupsd 3.14.14 --url=https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/a/apcupsd/apcupsd_3.14.14.orig.tar.gz
```

2. 平台适配（替换旧的 config.guess/config.sub）
```bash
cp ~/builds/xinit-1.4.4.work/config.guess autoconf/
cp ~/builds/xinit-1.4.4.work/config.sub autoconf/
```

3. 解决 HMDFS 临时文件问题
```bash
# 创建临时目录
mkdir -p .tmp && chmod 1777 .tmp

# 修改 configure 使用 .tmp 目录
sed -i 's|mktemp -d "./confXXXXXX"|mktemp -d ".tmp/confXXXXXX"|' configure
sed -i '14063s|tmp=./conf$$-$RANDOM|tmp=.tmp/conf$$-$RANDOM|' configure

# 关键：去掉 umask 077（HMDFS 限制）
sed -i 's|(umask 077 && mktemp -d ".tmp/confXXXXXX")|mktemp -d ".tmp/confXXXXXX"|' configure
sed -i 's|(umask 077 && mkdir "\$tmp")|mkdir "$tmp"|' configure
```

4. 配置和编译
```bash
export CC=clang CXX=clang++
./configure --prefix=$DEFAULT_PREFIX
make -j1
```

5. 安装
```bash
# DESTDIR 模式
make install DESTDIR=$TEST_PREFIX

# 本地安装（验证）
make install
$DEFAULT_PREFIX/sbin/apcupsd --version
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 临时文件权限问题 | autotools 使用 `./confXXXXXX`，HMDFS SELinux 限制 | 使用 `.tmp` 目录 + 去掉 umask 077 |
| 2 | config.guess 无法识别 HarmonyOS | 2014 版本过旧，补丁脚本失败 | 替换为已工作的 config.guess |
| 3 | pthread_cancel 未声明 | HarmonyOS 不支持 pthread_cancel | 添加 `#ifndef __OHOS__` 条件编译 |
| 4 | sbindir 硬编码为 /sbin | apcupsd 特殊配置 | 修改 variables.mak 使用 ${exec_prefix}/sbin |
| 5 | HALPOLICYDIR 硬编码为 /usr/share/hal | 系统目录权限问题 | 修改为 ${datadir}/hal/fdi/policy/20thirdparty |
| 6 | man/col 命令不存在 | 文档生成依赖缺失 | 创建空的 man 文档文件 |

## 源码修改

**5 个补丁文件**：
1. `0001-autoconf-config.guess.patch` - 替换为支持 HarmonyOS 的版本
2. `0002-autoconf-config.sub.patch` - 替换为支持 linux-ohos 的版本
3. `0003-autoconf-variables.mak.patch` - 修正 sbindir/sysconfdir/HALPOLICYDIR 路径
4. `0004-configure.patch` - HMDFS 临时文件修复（使用 .tmp 目录）
5. `0005-src-lib-apcexec.c.patch` - pthread_cancel 条件编译

## 依赖版本

- clang 15.0.4
- make 4.4.1
- autoconf 2.72
- automake 1.17

## 验证结果

```bash
$ ~/usr/local/sbin/apcupsd --version
apcupsd 3.14.14 (31 May 2016) unknown

$ file ~/usr/local/sbin/apcupsd
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| apcupsd | 783KB | UPS 电源管理守护进程 |
| apcaccess | 115KB | UPS 状态访问工具 |
| apctest | 839KB | UPS 测试工具 |
| smtp | 58KB | SMTP 邮件发送工具 |

## 注意事项

### HMDFS 临时文件兼容性（核心发现）

**问题**：HMDFS 文件系统有 SELinux 策略限制，autotools 的临时文件创建方式会失败：
- `mktemp -d "./confXXXXXX"` 创建的目录权限过于严格（`drwx--S---`）
- `umask 077` 导致新创建的目录无法写入文件

**解决方案**：
1. 使用源码目录内的 `.tmp` 目录（与源码同 SELinux 上下文）
2. **去掉 `umask 077`**，使用默认权限（`drwxrws--x`）

**补丁位置**：configure 脚本第 14059-14063 行

### pthread_cancel 平台限制

HarmonyOS 不支持 `pthread_cancel`，需要条件编译绕过：
```c
#ifndef __OHOS__
pthread_cancel(thread_id[i]);
#endif
```

---

**编译结束**: 2026-06-02 18:09
**最终状态**: built
