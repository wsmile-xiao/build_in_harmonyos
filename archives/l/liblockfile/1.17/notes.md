# liblockfile 1.17 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`python3 ohc-run.py init-build liblockfile 1.17 --url=https://ftp.debian.org/debian/pool/main/libl/liblockfile/liblockfile_1.17.orig.tar.gz`
2. 修复 configure 中的 umask 设置（HMDFS 权限问题）
3. 修复 dotlockfile.c 中 getpwuid 返回 NULL 的问题（鸿蒙系统无用户名映射）
4. 修复 lockfile.c 中 link() 不支持的问题（HMDFS 不支持硬链接）
5. 执行 configure + make 编译
6. 手动 staging 安装（Makefile 中的 install 命令使用 toybox 不支持的选项）
7. 执行测试套验证
8. 制作预编译包
9. 本地安装验证
10. finish 收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法创建临时文件 | HMDFS 的 hmmac 强制访问控制限制了 umask 077 创建的文件权限 | 修改 configure 中的 umask 077 为 umask 022 |
| 2 | dotlockfile -m 报错 "You don't exist" | 鸿蒙系统用户 ID 没有对应的用户名映射，getpwuid 返回 NULL | 修改 dotlockfile.c，当 getpwuid 返回 NULL 时使用数字形式的 UID |
| 3 | 锁创建失败（L_MAXTRYS） | HMDFS 不支持硬链接，link() 操作失败 | 修改 lockfile.c，使用 open(O_CREAT|O_EXCL) 替代 link() 进行原子锁创建 |
| 4 | make install 失败 | Makefile 中的 install 命令使用 toybox 不支持的选项（-d -p） | 手动执行 staging 安装 |

## 源码修改

### 0001-configure.patch
- 修改 umask 077 为 umask 022，解决 HMDFS 权限问题

### 0002-dotlockfile.c.patch
- 处理 getpwuid 返回 NULL 的情况，使用数字形式的 UID

### 0003-lockfile.c.patch
- 使用 open(O_CREAT|O_EXCL) 替代 link() 实现原子锁创建
- HMDFS 不支持硬链接，必须使用其他原子操作方式

## 依赖版本

- 无外部依赖

## 验证结果

```bash
# 测试套验证
$ sh run-tests.sh
tests OK

# 本地安装验证
$ dotlockfile -l -r 1 testlock.lock
Lock OK
$ dotlockfile -u testlock.lock
Unlock OK
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| liblockfile-1.17-ohos-aarch64.tar.gz | 127KB | 预编译包（静态库 + dotlockfile） |
| liblockfile-1.17-ohos-aarch64-debug.tar.gz | 48KB | 调试符号包 |

## 注意事项

1. HMDFS 不支持硬链接，这是平台限制，所有依赖 link() 的锁机制都需要适配
2. 鸿蒙系统用户 ID 可能没有用户名映射，需要处理 getpwuid 返回 NULL 的情况
3. toybox 的 install 命令功能有限，可能需要手动执行安装步骤

---

**编译结束**: 2026-06-03 10:05
**最终状态**: built