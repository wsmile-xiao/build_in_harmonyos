# autoconf-archive 2024.10.16 — 适配笔记

## 平台
- 目标: OpenHarmony (aarch64, musl libc)
- 构建系统: autotools (纯 M4 宏集合，无 C 代码)

## 编译步骤
1. 应用 1 个补丁 (configure: HMDFS umask fix)
2. `./configure --prefix=$PREFIX`
3. 创建 dummy makeinfo stub (texinfo 不可用，跳过 doc 构建)
4. `make -j1` (doc 构建通过 dummy makeinfo)
5. `make install DESTDIR=$STAGING` (586 个 ax_*.m4 宏文件安装)

## 关键信息
- 总共安装 586 个 ax_*.m4 宏文件 (共 591 个文件)
- 安装路径: $PREFIX/share/aclocal/
- autoconf 可通过 `aclocal` 自动发现这些宏

## 已知限制
- texinfo (makeinfo) 不可用，使用 dummy stub 创建空 info 文件
- doc/stamp-vti 和 doc/version.texi 原始内容正常，无需修改

## 验证
```
$ ls $PREFIX/share/aclocal/ | wc -l
594
$ ls $PREFIX/share/aclocal/ax_*.m4 | wc -l
586
```

## Conan 适配
- package_type: build-scripts
- 无 libs（纯数据包）
- resdirs: ["share"] (暴露 aclocal 目录)
- buildenv_info: ACLOCAL_PATH 指向 share/aclocal/
---

**编译结束**: 2026-08-09 05:07
**最终状态**: built
