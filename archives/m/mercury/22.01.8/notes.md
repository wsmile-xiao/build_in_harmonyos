# Mercury 22.01.8 编译笔记

## 编译环境
- 目标平台: HarmonyOS (aarch64-unknown-linux-ohos)
- 编译器: clang
- Grade: hlc.gc.pregen (禁用多 grade 编译)
- 并行度: -j2

## 应用的补丁

### 0001-fix-tmpdir.patch
修改 config.status，将 mktemp 临时目录从当前目录改为 `/storage/Users/currentUser/tmp`，
解决 HMDFS 文件系统安全标签限制无法在当前目录创建临时文件的问题。

### 0002-fix-gcconfig-h.patch
修改 `boehm_gc/include/private/gcconfig.h`，为 AARCH64 Linux 平台使用 `SEARCH_FOR_DATA_START`
替代 `DATASTART_IS_ETEXT`，解决 HarmonyOS 缺少 `__data_start` 符号导致的链接错误。

## 编译选项
```bash
./configure --prefix=/storage/Users/currentUser/usr/local \
    --with-cc=clang \
    --disable-most-grades \
    --disable-shared-libs

make -j2
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-mercury-22.01.8
```

## 已知问题
1. GC Warning: "Failed to find PT_GNU_RELRO segment" - 无害警告
2. make check 需要 configure 重新运行 - 非关键
3. 需要设置 TMPDIR 环境变量

## 验证
- mercury_compile --version: ✓
- 编译 hello.m: ✓
- 运行 hello: ✓ 输出 "Hello, Mercury on HarmonyOS!"
