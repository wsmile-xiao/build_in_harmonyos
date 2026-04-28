# bzip2 1.0.8 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2024-03-20
- 编译器: clang
- 状态: success

## 编译步骤
```bash
patch -p1 < patches/0001-bzip2-1.0.8.orig-Makefile.patch
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j$(nproc)
make -f Makefile-libbz2_so CC=clang
make install PREFIX=$HOME/usr/local
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态库缺少 -fPIC | Makefile CFLAGS 无 -fPIC | 补丁自动检测 OHOS 添加 -fPIC |
| 2 | ln -sf 创建错误文件 | 鸿蒙 ln -sf bug | 先 `/bin/rm -f` 再 `/bin/ln -s` |
| 3 | 共享库未编译 | 默认只编译静态库 | 单独 `make -f Makefile-libbz2_so` |

## 验证结果
```bash
bzip2 --version  # ✅
bzip2 -z test.txt && bzip2 -d test.txt.bz2  # ✅
```

## 注意事项
- 鸿蒙 ln -sf bug 影响符号链接创建
- -fPIC 对 Python _bz2 模块编译是必要的
