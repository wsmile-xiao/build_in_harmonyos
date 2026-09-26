# rply — PLY 文件格式读写 C 库

`rply` 是一个 ANSI C 库，让应用程序读写 **PLY**（Polygon File Format，斯坦福三角网格格式）文件。PLY 常用于存储三维几何信息（如 3D 模型），也可用于其他需要「元素 + 属性」结构的场景。

## 主要功能

- 打开/创建 PLY 文件（ASCII、二进制大端/小端）
- 读取文件头：遍历元素（element）与属性（property）的名称、类型、实例数
- 以回调方式读取标量/列表属性值
- 通过 API 逐项写出元素与属性，生成 PLY 文件
- 支持注释（comment）与对象信息（obj_info）

## OHOS 适配要点

- **上游无构建系统**：源码包只有 `rply.c`、`rply.h`、`rplyfile.h`（以及 `etc/` 下的示例程序与 HTML 手册），没有任何 Makefile/CMake。本配方直接编译 `rply.c` 为静态库。
- **零依赖**：只使用 C 标准库，不需要 libm 或任何第三方库。
- **产物形态**：静态库 `librply.a` + 两个公共头文件 `rply.h`、`rplyfile.h`；属于库，不含命令行工具。

## 产物

| 路径 | 说明 |
|------|------|
| `include/rply.h` | 公共 API 头文件 |
| `include/rplyfile.h` | 内部/扩展头文件（随上游发布） |
| `lib/librply.a` | 静态库 |

## 参考资料

- 上游主页：<https://w3.impa.br/~diego/software/rply/>
- 上游仓库：<https://github.com/diegonehab/rply>
- 许可证：MIT
