# clamav-libunrar

ClamAV 内嵌的 RAR 解包库（UnRAR 解码器），为 ClamAV 扫描器提供 RAR 压缩包解析能力。
本适配将其作为独立 Conan 包提供，上游来源为 ClamAV 单体源码树中的 `libclamunrar/` 子目录。

## 功能概述

- RAR 压缩包解包（UnRAR 6.24 解码核心）
- 公共 C API（`dll.hpp`）：`RAROpenArchive` / `RAROpenArchiveEx` / `RARReadHeader` /
  `RARProcessFile` / `RARCloseArchive` / `RARGetDllVersion`
- 自包含 C++ 实现，无第三方运行时依赖

## OHOS 适配要点

### 构建方式
- **构建系统**：CMake，但仅配置 `libclamunrar/` 子目录（`cmake.configure(build_script_folder=.../libclamunrar)`），
  避开顶层单体构建对 Rust 工具链、Libcheck、python pytest 的强依赖
- **父变量补齐**：独立配置时显式传入 `ENABLE_SHARED_LIB/ENABLE_STATIC_LIB`、
  `LIBCLAMAV_VERSION=12.0.3`、`LIBCLAMAV_SOVERSION=12`、`CMAKE_INSTALL_LIBDIR=lib`
- **SONAME**：CMake 无 HarmonyOS 平台模块，OHOS 下沿用 azure-core-cpp 的 SONAME flag 守卫
- **头文件**：上游只安装库目标，配方手工复制 `dll.hpp` + `raros.hpp` 到 `include/`

### 已知限制
- 上游 `libclamunrar/` 无独立测试套件（见 `test_package/MANIFEST.yml` 审计），功能验证由
  test_package 真实调用 UnRAR C API 完成
- `libclamunrar_iface`（ClamAV 胶水层，需完整 libclamav 头文件）不在本包范围内

## 依赖关系

### 编译依赖
无（仅 libc/libc++）

## 编译版本

| 版本 | 状态 | 日期 | 产物 |
|------|------|------|------|
| 1.4.5 | built | 2026-09-09 | lib/libclamunrar.a（默认静态），include/dll.hpp、include/raros.hpp |

## 使用示例
```cpp
#include "raros.hpp"
#include "dll.hpp"

int main() {
    if (RARGetDllVersion() != RAR_DLL_VERSION) return 1;
    RAROpenArchiveDataEx data{};
    char name[] = "sample.rar";
    data.ArcName = name;
    data.OpenMode = RAR_OM_LIST;
    HANDLE hArc = RAROpenArchiveEx(&data);
    if (data.OpenResult != ERAR_SUCCESS) return 1;
    RARCloseArchive(hArc);
    return 0;
}
```

```cmake
find_package(clamav-libunrar REQUIRED)
target_link_libraries(app clamav-libunrar::clamunrar)
```

## 许可证
- GPL-2.0-only（ClamAV 主体许可证；内嵌解码器另带 UnRAR freeware 条款，见包内 `licenses/license.txt`）
