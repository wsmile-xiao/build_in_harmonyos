# bgrep

二进制 grep — 在文件中搜索二进制/十六进制字符串。

类似于 grep，但用于搜索二进制模式而非文本模式。支持十六进制搜索（如 `deadbeef`）、通配符搜索（`??` 代表匹配任意一字节）、标准输入和目录递归搜索。

## 用法

```bash
bgrep <hex> [<path> [...]]
```

### 示例

```bash
# 在文件中搜索 DEADBEEF
bgrep deadbeef firmware.bin

# 使用通配符（匹配任意一字节）
bgrep de??be firmware.bin

# 从标准输入搜索
cat data.bin | bgrep fffe

# 递归搜索目录
bgrep aabbccdd /path/to/dir
```

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.2 | published | 2026-06-18 |

## 软件信息

- 源码: https://github.com/tmbinc/bgrep
- 许可证: BSD
- 语言: C
- 构建系统: makefile（极简 Makefile）
- 依赖: 无（仅依赖标准 C 库 / musl libc）
- 编译器: clang 15.0.4
- 适用平台: OpenHarmony aarch64
