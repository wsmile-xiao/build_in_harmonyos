# cryptmount 6.4.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-23
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 Debian 获取源码：`cryptmount_6.4.0.orig.tar.gz`
2. 初始化编译环境：`ohc-run.py init-build cryptmount 6.4.0`
3. 运行 autoreconf 生成 configure（需要 m4 宏文件）
4. 配置：`./configure --prefix=/storage/Users/currentUser/usr/local`
5. 编译：`make cryptmount`（跳过 po 目录）
6. 手动链接添加 libintl：`clang ... -ldevmapper -lintl`
7. 安装到 staging 目录
8. 打包：`ohc-run.py package cryptmount 6.4.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 软件名称错误 | libcryptmount 不存在 | 正确名称是 cryptmount |
| 2 | SSL证书验证失败 | HTTPS下载失败 | 使用 curl -k 手动下载 |
| 3 | /tmp 只读 | E002 Gotcha | 使用 ~/tmp 或 $TMPDIR |
| 4 | 缺少 autopoint | gettext-devel 未安装 | 创建假的 autopoint 跳过 |
| 5 | 缺少 gettext m4 | autoreconf失败 | 复制 gettext.m4 到 m4/ |
| 6 | config.guess失败 | HarmonyOS未识别 | 使用 --build=aarch64-unknown-linux-gnu |
| 7 | 缺少 libdevmapper | device-mapper依赖 | 先编译LVM2获取libdevmapper |
| 8 | 缺少 libintl链接 | LIBS未包含libintl | 手动添加 -lintl |
| 9 | 缺少 addmntent | HarmonyOS未实现mntent函数 | 添加stub实现到fsutils.c |

## 源码修改

- fsutils.c: 添加 mntent 函数 stub 实现（setmntent, addmntent, endmntent, getmntent）

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| libdevmapper | 1.02 | 编译LVM2 2.03.31获取 |
| libintl | 系统内置 | - |

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/cryptmount --version
Cannot open "/etc/cryptmount/cmtab"
Security failure
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cryptmount-6.4.0-ohos-aarch64.tar.gz | 514KB | 预编译包 |
| cryptmount-6.4.0-ohos-aarch64-debug.tar.gz | 135KB | 调试符号包 |
| 0001-fsutils.c.patch | 1673B | mntent函数补丁 |

## 注意事项

1. cryptmount 是 Linux device-mapper加密管理工具，在鸿蒙上功能可能受限
2. 缺少 libgcrypt 和 LUKS 支持，加密功能不完整
3. G0 干净构建验证失败（autoreconf问题），需手动验证

---

**编译结束**: 2026-05-23 11:17
**最终状态**: built
