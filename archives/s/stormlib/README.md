# StormLib

StormLib是一个开源库，用于读取和操作暴雪游戏（如《魔兽争霸III》、《星际争霸II》、《暗黑破坏神III》等）的MPQ档案格式。

## 软件信息

- **官方网站**: https://github.com/ladislav-zezula/StormLib
- **最新版本**: 9.25 (稳定版)
- **许可证**: MIT License
- **构建系统**: CMake

## 功能特性

- 读取MPQ档案文件
- 创建和修改MPQ档案
- 支持多种压缩算法：zlib、bzip2、LZMA、PKWARE
- 支持强数字签名验证
- 跨平台支持（Windows、Linux、macOS）

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 9.25 | built | 2026-06-17 | 首次编译，静态库 |

## 依赖关系

StormLib内部集成了以下依赖库（源码内嵌）：
- zlib (内嵌版本)
- bzip2 (内嵌版本)
- libtomcrypt (内嵌版本)
- libtommath (内嵌版本)

编译时无需额外依赖，但可选链接系统版本的zlib和bzip2。

## 使用说明

### 安装

预编译包可通过cmd-pkgs公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- stormlib 9.25
```

### 使用

在项目中引用StormLib：
```c
#include <StormLib.h>

// 接时需要: -lstorm
```

编译你的项目时需要链接：
```bash
gcc your_program.c -lstorm
```

### API示例

```c
// 打开MPQ档案
HANDLE hMpq = NULL;
if(SFileOpenArchive("path/to/archive.mpq", 0, 0, &hMpq))
{
    // 提取文件
    SFileExtractFile(hMpq, "file.txt", "output.txt", 0);

    // 关闭档案
    SFileCloseArchive(hMpq);
}
```

## 相关资源

- [API文档](https://github.com/ladislav-zezula/StormLib/wiki)
- [MPQ格式规范](https://github.com/ladislav-zezula/StormLib/wiki/MPQ-Format)
- [示例代码](https://github.com/ladislav-zezula/StormLib/tree/master/test)

## 编译注意事项

- StormLib默认编译为静态库（libstorm.a）
- 内嵌的依赖库避免了外部依赖冲突
- 使用CMake构建系统，支持标准的`cmake .. && make && make install`流程