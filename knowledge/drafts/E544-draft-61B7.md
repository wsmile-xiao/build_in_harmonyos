# E544 — Ubuntu cmake-extras 的 GSettings/Intltool CMake 模块在 OHOS 缺失

## 错误特征

cmake configure 阶段失败或告警，日志含：

```
FindGSettings.cmake not found
GSettings: not found
intltool not found
```

或 `CMake Error: Could not find module FindGSettings.cmake`。

## 触发条件

- 构建系统: cmake
- 阶段: configure

## 根因分析

上游（Ayatana 系软件，如 libayatana-common）依赖 Ubuntu 私有包
`cmake-extras` 提供的 GSettings / Intltool CMake 模块（`FindGSettings.cmake`、
`Intltool.cmake`）。OHOS 平台没有该发行版包，configure 阶段找不到这些模块
即失败。其中 `po/`（翻译）子目录依赖 Intltool 模块，属可选功能，不应阻断
主库构建。

## 解决方案

### 推荐方案

1. 在 `cmake/` 提供最小 `FindGSettings.cmake` shim，声明
   `org.ayatana.common` GSettings schema 的安装逻辑（替换 cmake-extras）。
2. 将 `po/` 翻译子目录做成可选：`find_package(Intltool)` 找到才
   `add_subdirectory(po)`，否则跳过，不阻断主构建。
3. configure + 构建双验证：

```bash
cmake -S . -B build -DENABLE_TESTS=OFF -DENABLE_WERROR=OFF
cmake --build build
```

### 禁止做法

- ❌ 空壳跳过整个 `data/`/schema 安装——会安装不了
  `org.ayatana.common` gschema，破坏 GSettings 消费者。
- ❌ 把 `po/` 无条件当作硬依赖——OHOS 无 intltool 时主库无法构建。

## 验证

```bash
cmake -S . -B build -DENABLE_TESTS=OFF && cmake --build build
ls build/data/org.ayatana.common.gschema.xml
```

## 关联条目

- 相关: E543（新建文件补丁头）
