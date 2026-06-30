# portable-libyaml

**libyaml** 是一个高效的 YAML 解析器和生成器库，用 C 语言实现。这是为 OpenHarmony 平台适配的 portable 版本。

## 功能概述

- **YAML 解析**：将 YAML 文档解析为内存中的数据结构
- **YAML 生成**：将内存数据结构序列化为 YAML 文档
- **流式处理**：支持增量解析和生成，适合大文件处理
- **标准兼容**：完全符合 YAML 1.1 规范

## OHOS 适配要点

### 已知问题

1. **E046 SELinux 限制（Autotools）**
   - **问题**：使用 autotools 构建时，configure 无法在当前目录创建临时文件
   - **错误**：`./config.status[980]: can't create ./confXXX/subs1.awk: Permission denied`
   - **原因**：HarmonyOS SELinux/文件系统限制
   - **解决**：使用 CMake 构建系统替代 autotools

### 构建方式

**推荐：CMake 构建**

```bash
# 1. 创建简化版 CMakeLists.txt（原版不完整）
# 2. 创建 include/config.h.in 模板
# 3. 定义 HAVE_CONFIG_H 编译宏
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_SYSTEM_NAME=OHOS \
      -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
make -j2
make install
```

**不推荐：Autotools 构建**

受 SELinux 限制，configure 阶段会失败。如需使用 autotools，需在权限宽松环境中构建。

### 验证方法

```c
#include <yaml.h>
#include <stdio.h>

int main() {
    int major, minor, patch;
    yaml_get_version(&major, &minor, &patch);
    printf("libyaml version: %d.%d.%d\n", major, minor, patch);
    return 0;
}
```

编译并运行：
```bash
clang test_yaml.c -lyaml -o test_yaml
./test_yaml
# 输出: libyaml version: 0.2.5
```

## 依赖关系

### 编译依赖
- 无外部依赖

### 运行依赖
- 无外部依赖（静态库）

## 文件产物

- `libyaml.a`：静态库（142KB）
- `yaml.h`：头文件

## 参考资料

- **官网**：https://pyyaml.org/wiki/LibYAML
- **源码仓库**：https://github.com/yaml/libyaml
- **文档**：https://pyyaml.org/wiki/LibYAMLDocumentation
- **许可证**：MIT License

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.2.5 | published | 2026-06-17 | CMake 构建成功，预编译包已生成 |

---

**注意**：此软件的 autotools 构建在当前 HarmonyOS 环境受 SELinux 限制阻塞（E046）。如遇到构建问题，请使用 CMake 构建系统。