# nano 7.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built
- 目标架构: aarch64 (arm64)

## 编译步骤

1. 解压源码: tar xf nano-7.2.tar.xz
2. 应用补丁:
   - 0001-config-tempdir.patch: 修复configure临时目录创建
   - 0002-keydef.patch: 添加缺失的ncurses KEY定义
3. 配置: ./configure --prefix=/data/service/hnp/usr/local --disable-libmagic --disable-mouse --disable-nls --enable-utf8
4. 编译: make -j1 LDFLAGS="-L$HOME/usr/local/lib"
5. 安装: make install DESTDIR=$TEST_PREFIX LDFLAGS="-L$HOME/usr/local/lib"
6. 验证: LD_LIBRARY_PATH=$HOME/usr/local/lib nano --version

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E001 | configure临时目录创建失败 | HMDFS限制fstat/lseek对管道fd返回EACCES | 修改configure使用本地目录./.conf-temp |
| E002 | KEY_F0等定义缺失 | 预编译ncurses包缺少功能键定义 | 在definitions.h添加缺失定义 |
| E003 | 链接找不到libncursesw | 未指定库路径 | make LDFLAGS="-L$HOME/usr/local/lib" |
| E004 | 鼠标功能禁用 | ncurses无NCURSES_MOUSE_VERSION | 配置自动检测并禁用 |

## 源码修改

### 0001-config-tempdir.patch
- configure: 第603-609行，将mktemp改为本地目录
- config.status: 同样使用本地临时目录

### 0002-keydef.patch
- src/definitions.h: 添加30+个缺失的KEY定义

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| ncursesw | 6.4 | 预编译包 ~/usr/local |

## 验证结果

```bash
$ LD_LIBRARY_PATH=$HOME/usr/local/lib ~/usr/local/bin/nano --version
GNU nano, version 7.2
 (C) 2023 the Free Software Foundation and various contributors
 Compiled options: --disable-libmagic --disable-mouse --disable-nls --enable-utf8
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/nano | 1.2M | 主程序 |
| bin/rnano | symlink | 软链接 |
| share/nano/*.nanorc | ~50KB | 语法高亮配置 |

## 注意事项

1. 运行需设置LD_LIBRARY_PATH=$HOME/usr/local/lib
2. 鼠标功能不可用
3. 多语言支持不可用(仅英文)
---

**编译结束**: 2026-05-20 21:12
**最终状态**: built
