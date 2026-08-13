# libzmf 0.0.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 状态: built (conan-verify 通过，待 CI upload 后升 published)

## 编译步骤

1. `./configure --prefix=... --disable-shared --enable-static --disable-tests --without-docs --without-icu`
2. `make -j1 CXXFLAGS="-fPIC -O2 -DZMF_NO_ICU"`
3. `make install DESTDIR=$STAGING` (staging 验证通过)
4. `conan create` (conan-verify G1-G4 + L2/L4/L5 全部 PASS)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不识别 OHOS | config.guess/config.sub 太旧 (2013) | 补丁 0001/0002 升级到 2023 版 (E007) |
| 2 | configure umask 创建子目录失败 | HMDFS 拒绝 700 权限 mktemp 子目录 | 补丁 0003 umask 077→022 (E046) |
| 3 | 链接缺 ucnv_open/ucnv_close/ucnv_getNextUChar | libzmf_utils.cpp 硬依赖 ICU | 补丁 0004 ZMF_NO_ICU 宏下用 Latin-1 passthrough 替代 |
| 4 | librevenge .la 文件 dependency_libs 引用 //lib/ | conan 占位符 prefix=/ | build() 中修复 .la 文件路径 |
| 5 | zlib 版本冲突 (1.3.1 vs 1.3.1.1) | librevenge 要 1.3.1，libpng 要 1.3.1.1 | librevenge 升级到 zlib/1.3.1.1 (兼容) |
| 6 | cpp_info.libs 库名不匹配 | conan 期望库名不含 lib 前缀 | cpp_info.libs = ["zmf-0.0"] |
| 7 | test_package SEGFAULT | test.cpp 传 nullptr 给 isSupported() | 改用空 RVNGStringStream |

## 源码修改

| 补丁文件 | 修改内容 |
|---------|---------|
| 0001-config.guess.patch | config.guess 升级到 2023 版识别 OHOS (E007) |
| 0002-config.sub.patch | config.sub 升级到 2023 版支持 OHOS triplet (E007) |
| 0003-configure.patch | configure umask 077→022 修复 HMDFS 权限 (E046) |
| 0004-src-lib-libzmf_utils.cpp.patch | ICU fallback: ZMF_NO_ICU 宏下用 Latin-1 passthrough |

## 依赖版本

- librevenge/0.0.5 (zlib 升级到 1.3.1.1)
- boost/1.90.0.3 (header-only)
- libpng/1.6.58
- zlib/1.3.1.1 (传递依赖)

## 验证结果

```
conan-verify: G1-G4 + L2/L4/L5 全部 PASS
status: built (可标记 published)
```

## 注意事项

- ICU 在 OHOS worker 不可用，用 ZMF_NO_ICU + Latin-1 passthrough 替代。ASCII 文本完整保留，非 ASCII 字节映射到 U+00xx。
- librevenge/0.0.5 的 zlib 依赖从 1.3.1 升级到 1.3.1.1 以解决与 libpng 的版本冲突（patch release，同 ABI，test 通过）。

---

**编译结束**: 2026-08-08
**最终状态**: built
