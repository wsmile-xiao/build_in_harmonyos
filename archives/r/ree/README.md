# ree — BIOS ROM 扩展 / VGA 字体提取器

`ree` 是一个从 PC 固件中提取 **ROM 扩展**的小工具；随包还提供 `fontdump`，用于从显卡 BIOS ROM 中提取 VGA 字体。

## 主要功能

- **`ree`**：以 512 字节为步长扫描系统内存 `0xc0000`–`0xf0000`，识别 ROM 扩展标志 `55 aa`，按标志后的长度字节计算大小（×512）并保存为 `<地址>.rom`。需要读取 `/dev/mem`（通常需 root）。
- **`fontdump`**：扫描一个 ROM 文件，识别 8×8 / 8×14 / 8×16 的 VGA 字体图案（字符 0 与 255 为全 0 的签名），并分别导出为 `8x8.fnt` / `8x14.fnt` / `8x16.fnt`，可用于 `setfont` 等控制台字体设置。

## OHOS 适配要点

- **手写 makefile**：无 `configure`，`make -f makefile CC=clang CFLAGS="-O2 -Wall"` 即可；上游仓库另有一份 CMake 生成的 `Makefile`，但不使用。
- **零依赖**：仅使用 C 标准库。
- **运行时权限**：`ree` 依赖 `/dev/mem`；在无读权限时会按设计打印 `could not open /dev/mem` 并退出。`fontdump` 是纯文件工具，便于功能测试。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/ree` | ROM 扩展提取器 |
| `bin/fontdump` | VGA 字体提取器 |
| `share/man/man8/ree.8`、`share/man/man1/fontdump.1` | man 手册 |
| `share/doc/ree/README.md` | 上游说明 |

## 参考资料

- 上游仓库：<https://github.com/alexmyczko/ree>
- 许可证：GPL-2.0-or-later
