# pcalc 3 — 适配笔记

> 档案创建时间: 2026-07-13
> 最后更新: 2026-07-20
> 状态: pending

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | pcalc |
| 版本 | 3.0.0 |
| 状态 | ⏳ pending |
| 构建系统 | Makefile |
| 源码路径 | https://github.com/vapier/pcalc/archive/refs/tags/v3.tar.gz |
| 依赖 | flex, bison (仅构建时) |

## 二、适配过程

### Phase 1: 环境准备
- [x] 源码下载解压
- [x] 目录结构创建

### Phase 2: 编译适配
- [x] Conan 配方编写（conanfile.py）
- [x] conandata.yml 配置
- [x] test_package 创建

### Phase 3: 问题修复
- [x] 修复 package_info：pcalc 是工具不是库，移除 libs 设置
- [x] 添加 tool_requires：flex/bison 作为构建依赖
- [x] 源码解压配置：strip_root=True
- [x] 修复并行构建竞态：`make -jN` 下 bison 尚未生成 `pcalc.h` 就编译了 `symbol.o`/`pcalcl.o`，报 `fatal error: 'pcalc.h' file not found`。新增 `0002-Makefile-fix-parallel-build-pcalc-h-race.patch`，将 `pcalc.c: pcalc.y` 改为分组目标 `pcalc.c pcalc.h &: pcalc.y`，并让所有 `#include "pcalc.h"` 的 `.o` 依赖 `pcalc.h`。

## 三、关键技术点

### 1. 工具 vs 库的区分
pcalc 是可执行文件，不是库。Conan 配方中：
- ❌ 错误：`self.cpp_info.libs = ["pcalc"]`
- ✅ 正确：`self.cpp_info.bindirs = ["bin"]`

### 2. 构建依赖处理
flex 和 bison 是构建时需要的工具，使用 `tool_requires` 声明：
```python
def build_requirements(self):
    self.tool_requires("flex/2.6.4")
    self.tool_requires("bison/3.8.2")
```

### 3. Makefile 构建
直接调用 make 命令：
```python
def build(self):
    self.run("make -j$(nproc)")
```

## 四、文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| conanfile.py | ✅ | Conan 配方 |
| conandata.yml | ✅ | 源码 URL + SHA256 |
| manifest.yaml | ✅ | 版本元数据 |
| commands.json | ✅ | 命令定义 |
| README.md | ✅ | 功能说明文档 |
| notes.md | ✅ | 本文件 |
| test_package/ | ✅ | Conan L1 测试 |

## 五、待办事项

- [ ] 实际编译测试（需要 gcc/flex/bison 环境）
- [ ] 生成预编译包
- [x] 提交 PR（文件格式已修复）

## 六、知识沉淀

1. **pcalc 是工具**：命令行计算器，不是库
2. **依赖极少**：仅需 flex/bison 构建
3. **Makefile 构建**：无 configure 脚本
4. **多进制支持**：hex/dec/oct/bin 混合运算
