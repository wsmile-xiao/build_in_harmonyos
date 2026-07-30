# Picat

Picat 是一个简单而强大的逻辑型多范式编程语言，面向通用应用。Picat 是基于规则的语言，融合了显式非确定性、显式统一、函数、列表推导、约束和表化等声明式语言特性。

## 版本信息

- 当前版本: 3.9.7 (Picat version 3.9#7)
- 许可证: MPL-2.0
- 主页: https://picat-lang.org

## OpenHarmony 适配要点

- musl libc 兼容性: 替代 `fdes->_fileno` 为标准 POSIX `fileno()` 函数（`__OHOS__` 守卫）
- 自定义 Makefile.ohos 适配 clang/OpenHarmony 编译
- 无外部依赖（自包含 espresso/kissat/fann 子项目）
- -DGCC 宏必须保留（启用 computed goto 等 GCC 扩展，clang 兼容）
- -DM64BITS 宏必须保留（64-bit 类型定义）

## 安装说明

预编译包解压后包含:
- `bin/picat` — 可执行二进制
- `share/picat/lib/*.pi` — 26 个库模块

非预加载模块需要设置 `PICATPATH` 环境变量指向 lib 目录。

## 功能验证

已验证通过的功能: 算术运算、函数定义、列表操作、math模块、大整数运算、字符串操作、成员判断、os模块、planner/util模块导入、命令行目标执行(-g)、预编译包独立安装
