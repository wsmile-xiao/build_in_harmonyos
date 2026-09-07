# ocrad 0.29 适配笔记

## 基本信息
- 软件：ocrad (GNU Ocrad - Optical Character Recognition program)
- 版本：0.29
- 上游仓库：https://ftp.gnu.org/gnu/ocrad/ocrad-0.29.tar.lz
- 构建系统：custom configure (非标准 autotools，自定义 shell configure)
- 语言：C++
- 作者：Antonio Diaz Diaz

## 编译参数
```bash
./configure --prefix=$DEFAULT_PREFIX \
  CXX=clang++ \
  CXXFLAGS="-fPIC -O2" \
  CPPFLAGS="-I<libpng_include> -I<zlib_include>" \
  LDFLAGS="-L<libpng_lib> -L<zlib_lib>" \
  LIBS="-lpng -lz"
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 依赖
- libpng (1.6.58.2 from conan ohpcd registry, shared library)
- zlib (1.3.2 from conan ohpcd registry, static library)

## 平台适配
- 无需平台补丁
- configure 脚本为自定义实现，非标准 autoconf，不需要 config.guess/config.sub
- 源码无平台特定代码需要修改
- libpng 为动态链接 (.so)，zlib 为静态链接 (.a)

## 测试
- make check: ✅ tests completed successfully (需设置 LD_LIBRARY_PATH 指向 conan 缓存中的 libpng lib 目录)

## 构建产物
- bin/ocrad (可执行文件)
- lib/libocrad.a (静态库)
- include/ocradlib.h (头文件)

## 注意事项
- 源码包格式为 .tar.lz (lzip 压缩)，需要手动下载解压
- 系统缺少 install 命令，使用 wrapper 脚本替代
- 运行时需要 LD_LIBRARY_PATH 包含 libpng.so 所在目录
---

**编译结束**: 2026-09-04 11:53
**最终状态**: built
