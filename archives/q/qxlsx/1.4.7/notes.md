# QXlsx 1.4.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-25
- 编译器: clang/clang++ (15.0.4)
- 状态: built
- Qt5 版本: 5.15.2
- Conan 版本: 2.12.0

## 编译步骤

### 1. 获取源码

GitHub 直接下载超时，改用 git clone：
```bash
git clone --depth 1 --branch v1.4.7 https://github.com/QtExcel/QXlsx.git /storage/Users/currentUser/tmp/qxlsx-clone
```

手动创建 tarball：
```bash
cd /storage/Users/currentUser/tmp
tar czf qxlsx-1.4.7.tar.gz -C qxlsx-clone .
```
SHA256: `45a344edf7f59487a3d3093133dad62bd35ac18aa88403eb448d718da3bc5b85`

### 2. 手动编译

```bash
cd /storage/Users/currentUser/builds/QXlsx-1.4.7.work
mkdir build && cd build

export Qt5_DIR=/storage/Users/currentUser/usr/local/Qt5/lib/cmake/Qt5
export CMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local/Qt5

cmake ../QXlsx \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/test-install-QXlsx-1.4.7 \
  -DBUILD_SHARED_LIBS=OFF

make -j1
make install
```

产物：`libQXlsxQt5.a`（静态库）

### 3. 手动测试

```bash
# 编译测试程序
clang++ test_manual.cpp \
  -I/storage/Users/currentUser/test-install-QXlsx-1.4.7/include \
  -I/storage/Users/currentUser/usr/local/Qt5/include \
  -I/storage/Users/currentUser/usr/local/Qt5/include/QtCore \
  -I/storage/Users/currentUser/usr/local/Qt5/include/QtGui \
  -L/storage/Users/currentUser/test-install-QXlsx-1.4.7/lib \
  -L/storage/Users/currentUser/usr/local/Qt5/lib \
  -lQXlsxQt5 -lQt5Core -lQt5Gui \
  -std=c++17 -stdlib=libc++ \
  -o test_manual

# 运行测试
./test_manual
# 输出: PASS: Read A1 = "Hello QXlsx!" ... All tests passed!
```

### 4. Conan 配方验证

```bash
# 安装 Conan CLI
python3 -m pip install conan==2.12.0

# 创建 Qt5 wrapper 包
conan create /storage/Users/currentUser/tmp/qt-wrapper/conanfile.py \
  -pr:h=/storage/Users/currentUser/tmp/conan-profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/tmp/conan-profiles/ohos-aarch64 \
  --user=ohpcd --channel=stable

# 验证 QXlsx 配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify QXlsx 1.4.7
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络环境限制 | 改用 `git clone --depth 1 --branch v1.4.7` |
| 2 | conan-init 误判构建系统为 autotools | QXlsx 根目录无 CMakeLists.txt，实际在 QXlsx/ 子目录 | 手动改 conanfile.py 为 CMakeDeps/CMakeToolchain |
| 3 | Conan 2.x 包名必须小写 | Conan 2.x 限制包名为小写 | 包名改为 `qxlsx` |
| 4 | CI profile 中 `generator=Make` 无效 | Conan 2.x 不支持 `Make` 作为生成器名 | 在 conanfile.py 中显式指定 `generator="Unix Makefiles"` |
| 5 | Qt5::GuiPrivate target 不存在 | Qt5 wrapper 未导出 GuiPrivate | 移除 GuiPrivate 依赖，QXlsx 不需要 |
| 6 | 运行时 Qt5 .so 找不到 | Qt5 wrapper 缺少 runenv_info | 添加 `runenv_info` 设置 LD_LIBRARY_PATH |
| 7 | 测试程序保存到 /tmp 失败 | E002: /tmp 只读 | 测试程序改用 $TMPDIR 或 $HOME |
| 8 | Conan run() 的 env 参数类型错误 | env 应为字符串或列表，不能是 dict | 改用 `os.environ` 设置 TMPDIR，env 用 "conanrun" |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Qt5 | 5.15.2 | 本地安装 /storage/Users/currentUser/usr/local/Qt5 |
| Clang | 15.0.4 | 鸿蒙 SDK /data/service/hnp/bin/clang++ |
| CMake | 4.1.2 | 系统自带 |
| Conan | 2.12.0 | pip 安装 |

## 验证结果

```bash
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
...
qxlsx/1.4.7@ohpcd/stable (test package): Running test()
qxlsx/1.4.7@ohpcd/stable (test package): RUN: ./test_QXlsx
PASS: Read A1 = "Hello QXlsx!"
PASS: Saved to "/storage/Users/currentUser/qxlsx_test_output.xlsx"
PASS: Loaded A1 = "Hello QXlsx!"
PASS: Loaded B1 = "12345"
PASS: Loaded C1 = "3.14159"
All tests passed!
```

```bash
$ ohc-run.py conan-verify QXlsx 1.4.7
✅ 配方验证通过: QXlsx 1.4.7
✅ 可标记 status: published
```

## 注意事项

1. Conan conandata.yml 中 source URL 使用本地 `file://` URL（因 GitHub 下载超时），生产环境应替换为官方 GitHub URL
2. Qt5 wrapper 包 `qt/5.15.2@ohpcd/stable` 是系统 wrapper，指向本地安装的 Qt5
3. conanfile.py 中 `generate()` 显式指定 `generator="Unix Makefiles"` 以覆盖 CI profile 中的无效设置
4. test_package 的 test.cpp 使用 `getenv("TMPDIR")` 获取可写目录路径
5. 产物名为 `libQXlsxQt5.a`（非 libQXlsx.a），cpp_info.libs 设置为 `QXlsxQt5`

---

**编译结束**: 2026-06-25 20:38
**最终状态**: built
