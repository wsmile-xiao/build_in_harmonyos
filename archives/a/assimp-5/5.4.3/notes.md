# assimp-5 5.4.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-22
- 编译器: clang/clang++ (OHOS SDK 15, /data/service/hnp/bin/clang)
- 状态: built

## 编译步骤

1. 下载上游源码（GitHub releases v5.4.3.tar.gz，sha256 已写入 conandata.yml）。
2. 在 `archives/a/assimp-5/5.4.3/` 下放置：
   - `conanfile.py`（裸 cmake + ohos.toolchain.cmake 注入 + 跑上游 gtest + 跑 test_package）
   - `conandata.yml`（上游 URL + sha256 + 1 个 OHOS 补丁）
   - `patches/0001-ohos-tmp-path.patch`（重定向 TMP_PATH，规避 OHOS /tmp 只读）
   - `test_package/{conanfile.py,test.cpp,MANIFEST.yml}`（21 项鸿蒙特有断言）
3. 运行 `conan create . -pr:h=default -pr:b=default --build=missing`，recipe 内 build() 顺序为：
   - `apply_conandata_patches(self)`（应用 TMP_PATH 补丁）
   - `cmake -B build-ohos -S . -DCMAKE_TOOLCHAIN_FILE=$OHOS_NDK_HOME/build/cmake/ohos.toolchain.cmake ...`
   - `cmake --build build-ohos`
   - `cmake --build build-ohos --target unit`（编上游 gtest 二进制）
   - `cd build-ohos/bin && ./unit`（跑上游 577 个用例，要求 100% 通过）
   - `cmake --install build-ohos --prefix $package_folder`
   - `_sign_binaries()`：dlopen 真机要求 .so 已用 `binary-sign-tool sign -selfSign 1` 签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `llvm-ranlib` 找不到导致 `Error running link command: no such file or directory` | OHOS SDK llvm/bin 只有 llvm-ar，无 llvm-ranlib | `_llvm_ranlib()` 用 `shutil.which("llvm-ranlib")` 兜底，注入 `-DCMAKE_RANLIB=...` |
| 2 | `find_package(ZLIB)` 在交叉链下找不到制品仓里的 zlib | ohos.toolchain 把 sysroot 外路径全过滤掉 | 直接预置 `-DZLIB_INCLUDE_DIR=...`、`-DZLIB_LIBRARY=...` cache 变量绕开 find |
| 3 | 真机 dlopen 报 "Permission denied" | conan install 复制 .so 时破坏链接器自签 | `_sign_binaries()` 用 `binary-sign-tool` 重新签名 |
| 4 | `cmake --build --target unittest` 报 unknown target | assimp 5.4.3 测试可执行文件叫 `unit` 不是 `unittest` | 改用 `--target unit` |
| 5 | 上游 utDefaultIOStream.FileSizeTest 报 `mkstemp` 返回 -1 | OHOS 6.0 把 `/tmp` 挂成只读，mkstemp 失败 | 打 patch `0001-ohos-tmp-path.patch`，把 `TMP_PATH "/tmp/"` 改 `TMP_PATH "./"` |
| 6 | 上游 utD3MFImporterExporter.import3MFFromFileTest 报 "No suitable reader found" | 复制 6.0.5 recipe 时把 `-DASSIMP_BUILD_3MF_IMPORTER=OFF` 也带过来（5.4.3 真的认）| 删除该选项；3MF 是内置实现，无外部依赖 |

## 源码修改

1 个补丁：`patches/0001-ohos-tmp-path.patch`（修改 `test/unit/UnitTestFileGenerator.h`，把 `TMP_PATH "/tmp/"` 改成 `TMP_PATH "./"`）。该文件仅被 gtest 引用，不影响生产代码。

## 依赖版本

- zlib: 1.3.1.1（制品仓静态库，被静态链接进 libassimp.so）

## 验证结果

```bash
$ conan create archives/a/assimp-5/5.4.3 -pr:h=default -pr:b=default --build=missing
...
======== Testing the package ========
...
[==========] 577 tests from 115 test suites ran. (13769 ms total)
[  PASSED  ] 577 tests.          ← 上游 gtest 100%
...
[ok] aiGetVersionMajor() == 5   ← test_package 100%
...
assimp 5.4.3: 全部断言通过
```

测试用例 (test_probe, 21 项断言):
1. aiGetVersionMajor() == 5
2. aiGetVersionMinor() == 4
3. aiGetVersionPatch() == 3
4. ReadFileFromMemory 解析 OBJ（正方形）成功
5. 网格数 = 1
6. 面数 = 2（两个三角形）
7. 顶点数 = 4（JoinIdenticalVertices 后去重）
8. 所有顶点 z = 0（平面正方形）
9. 包围盒尺寸 = 1×1
10. 每个面都是 3 个索引（Triangulate 生效）
11. 法线 buffer 指针安全
12. ReadFileFromMemory 解析 OBJ（单三角形）成功
13. 三角形顶点数 = 3
14. 三角形面数 = 1
15. 三角形索引数 = 3
16. 垃圾输入不产生有效网格
17. GetErrorString 可调用（非 null）
18. dlopen libassimp.so 成功
19. dlsym(aiGetVersionMajor) 命中
20. dlopen 出来的 aiGetVersionMajor() = 5
21. dlsym(Assimp::Importer::ReadFileFromMemory) 命中（mangled 名 _ZN6Assimp8Importer18ReadFileFromMemoryEPKvmjPKc）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libassimp.so | ~80MB（含 contrib/ 静态代码） | 主库，已签名 |
| libassimp.so.5 | 软链 | 版本化软链（指向 .so） |
| include/assimp/*.h | 完整头文件 | C/C++ API |
| cmake/assimp-5.4.3/*.cmake | cmake config | find_package(assimp) 支持 |
| lib/pkgconfig/assimp.pc | pkg-config | pkg_check_modules(assimp) 支持 |

## 注意事项

- `assimp-5/5.4.3` 与 `assimp/6.0.5` 共存制品仓时，先用 `conan remove assimp-5/5.4.3 -f` 清掉旧 build dir 再重 build；否则 cmake 缓存可能引用旧 toolchain 文件
- 真机测试时 `LD_LIBRARY_PATH` 不需要显式设：test_package 已通过 `-Wl,-rpath,$(libdir)` 把 libassimp.so 路径嵌进 test_probe
- 5.x 的 API 与 6.x 兼容：测试程序可以直接复用 6.0.5 模板，只需把版本断言从 6 改成 5

---
**编译结束**: 2026-08-22
**最终状态**: built
