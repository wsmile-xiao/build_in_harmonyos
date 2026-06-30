# easyrpg-player

EasyRPG Player 是一个开源的 RPG Maker 2000/2003 游戏播放器。

## 描述
EasyRPG Player 可以在多个平台上运行 RPG Maker 2000 和 2003 制作的游戏，无需修改游戏文件。它使用 SDL2 作为图形后端。

## 版本列表
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.8.1.1 | built | 2026-06-03 | 当前版本 |

## 依赖
- SDL2（图形界面）
- liblcf（游戏文件解析）
- inih（INI 配置解析）
- pixman（像素操作）
- expat（XML 解析）
- freetype（字体渲染）
- vorbis（音频解码）

## 补丁说明
当前版本无补丁。

## 安装方法
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- easyrpg-player 0.8.1.1
```

## 验证安装
```bash
~/usr/local/bin/easyrpg-player --version
# 输出: EasyRPG Player 0.8.1.1 (2026-06-03)
```

## 使用方法
运行 RPG Maker 游戏：
```bash
easyrpg-player --game-path /path/to/game
```

## 遇到的问题
1. Pixman 依赖缺失 → 通过预编译包安装
2. Pixman 库文件符号链接缺失 → 手动创建
3. 预编译包打包脚本问题 → 手动打包

## 平台限制
- 需要 ELF 签名才能执行
- 需要设置 LD_LIBRARY_PATH 或使用公共安装脚本

## 更多信息
- 官网: https://easyrpg.org/
- GitHub: https://github.com/EasyRPG/Player