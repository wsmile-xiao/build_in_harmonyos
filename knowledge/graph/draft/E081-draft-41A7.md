# E081: OHOS 平台 clang/lld 动态链接器路径问题

## 错误表现

在 OHOS 平台上使用 clang/lld 进行链接时，出现找不到 libxml2.so.16 的错误：

```
lld: error while loading shared libraries: libxml2.so.16: cannot open shared object file: No such file or directory
```

或者：

```
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: error while loading shared libraries: libxml2.so.16: cannot open shared object file: No such file or directory
```

## 根因分析

OHOS SDK 的 lld（链接器）被编译为动态链接到 libxml2 库，但系统的库搜索路径（LD_LIBRARY_PATH）中没有包含 OHOS SDK 的 lib 目录。

验证命令：
```bash
ldd /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld | grep libxml2
# 输出: libxml2.so.16 => not found
```

## 解决方案

### 方案 1：设置 LD_LIBRARY_PATH（推荐）

在编译前设置环境变量：

```bash
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH
```

或者在 CMake 配置时：

```bash
cmake .. -DCMAKE_LINKER=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld
LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH make -j2
```

### 方案 2：使用静态链接版本

如果 OHOS SDK 提供了静态链接的 lld 版本，可以优先使用该版本，避免动态库依赖问题。

## 受影响的软件

所有使用 OHOS SDK 进行编译的项目，尤其是在链接阶段使用 lld 的情况。

## 案例

### raylib 6.0 编译失败

在 raylib 6.0 编译过程中，CMake 配置阶段使用 clang 作为编译器，链接阶段调用 lld 时失败：

```
[  50%] Linking C shared library libraylib.so
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: error while loading shared libraries: libxml2.so.16: cannot open shared object file: No such file or directory
```

解决方法：在编译命令前设置 `LD_LIBRARY_PATH` 环境变量。

## 注意事项

- 不要将 LD_LIBRARY_PATH 直接指向 libxml2 的库目录，应指向 OHOS SDK 的 lib 目录
- 确保路径与实际安装的 SDK 版本一致（如 26.0.0.18）

## 相关原则

- P005: 环境路径正确性原则
- P006: 动态库依赖完整性原则