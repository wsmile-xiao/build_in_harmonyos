# E111 — qmake 构建失败：缺少 features 目录和配置文件

## 错误特征

执行 qmake 时出现以下错误：
```
Cannot find feature spec_pre.prf
Error processing project file: root.pro
```

或
```
Could not find qmake spec 'linux-clang'.
Error processing project file: root.pro
```

## 触发条件
- 构建系统: qmake (Qt 项目)
- 阶段: configure (qmake 配置阶段)
- Qt 安装: QT_HOST_DATA 路径配置不正确或 mkspecs/features 目录缺失

## 根因分析

Qt 的 qmake 需要以下文件才能正常工作：
1. mkspecs 目录（包含平台规格文件，如 linux-clang/qmake.conf）
2. features 目录（包含 .prf 特性文件，如 spec_pre.prf）
3. 正确的 QT_HOST_DATA 配置（指向包含上述文件的目录）

当前系统中：
- QT_HOST_DATA 设置为 `/storage/Users/currentUser/usr/local/lib`
- mkspecs 实际位于 `/storage/Users/currentUser/usr/local/mkspecs`
- features 目录完全缺失

这种不完整的 Qt 安装导致 qmake 无法定位必要的配置文件。

## 解决方案

### 推荐方案：手动编译 qmake 项目

由于 Qt 安装不完整，无法使用 qmake，需要手动执行以下步骤：

1. **生成 Flex/Bison 文件**
   ```bash
   cd src/
   bison -v -d -o parser.cpp datalang.y
   flex -o tokens.cpp datalang.l
   ```

2. **编译源文件**
   ```bash
   export IODATA_VERSION=19.14  # 根据版本设置
   clang++ -std=c++14 -fPIC \
     -I/storage/Users/currentUser/usr/local/include \
     -I/storage/Users/currentUser/usr/local/include/QtCore \
     -DQT_CORE_LIB \
     -c *.cpp
   ```

3. **创建共享库**
   ```bash
   clang++ -shared -o libiodata-qt5.so.0.$IODATA_VERSION *.o \
     -L/storage/Users/currentUser/usr/local/lib \
     -lQt5Core \
     -Wl,-rpath,/storage/Users/currentUser/usr/local/lib
   ```

4. **创建符号链接**
   ```bash
   ln -sf libiodata-qt5.so.0.$IODATA_VERSION libiodata-qt5.so
   ln -sf libiodata-qt5.so.0.$IODATA_VERSION libiodata-qt5.so.0
   ```

5. **安装到 DESTDIR**
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/include/iodata-qt5
   cp -a libiodata-qt5.so* $TEST_PREFIX/$DEFAULT_PREFIX/lib/
   cp *.h $TEST_PREFIX/$DEFAULT_PREFIX/include/iodata-qt5/
   ```

### 禁止做法
- ❌ 不要尝试重新配置 QT_HOST_DATA（可能破坏现有 Qt 安装）
- ❌ 不要尝试从 cmd-pkgs 安装完整 Qt（可能不兼容或无可用包）
- ❌ 不要跳过 flex/bison 生成步骤（直接编译会失败）

## 验证
```bash
# 检查 Qt 安装状态
qmake -query QT_HOST_DATA
find $QT_HOST_DATA -name "mkspecs" -type d
find $QT_HOST_DATA -name "features" -type d
find $QT_HOST_DATA -name "spec_pre.prf"

# 验证手动编译成功
ls src/libiodata-qt5.so*
file src/libiodata-qt5.so.0.19.14
llvm-strip src/libiodata-qt5.so.0.19.14
```

## 关联条目
- 相关: E007 (平台不识别)
- 相关: E046 (chmod 不生效 - 可能与 Qt 安装问题相关)
- 前置: Qt5Core 必须已安装并通过 ELF 签名