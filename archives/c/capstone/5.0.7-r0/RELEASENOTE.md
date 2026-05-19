# Release Notes — capstone 5.0.7-r0

**发布日期**: 2026-05-09  
**版本**: 5.0.7-r0  
**平台**: OpenHarmony aarch64  

## 概述

capstone 是一个轻量级、多平台、多架构的反汇编框架。本版本为 OpenHarmony 平台的预编译包。

## 版本信息

- **上游版本**: 5.0.7
- **修订版本**: r0
- **构建系统**: autotools
- **编译器**: GCC (OpenHarmony)

## 新特性

这是 capstone 5.0.7 在 OpenHarmony 平台的首次预编译发布。

### capstone 5.0.7 主要特性

- 支持多种架构：ARM, ARM64, Mips, PowerPC, Sparc, SystemZ, X86, XCore 等
- 提供稳定的 C API
- 支持 Python、Java、 OCaml 等多种语言绑定
- 优化的反汇编引擎

## 预编译包内容

### 文件列表

```
usr/
├── include/
│   └── capstone/
│       ├── arm.h
│       ├── arm64.h
│       ├── capstone.h
│       ├── m680x.h
│       ├── mips.h
│       ├── platform.h
│       ├── ppc.h
│       ├── sparc.h
│       ├── systemz.h
│       ├── tms320c64x.h
│       ├── x86.h
│       └── xcore.h
└── lib/
    ├── libcapstone.a
    └── pkgconfig/
        └── capstone.pc
```

### 安装方法

1. 下载预编译包：`capstone-5.0.7-r0-ohos-aarch64.tar.gz`
2. 解压到目标目录
3. 运行安装脚本：`sh install-capstone-5.0.7-r0.sh`

或使用一键安装：
```bash
tar xzf capstone-5.0.7-r0-ohos-aarch64.tar.gz
cd capstone-5.0.7-r0-ohos-aarch64
sh install-capstone-5.0.7-r0.sh
```

## 质量保证

### 编译验证

- ✅ G1 二进制完整性：PASS
- ✅ G2 功能可用性：PASS
- ✅ G3 可移植性：PASS
- ✅ G4 归档完整性：PASS

### 依赖关系

无外部依赖（静态库版本）。

## 已知限制

1. 本预编译包为静态库版本（libcapstone.a）
2. 需要运行时链接 OpenHarmony 标准 C 库
3. Python/Java 绑定需要单独编译

## 使用示例

```c
#include <capstone/capstone.h>

int main() {
    csh handle;
    cs_insn *insn;
    size_t count;
    
    if (cs_open(CS_ARCH_X86, CS_MODE_64, &handle) != CS_ERR_OK) {
        return -1;
    }
    
    // 反汇编代码
    count = cs_disasm(handle, code, code_size, address, 0, &insn);
    
    // 使用反汇编结果...
    
    cs_free(insn, count);
    cs_close(&handle);
    
    return 0;
}
```

编译命令：
```bash
gcc -o myapp myapp.c -lcapstone -I$HOME/usr/local/include -L$HOME/usr/local/lib
```

## 技术支持

- 上游项目：https://github.com/capstone-engine/capstone
- 文档：https://www.capstone-engine.org/
- OpenHarmony 编译记录：本归档目录

## 更新历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 5.0.7-r0 | 2026-05-09 | 初始版本，OpenHarmony aarch64 预编译包 |

---

**构建者**: OpenHarmony Compile Agent  
**构建系统版本**: v7.4  
**归档路径**: archives/c/capstone/5.0.7-r0/