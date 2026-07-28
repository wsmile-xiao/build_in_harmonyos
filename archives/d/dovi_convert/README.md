# dovi_convert

## 简介
dovi_convert 是 cryptochrome 开发的 Dolby Vision Profile 7 -> 8.1 转换工具，用于将 UHD 蓝光 rip 的 Dolby Vision Profile 7 MKV 文件转换为 Profile 8.1，以确保在不支持 Enhancement Layer 的设备上正确播放。工具会先分析文件的 FEL 复杂度，只转换安全文件，并保留动态元数据。

## 命令
- **scan** — 分析当前目录或指定文件/目录的 DoVi 状态
- **convert** — 转换单个文件或目录（批处理模式）
- **inspect** — 检查单个文件的详细信息
- **backup** — 备份 Dolby Vision 增强层到 .dovi 文件
- **restore** — 从 .dovi 备份和转换后的文件恢复完整 DoVi 7.1 文件
- **cleanup** — 清理备份文件
- **update-check** — 检查上游更新
- **help** — 显示帮助

## OHOS 适配
- **构建系统**: 无（单文件 Python 3 CLI 脚本）
- **shebang**: 脚本使用 `#!/usr/bin/env python3`，OHOS 上 python3 在 PATH 中可用，无需 patch
- **安装**: 将 `dovi_convert.py` 重命名为 `dovi_convert` 安装到 `bin/`，保留可执行位
- **无编译**: 纯 Python 脚本，无 C 编译，arch 无关

## 依赖
- **运行时**: python3 (>= 3.8)
- **外部工具**（通过 subprocess 调用，非 Conan 依赖）:
  - ffmpeg
  - dovi_tool (https://github.com/quietvoid/dovi_tool)
  - mkvtoolnix (mkvmerge, mkvextract)
  - mediainfo
- **测试**: bash（运行 test_package 烟雾测试）

## 安装产物
- bin/dovi_convert — 主可执行脚本（从 dovi_convert.py 重命名）
- licenses/LICENSE — GPL-3.0 许可证

## 功能验证
```bash
dovi_convert help
dovi_convert scan /path/to/media
dovi_convert convert Movie.mkv
dovi_convert backup Movie.mkv
dovi_convert restore Movie.mkv
```

## 参考
- GitHub: https://github.com/cryptochrome/dovi_convert
- 文档: https://docs.doviconvert.com
- v8.2.0 Release: https://github.com/cryptochrome/dovi_convert/releases/tag/v8.2.0
