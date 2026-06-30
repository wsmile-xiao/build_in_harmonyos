# nsync 1.30.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 源码下载：使用 codeload.github.com/google/nsync/tar.gz/1.30.0（GitHub直接下载SSL失败，用codeload替代）
2. init-build 使用 --no-download（因SSL证书问题，手动下载并解压源码到 ~/tmp/builds/）
3. cmake configure:
   ```bash
   mkdir -p build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
   ```
4. make: `make -j1` — 100% 完成，无错误
5. make install DESTDIR=$TEST_PREFIX — 成功安装到 staging 目录
6. ctest: 26/26 tests PASS（148.29秒）
7. Staging 验证: 2个静态库 + 13个头文件 + 4个CMake配置文件
8. Package: nsync-1.30.0-ohos-aarch64.tar.gz (240KB)
9. 本地安装: make install（无DESTDIR）到 $DEFAULT_PREFIX
10. 用户验证: C 和 C++ 版 nsync 均可正确链接和运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build下载失败（SSL CERTIFICATE_VERIFY_FAILED） | 鸿蒙环境SSL证书不完整 | 手动用curl -kL下载，然后init-build --no-download |
| 2 | manifest.yaml缺少build_system字段 | init-build误判为autotools | 手动添加build_system: cmake顶层字段和build.system: cmake |
| 3 | cmake提示"System is unknown to cmake" | HarmonyOS未被cmake识别为已知平台 | 不影响编译，cmake仍能正确检测pthread和完成配置 |

## 源码修改

无源码修改，nsync 1.30.0 在鸿蒙上原生编译无问题。

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- GNU Make 4.4.1
- pthread（系统自带）

## 验证结果

```bash
# C 版验证
clang -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -lnsync -lpthread test.c -o test
./test → "nsync mutex locked successfully!" / "nsync mutex unlocked successfully!"

# C++ 版验证
clang++ -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -lnsync_cpp -lpthread test.cc -o test
./test → "nsync_cpp: mutex locked!" / "nsync_cpp: mutex unlocked!"

# ctest 结果
26/26 PASS (100%), Total time: 148.29 sec
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nsync-1.30.0-ohos-aarch64.tar.gz | 240KB | 预编译包 |
| libnsync.a | 67KB | C静态库 |
| libnsync_cpp.a | 96KB | C++静态库 |
| 13个头文件 | - | nsync公共API头文件 |
| 4个CMake配置 | - | nsync/nsync_cpp Config.cmake |

## 注意事项

1. nsync是纯库项目（无bin/可执行文件），R7安全弹窗验证使用测试二进制代替
2. cmake不识别HarmonyOS平台，但编译和功能正常
3. nsync使用posix平台实现，与鸿蒙Linux内核兼容性良好
4. SSL证书问题需在init-build前解决或使用--no-download模式

**编译结束**: 2026-06-01
**最终状态**: published
---

**编译结束**: 2026-06-01 18:33
**最终状态**: published
