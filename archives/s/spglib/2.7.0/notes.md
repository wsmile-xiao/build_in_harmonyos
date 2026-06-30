# spglib 2.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤（生产版本，不含测试）

```bash
source .build-context-spglib-2.7.0
cd $BUILD_SRC_DIR && mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DSPGLIB_WITH_TESTS=OFF -DSPGLIB_SHARED_LIBS=OFF -DCMAKE_SYSTEM_NAME=OHOS
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 编译步骤（测试版本，用于ctest）

```bash
source .build-context-spglib-2.7.0
cd $BUILD_SRC_DIR && rm -rf build && mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DSPGLIB_WITH_TESTS=ON -DSPGLIB_SHARED_LIBS=OFF -DCMAKE_CXX_FLAGS="-fno-rtti" -DFETCHCONTENT_TRY_FIND_PACKAGE_MODE=ALWAYS -DCMAKE_SYSTEM_NAME=OHOS
make -j1
ctest --output-on-failure  # 45/45 PASS, 18.27 sec
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败导致源码下载失败 | 鸿蒙环境缺少CA证书 | 手动curl -kL下载后用--no-download模式 |
| 2 | cmake不识别HarmonyOS平台 | CMake缺少HarmonyOS平台定义 | 仅输出警告不影响编译，添加-DCMAKE_SYSTEM_NAME=OHOS |
| 3 | GTest RTTI不兼容（typeinfo undefined） | 预编译GTest(libgtest.a)编译时用了-fno-rtti | 测试代码添加-DCMAKE_CXX_FLAGS="-fno-rtti"匹配GTest ABI |
| 4 | FetchContent无法git clone GTest | 网络无法连接github.com | 用FETCHCONTENT_TRY_FIND_PACKAGE_MODE=ALWAYS优先find_package |
| 5 | GTest安装路径嵌套错误 | 之前DESTDIR安装导致双重嵌套 | 从嵌套路径复制到正确位置 |
| 6 | G0 clean-verify脚本不支持cmake | 脚本默认执行./configure | 创建hints/build-hints.yaml指定构建系统为cmake |

## 源码修改

无补丁。spglib是纯C库，cmake配置直接支持Release编译，无需修改源码。

## 依赖版本

- 无必需依赖

## 验证结果

### ctest 真实执行输出（45/45 PASS, 18.27 sec）

完整输出详见 reports/test-report.md

### 自定义C功能验证程序

```bash
$ ~/tmp/test_spglib
spglib version: 2.7.0
spglib version full: 2.7.0
spglib commit: 12355c77fb7c505a55f52cae36341d73b781a065
Number of symmetry operations: 192
Space group number: 225
International symbol: Fm-3m
Hall number: 523
PASS: Symmetry detection works (spacegroup=225)
All basic tests completed successfully.
```

### pkg-config验证

```bash
$ PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig pkg-config --modversion spglib
2.7.0
$ PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig pkg-config --libs spglib
-L/storage/Users/currentUser/usr/local/lib -lsymspg
$ PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig pkg-config --cflags spglib
-I/storage/Users/currentUser/usr/local/include
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libsymspg.a | 1956420 B | 静态库 |
| spglib.h | 26405 B | 头文件 |
| spglib.pc | 173 B | pkg-config文件 |
| SpglibConfig.cmake | 2880 B | cmake配置文件 |
| SpglibConfigVersion.cmake | 2762 B | cmake版本配置文件 |
| SpglibTargets_static.cmake | 4532 B | cmake目标文件 |
| SpglibTargets_static-release.cmake | 841 B | cmake目标(release)文件 |
| PackageCompsHelper.cmake | 23209 B | cmake辅助组件 |

预编译包: spglib-2.7.0-ohos-aarch64.tar.gz (1980KB)

## 注意事项

1. spglib是纯C库（libsymspg.a），测试框架GTest是C++，需要-fno-rtti兼容已安装的GTest
2. 纯库打包时使用SPGLIB_WITH_TESTS=OFF避免GTest依赖
3. cmake平台不识别HarmonyOS仅产生警告，不影响编译结果；添加-DCMAKE_SYSTEM_NAME=OHOS可消除警告
4. 需要cmake >= 3.25（spglib CMakeLists.txt要求）
5. 无源码补丁，build_cleanliness: minimal（仅需--prefix+DESTDIR，无需--build/--host）

---

**编译结束**: 2026-06-12
**最终状态**: published