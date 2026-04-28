# bzip2 — OpenHarmony 编译档案

## 软件简介
bzip2 是高压缩比数据压缩工具和库，广泛用于 Linux 生态。提供 bzip2/bunzip2/bzcat 等命令和 libbz2 库。

## OHOS 适配要点
- 简单 Makefile，使用环境变量覆盖编译器（CC=clang AR=llvm-ar RANLIB=llvm-ranlib）
- 补丁自动检测 OHOS 平台并添加 `-fPIC`
- **鸿蒙 ln -sf bug**: 必须先 rm 再 ln 创建符号链接
- 共享库需单独编译: `make -f Makefile-libbz2_so CC=clang`

## 依赖关系
- 无编译依赖
- 被依赖: Python (_bz2), tar (.tar.bz2), dpkg, rpm 等

## 参考资料
- [bzip2 官网](https://sourceware.org/bzip2/)
