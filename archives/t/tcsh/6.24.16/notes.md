# tcsh 6.24.16 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码（从 GitHub tcsh-org/tcsh release TCSH6_24_16）
2. 解压并初始化构建环境
3. 修补 config.guess 和 config.sub（使用 patch-autotools-ohos.pl）
4. 手动添加 linux-ohos* 到 config.sub kernel-os 验证列表
5. 运行 `./configure --prefix=$DEFAULT_PREFIX`
6. 修改 config.h 禁用 HAVE_SHADOW_H
7. 运行 `make -j2`
8. 运行 `make install DESTDIR=$TEST_PREFIX`
9. 运行 `make install`（安装到本地）
10. 创建预编译包 tcsh-6.24.16-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测 | 使用 patch-autotools-ohos.pl 补丁 |
| 2 | config.sub 不支持 linux-ohos 组合 | kernel-os 验证列表缺失 | 手动添加 linux-ohos* 到 case 语句 |
| 3 | getspnam 函数编译失败 | musl 不支持 shadow password 函数 | 禁用 HAVE_SHADOW_H |

## 源码修改

### acaux/config.guess
添加 HarmonyOS 系统识别分支

### acaux/config.sub
添加 ohos-linux triplet 和 linux-ohos* kernel-os 组合

### config.h
禁用 HAVE_SHADOW_H 定义（musl 不支持 shadow password 函数）

## 依赖版本

- ncurses: 预编译包（通过 configure 自动检测）
- libiconv: 预编译包

## 验证结果

```bash
$ tcsh --version
tcsh 6.24.16 (Astron) 2025-07-09 (aarch64-unknown-linux) options wide,nls,dl,al,kan,sm,rh,color,filec

$ tcsh -c 'echo "Hello"; set a=10; echo $a'
Hello
10
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tcsh-6.24.16-ohos-aarch64.tar.gz | 758KB | 预编译包（包含 bin/tcsh 和 man page） |

## 注意事项

1. tcsh 是 C shell 的增强版本，提供命令行编辑、命令补全等功能
2. musl 环境不支持 shadow password 函数，需要禁用相关功能
3. 预编译包已经正确配置，可直接安装使用

---

**编译结束**: 2026-05-26 19:37
**最终状态**: built
---

**编译结束**: 2026-05-26 19:38
**最终状态**: built
