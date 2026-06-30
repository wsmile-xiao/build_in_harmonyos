# id3lib 3.8.3 — 鸿蒙系统预编译包

## 简介

id3lib 是一个用于操作 MP3 音频文件中 ID3v1 和 ID3v2 标签的 C++ 库。它提供了完整的标签读取、写入、修改和删除功能，同时附带四个命令行工具。

- **版本**: 3.8.3
- **许可证**: LGPL-2.0+
- **源码地址**: https://sourceforge.net/projects/id3lib/files/id3lib/3.8.3/id3lib-3.8.3.tar.gz
- **构建系统**: autotools
- **编程语言**: C/C++
- **预编译包**: id3lib-3.8.3-ohos-aarch64.tar.gz

## 功能特性

- ID3v1 和 ID3v2 标签的完整读写支持
- Unicode（UTF-8/UTF-16）标签支持
- 标签格式转换（v1 ↔ v2）
- 标签删除（strip）
- C++ API 和 C 包装器 API
- zlib 压缩标签支持

## 命令行工具

| 工具 | 功能 | 示例 |
|------|------|------|
| **id3info** | 查看 MP3 文件标签信息 | `id3info song.mp3` |
| **id3tag** | 写入/修改 MP3 标签 | `id3tag --artist="歌手" --song="歌名" song.mp3` |
| **id3convert** | 转换或删除标签 | `id3convert -1 song.mp3` (仅保留v1标签) |
| **id3cp** | 复制标签 | `id3cp source.mp3 dest.mp3` |

## 安装说明

```bash
# 通过 cmd-pkgs 公共安装脚本安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- id3lib 3.8.3

# 安装后验证
id3info --version   # 应输出: id3info 3.8.3
```

## 库文件

- **静态库**: `~/usr/local/lib/libid3.a`
- **头文件目录**: `~/usr/local/include/id3/`
  - `id3.h` — 主头文件
  - `tag.h` — 标签操作核心接口
  - `field.h` — 字段操作
  - `misc_support.h` — 辅助功能
  - `globals.h` — 全局定义
  - `id3lib_strings.h` — 字串类型定义
  - `id3lib_streams.h` — 流类型定义

## 编译链接

```cpp
// C++ 示例代码
#include <id3/tag.h>

int main() {
    ID3_Tag myTag("song.mp3");
    myTag.Add(ID3_Frame(ID3FID_LEADARTIST));
    // ...操作标签
    return 0;
}
```

编译命令:
```bash
clang++ your_code.cpp -I~/usr/local/include -L~/usr/local/lib -lid3 -lz -o your_program
```

## 鸿蒙适配说明

id3lib 3.8.3 是 2003 年发布的软件，在鸿蒙系统上编译需要以下适配修复：

1. **config.guess/config.sub**: 不识别 HarmonyOS 平台，已添加 OHOS 三元组支持
2. **iomanip.h 检查**: 现代 C++ 已弃用 `<iomanip.h>`，已从 configure 中移除该检查
3. **iostream.h**: 部分头文件使用弃用的 `<iostream.h>`，已替换为 `<iostream>`
4. **main() 签名**: 部分示例程序使用 `unsigned int argc`，已修正为 `int argc`

所有修复以补丁形式提供，位于 `archives/i/id3lib/3.8.3/patches/` 目录下。

## 已知限制

- 本预编译包仅提供静态库（libid3.a），不提供动态库（.so）
- id3lib 无自带正式测试套件，功能验证通过手动测试完成
- 示例测试程序 test_io.cpp 存在 C++ 兼容性问题，但不影响核心库功能