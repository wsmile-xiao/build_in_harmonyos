# E322 — qsb 宿主工具需 LD_LIBRARY_PATH

## 错误特征

```
qsb: error while loading shared libraries: libQt6ShaderTools.so.6:
  cannot open shared object file: No such file or directory
# 或交叉编译场景:
qsb: Error relocating ...: symbol not found
```

## 触发条件

- 构建系统: cmake
- 阶段: compilation（构建期宿主工具执行）
- 适用: 使用 Qt Shader Baker（qsb）预编译 shader 的 Qt 6 子模块
  （qtmultimedia、qtquick3d 等）

## 根因分析

qsb 是构建期运行的宿主工具，动态链接 `libQt6ShaderTools`/`libQt6Core`。
这些库位于 conan 缓存依赖包（qtbase/qtshadertools）的 lib 目录，不在系统
默认搜索路径；OHOS 无 RPATH 兜底时，运行 qsb 必然报找不到符号。

## 解决方案

### 推荐方案

conan 配方 build() 用 `cmake -E env` 注入依赖包 lib 路径后执行构建：

```
cmake -E env LD_LIBRARY_PATH=<qtbase lib>:<qtshadertools lib> \
  cmake --build <build_dir>
```

### 禁止做法

- ❌ 把 qsb 二进制拷贝进本包 bin/（宿主工具不属于目标包产物）
- ❌ 依赖系统全局 LD_LIBRARY_PATH（CI 环境不可控）

## 验证

```bash
LD_LIBRARY_PATH=<qtbase lib>:<qtshadertools lib> qsb --version
# 正常打印版本号即已修复
```
