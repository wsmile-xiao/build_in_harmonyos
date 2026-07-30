# bzip2 1.0.8 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-14
- 编译器: clang
- 状态: built

## 编译步骤
```bash
patch -p1 < patches/0001-bzip2-1.0.8.orig-Makefile.patch
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j$(nproc)
make install PREFIX=$HOME/usr/local
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态库缺少 -fPIC | Makefile CFLAGS 无 -fPIC | 补丁自动检测 OHOS 添加 -fPIC |
| 2 | ln -sf 创建错误文件 | 鸿蒙 ln -sf bug | 当前 Conan 配方禁用 `shared=True`，避免 Makefile-libbz2_so 的符号链接逻辑在 HMDFS 上出错 |
| 3 | 共享库构建路径不稳定 | Makefile-libbz2_so 含符号链接创建逻辑，OHOS/HMDFS 对覆盖软链接有限制 | 仅支持默认静态包；如后续启用 shared=True，需先补丁化共享 Makefile 的 `rm -f && ln -s` 逻辑 |
| 4 | 官方 sourceware.org 下载返回 429 | CI 请求触发上游限流 | 使用 mirrors.kernel.org 的 sourceware 镜像，SHA256 与官方源码一致 |

## 验证结果
```bash
bzip2 --version  # ✅
bzip2 -z test.txt && bzip2 -d test.txt.bz2  # ✅
```

## 注意事项
- 鸿蒙 ln -sf bug 影响符号链接创建；当前 Conan 配方禁用 `shared=True`，仅支持默认静态包
- -fPIC 对 Python _bz2 模块编译是必要的

---

**编译结束**: 2026-07-14
**最终状态**: built
