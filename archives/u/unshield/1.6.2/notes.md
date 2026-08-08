# unshield 1.6.2 适配笔记

## 编译信息

- **软件**: unshield 1.6.2
- **构建系统**: CMake
- **源码**: GitHub (https://github.com/twogood/unshield)
- **依赖**: zlib/1.3.1.1（-fPIC 静态库，因 libunshield.so 为共享库，静态 libz 须含 PIC）
- **难度**: low

## 构建步骤

```bash
cmake -DUSE_OUR_OWN_MD5=ON -DOPENSSL_ROOT_DIR='' .
make -j$(nproc)
make install DESTDIR=$DESTDIR
```

## 产物

| 产物 | 路径 |
|------|------|
| libunshield.so | lib/libunshield.so.1.6.2 |
| unshield | bin/unshield |
| unshield-deobfuscate | bin/unshield-deobfuscate |
| libunshield.h | include/libunshield.h |
| libunshield.pc | lib/pkgconfig/libunshield.pc |
| unshieldConfig.cmake | lib/cmake/unshield/ |

## 注意事项

1. 上游有 29 个 CTest 集成测试用例（test/ 目录），需要 .cab 测试数据文件，CI 中可通过 BUILD_TESTING=ON 启用
2. OpenSSL 为可选依赖，使用内建 MD5 避免额外依赖
3. 非系统同名库，动态链接策略（R26 不适用）
4. 需要在 CI worker 上进行 ELF 签名
5. zlib 须用 1.3.1.1（-fPIC 静态库），否则链进 libunshield.so 时报 R_AARCH64 relocation 错误
6. **补丁 0001-fix-rpath-soname**: HarmonyOS CMake 使用相对路径作为 DT_NEEDED（如 ../lib/libunshield.so），违反 E207 模式。补丁移除 src/CMakeLists.txt 中 CMAKE_INSTALL_RPATH 的绝对路径覆盖，改用 $ORIGIN/../lib 相对 RPATH；同时在 lib/CMakeLists.txt 中显式设置 SONAME 以绕过 CMake 对未知平台（HarmonyOS）的 SONAME 支持缺失问题