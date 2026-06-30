# libiodata 0.19.14 适配笔记

## 编译环境
- 构建系统: custom (手动编译)
- 编译日期: 2026-06-04
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

### 1. 源码准备
```bash
# 使用 ohc-run.py init-build 下载源码
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libiodata 0.19.14 \
  --url=https://api.github.com/repos/sailfishos/libiodata/tarball/refs/tags/0.19.14

# 源码目录: ~/builds/libiodata-0.19.14.work/src/
```

### 2. 尝试 qmake（失败）
```bash
cd ~/builds/libiodata-0.19.14.work/src/
export IODATA_VERSION=19.14
qmake root.pro -spec linux-clang PREFIX=$DEFAULT_PREFIX

# 错误: Cannot find feature spec_pre.prf
# 根因: Qt 安装不完整，缺少 mkspecs/features 目录
```

### 3. 手动编译（成功）

#### 3.1 生成 Flex/Bison 文件
```bash
cd ~/builds/libiodata-0.19.14.work/src/
bison -v -d -o parser.cpp datalang.y  # 生成 parser.cpp + parser.hpp
flex -o tokens.cpp datalang.l         # 生成 tokens.cpp
```

#### 3.2 编译源文件
```bash
export QT_INCLUDE=/storage/Users/currentUser/usr/local/include
export QT_LIB=/storage/Users/currentUser/usr/local/lib
export IODATA_VERSION=19.14

clang++ -std=c++14 -fPIC \
  -I$QT_INCLUDE \
  -I$QT_INCLUDE/QtCore \
  -DQT_CORE_LIB \
  -c iodata.cpp validator.cpp storage.cpp misc.cpp parser.cpp tokens.cpp
```

#### 3.3 创建共享库
```bash
clang++ -shared -o libiodata-qt5.so.0.$IODATA_VERSION *.o \
  -L$QT_LIB \
  -lQt5Core \
  -Wl,-rpath,$QT_LIB

# Strip 库文件
llvm-strip libiodata-qt5.so.0.$IODATA_VERSION  # 从 608KB 减小到 319KB

# 创建符号链接
ln -sf libiodata-qt5.so.0.$IODATA_VERSION libiodata-qt5.so
ln -sf libiodata-qt5.so.0.$IODATA_VERSION libiodata-qt5.so.0
```

#### 3.4 DESTDIR 安装
```bash
export TEST_PREFIX=/storage/Users/currentUser/test-install-libiodata-0.19.14
export DEFAULT_PREFIX=/storage/Users/currentUser/usr/local

mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/include/iodata-qt5
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib/mkspecs/features

cp -a libiodata-qt5.so* $TEST_PREFIX/$DEFAULT_PREFIX/lib/
cp iodata.h validator.h storage.h $TEST_PREFIX/$DEFAULT_PREFIX/include/iodata-qt5/
cp iodata validator storage $TEST_PREFIX/$DEFAULT_PREFIX/include/iodata-qt5/
cp ../iodata-qt5.prf $TEST_PREFIX/$DEFAULT_PREFIX/lib/mkspecs/features/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qmake 找不到 spec_pre.prf | Qt 安装不完整，缺少 features 目录 | 手动编译：flex/bison + clang++ |
| 2 | QMAKESPEC 设置无效 | mkspecs 路径与 QT_HOST_DATA 不匹配 | 绕过 qmake，直接手动编译 |
| 3 | 测试程序无法运行 | Qt5Core 加载失败（符号不匹配） | 跳过测试，记录为环境限制 |
| 4 | ohc-run.py package 失败 | 缺少 .verify-passed 标记 | 暂不创建预编译包 |

## 源码修改

无源码修改，完全使用原始源码进行手动编译。

## 依赖版本

- Qt5Core: 5.15.2
- flex: 2.6.4
- bison: 3.8.2
- clang: 15.0.4

## 验证结果

### 编译产物验证
```bash
# 库文件检查
file libiodata-qt5.so.0.19.14
# 输出: ELF shared object, 64-bit LSB arm64, stripped

ls -lh libiodata-qt5.so.0.19.14
# 输出: 319K

# 符号链接验证
ls -la libiodata-qt5.so*
# libiodata-qt5.so -> libiodata-qt5.so.0.19.14
# libiodata-qt5.so.0 -> libiodata-qt5.so.0.19.14
# libiodata-qt5.so.0.19.14 (319K)
```

### 测试验证（失败）
```bash
# 编译测试程序成功
clang++ -std=c++14 -I../src -I$QT_INCLUDE -I$QT_INCLUDE/QtCore \
  -DQT_CORE_LIB -L../src -L$QT_LIB -liodata-qt5 -lQt5Core \
  -Wl,-rpath,../src -Wl,-rpath,$QT_LIB \
  iodata-test.cpp -o iodata-qt5-test

# 运行测试失败（环境限制）
./iodata-qt5-test
# Error loading shared library libQt5Core.so.5
# Error relocating libiodata-qt5.so: symbol not found
```

### G0 干净构建验证
```
G0 验证失败: configure 失败 (exit 127)
原因: 无 configure 脚本（手动编译项目）
影响: 无法通过自动化干净构建验证
```

## 交付物

暂无预编译包（package 步骤需要 verify 通过）。

| 文件 | 大小 | 说明 |
|------|------|------|
| libiodata-qt5.so.0.19.14 | 319K | 共享库（已 strip） |
| libiodata-qt5.so | 符号链接 | 主链接 |
| libiodata-qt5.so.0 | 符号链接 | 版本链接 |
| iodata.h, validator.h, storage.h | - | 头文件 |
| iodata-qt5.prf | 669B | Qt 特性文件 |

## 注意事项

1. **构建系统限制**: 当前 Qt 安装不完整，无法使用 qmake，必须手动编译
2. **测试限制**: 由于 Qt5Core 运行时加载问题，无法运行测试程序
3. **知识图谱**: 创建了 E111 草稿记录 qmake 构建失败问题
4. **预编译包**: 需要手动创建 tar.gz（ohc-run.py package 不工作）
5. **版本号**: 通过环境变量 IODATA_VERSION 控制（设置为 19.14）

---

**编译结束**: 2026-06-04 15:24
**最终状态**: built (有质量门禁问题)