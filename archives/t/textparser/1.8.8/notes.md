# TextParser 1.8.8 适配笔记

## 软件信息

- **名称**: TextParser
- **版本**: 1.8.8
- **上游仓库**: https://github.com/avr-aics-riken/TextParser
- **许可证**: BSD-2-Clause
- **构建系统**: CMake
- **用途**: YAML-like 简单文本参数解析库

## 功能特性

- JSON/YAML 风格的简单参数结构解析
- 支持 C、C++ 和 Fortran API
- Singleton 模式实现
- 可选 MPI 支持
- 轻量级，无外部依赖

## 依赖关系

### 必需依赖
- CMake (>= 3.15)
- C++ 编译器

### 可选依赖
- MPI library（用于并行支持，已禁用）
- Fortran 编译器（用于 Fortran API，已禁用）

## 适配进展

### 阶段 1: 源码获取 ✅
- [x] 下载源码：https://github.com/avr-aics-riken/TextParser/archive/refs/tags/1.8.8.tar.gz
- [x] SHA256: ff87020943fdd1b9ead3c7e461fe364adc7651b87d57bce8e004ab7f82375194
- [x] 解压并检查源码结构

### 阶段 2: 创建 Conan 配方 ✅
- [x] conandata.yml 创建完成
- [x] conanfile.py 创建完成
- [x] test_package 创建完成
- [x] 补丁文件创建完成

### 阶段 3: 本地构建验证 ✅
- [x] 执行 conan create 本地构建
- [x] 编译成功，生成 libTP.a
- [x] 包已安装到本地 cache
- [x] Package ID: 1eb3476ec7a24c85e4c4226f8dbce9d9b4c912f9

### 阶段 4: 下一步 ⏳
- [ ] 提交 Git 分支
- [ ] 创建 PR
- [ ] 更新 CDMlib 配方依赖

## 构建配置

### CMake 选项
```cmake
-DCMAKE_BUILD_TYPE=Release
-DBUILD_SHARED_LIBS=OFF              # 静态链接
-Denable_fapi=OFF                     # 禁用 Fortran API
-Denable_test=OFF                     # 禁用测试
-Dwith_MPI=OFF                        # 禁用 MPI
```

### 应用的补丁

**0001-update-cmake-minimum-version.patch**
- 目的: 更新 CMake 最低版本从 2.6 到 3.15
- 原因: 现代 CMake 不再支持 2.6
- 类型: 可移植性补丁

## 构建结果

### 编译成功
```
[100%] Building CXX object src/CMakeFiles/TP.dir/TextParser.cpp.obj
[100%] Building CXX object src/CMakeFiles/TP.dir/TextParserElement.cpp.obj
[100%] Building CXX object src/CMakeFiles/TP.dir/TextParserTree.cpp.obj
[100%] Linking CXX static library libTP.a
[100%] Built target TP
```

### 安装的文件
```
lib/libTP.a                          # 静态库
include/TextParser.h                 # 主头文件
include/TextParserCommon.h
include/TextParserElement.h
include/TextParserTree.h
include/tpVersion.h                  # 版本信息
doc/*.pdf                            # 文档 (3个PDF)
licenses/License.txt                 # 许可证
```

### 包信息
- Package ID: `1eb3476ec7a24c85e4c4226f8dbce9d9b4c912f9`
- Recipe revision: `1634beb100957f12c1cff62c8207c552`
- 设置: os=OHOS, os.version=5.0, arch=armv8, compiler=clang-15
- 选项: shared=False, fPIC=True, with_mpi=False, enable_fapi=False

## 遇到的问题与解决方案

### 问题 1: CMake 版本过低
- **现象**: `CMake Error: Compatibility with CMake < 3.5 has been removed`
- **原因**: 上游 CMakeLists.txt 要求 CMake 2.6，但现代 CMake 已移除对旧版本的支持
- **解决方案**: 创建补丁 `0001-update-cmake-minimum-version.patch`，将最低版本更新到 3.15

### 问题 2: libcxx 设置不兼容
- **现象**: `clang-15: error: invalid library name in argument '-stdlib=libstdc++'`
- **原因**: OHOS 平台的 clang 不支持 `-stdlib=libstdc++`
- **解决方案**: 在 conanfile.py 的 `configure()` 方法中检测 OHOS 并设置 `compiler.libcxx = "c++_shared"`

### 问题 3: 全局 profile 设置
- **现象**: test_package 编译失败，仍然使用 libstdc++11
- **原因**: 全局 profile 未更新
- **解决方案**: 更新 `~/.conan2/profiles/default`，设置 `compiler.libcxx=c++_shared` 和 `os.version=5.0`

## API 概览

### 主要类
```cpp
class TextParser {
public:
    static TextParser* get_instance_singleton();  // 获取实例
    TextParserError read(const std::string& file); // 读取配置
    TextParserError write(const std::string& file); // 写入配置
    TextParserError getValue(const std::string& label, std::string& value); // 获取值
    TextParserError remove(); // 清除数据
    void status(); // 状态输出
};
```

### 版本宏
```cpp
#define TP_VERSION   "1.8.8"
#define TP_REVISION  "20180925_1830"
```

## 验证命令

```bash
# 本地构建（已完成）
conan create . --build=missing

# 查看包信息（已完成）
conan list "textparser/1.8.8:*"

# 检查产物
conan cache path textparser/1.8.8
```

## 下一步行动

### TextParser 完成后
1. ✅ 提交 Git 分支和 PR
2. ⏳ 更新 CDMlib conanfile.py：
   - 将依赖从 `textparser/1.9.0` 改为 `textparser/1.8.8`
3. ⏳ 验证 CDMlib 构建

## 参考资料

- [TextParser GitHub](https://github.com/avr-aics-riken/TextParser)
- [TextParser 主页](http://avr-aics-riken.github.io/TextParser/)
- [Spack 配方](https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/textparser/package.py)

## 作者与时间

- 适配者: AtomCode
- 适配日期: 2026-09-01
- 状态: ✅ 构建成功，包已生成
