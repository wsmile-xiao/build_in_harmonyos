# E327 - CMake static-only 构建必须保持安装导出的逻辑包身份稳定

## 错误特征

项目在 static-only 模式下可以完成编译和安装，但标准消费者无法按项目原有名称发现包：

```text
Could not find a package configuration file provided by "<package>"
```

另一种表现是找到了带 `-static` 或 `-shared` 后缀的 Config 文件，但该文件又 include
一个不存在的 `<package>Targets.cmake`。安装成功不能证明 CMake package export 可消费。

## 触发条件

- 构建系统同时支持 shared/static 目标，并使用一个可变名称变量驱动多个 CMake API。
- static-only 或 shared-only 分支给该变量追加 `-static`/`-shared` 后缀。
- `install(EXPORT)`、`configure_package_config_file()`、安装目录继续使用变异后的变量。
- Config 模板仍使用 `PROJECT_NAME`，或使用另一个未同步变化的包名引用 Targets/include。

## 根因分析

CMake target 名、磁盘制品名和安装包身份是三个不同概念。target 可以叫
`foo-static`，归档仍可通过 `OUTPUT_NAME` 叫 `libfoo.a`，而供消费者调用的逻辑包名
应继续是 `foo`。

若在 static-only 分支把通用 `LIBNAME` 改为 `foo-static`，后续安装图就会部分使用
`foo-static`，模板替换却仍可能使用 `PROJECT_NAME=foo`。结果是 Config、Targets、
include 根目录和 `find_package()` 名称不再组成闭合引用图。

## 解决方案

### 推荐方案

1. 引入或保留不可变的逻辑包名，例如 `PROJECT_NAME` 或独立 `PACKAGE_NAME`。
2. 只在真实 target 名和 alias 上表达变体，例如 `foo-static`、`foo::foo-static`。
3. 用 `OUTPUT_NAME foo` 保持归档名稳定，不要借此修改 package identity。
4. `install(EXPORT)`、Config/Version 生成、安装目录和 include 根目录统一使用稳定包名。
5. 安装后必须构建最小消费者，执行 `find_package(foo CONFIG REQUIRED)` 并链接导出目标。

短期无法拆分变量时，可显式指定稳定名称生成 Config/Targets；同时断言 Config 引用的
Targets 文件、include 路径和导入 target 均真实存在。

### 禁止做法

- 不要在变体分支修改后续还用于安装导出的 `LIBNAME`/`PACKAGE_NAME`。
- 不要把消费者改成 `find_package(foo-static)` 来掩盖生产者导出图错误。

## 验证

```bash
cmake -S . -B build \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON \
  -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build build
cmake --install build
cmake -S consumer -B consumer-build -DCMAKE_PREFIX_PATH="$PREFIX"
cmake --build consumer-build
ctest --test-dir consumer-build --output-on-failure
```

liquid-dsp 1.8.0 的真机对照 run
`xuguowei-liquid-dsp-issue-2206-path-b-evidence-r3-20260815-225009-42915`
使用同一份上游源码，仅改变当前补丁：

- 修复前：安装为 `liquid-staticConfig.cmake`/`liquid-staticTargets.cmake`，Config 却引用
  `liquidTargets.cmake`；标准 `find_package(liquid)` 返回 1。
- 修复后：安装为 `liquidConfig.cmake`/`liquidTargets.cmake`，导出
  `liquid::liquid-static`；最小消费者编译、链接、运行通过，runner exit 0。

## 关联条目与去重

- `E216` 处理 Conan CMakeDeps 组件元数据/头文件传播，不涉及上游 install export 身份。
- `E278` 处理条件目标缺失后裸名称退化为 `-l<name>`，不涉及 Config/Targets 命名漂移。
- 本条目聚焦上游 CMake 安装导出图的逻辑包身份稳定性，与两者可区分。
