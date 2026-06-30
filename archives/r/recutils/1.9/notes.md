# recutils 1.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载recutils 1.9源码 (https://ftpmirror.gnu.org/recutils/recutils-1.9.tar.gz)
2. 应用补丁：sed -i 's/umask 077/umask 007/g' configure
3. ./configure --prefix=$HOME/usr/local --disable-maintainer-mode
4. make -j4
5. make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure脚本umask 077创建临时目录不可访问 | HMFS文件系统权限继承机制 | sed替换umask 077为007 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-05-27 15:39
**最终状态**: built
