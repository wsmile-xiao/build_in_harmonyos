# breeze-grub

KDE Breeze 的 GRUB 引导菜单主题。本归档交付 HarmonyOS 可安装、读取和迁移的资源包。

## 资源与使用

- `share/grub/themes/breeze/`：原版 theme.txt、12 张 PNG、3 个 PF2 字体、SVG 源文件和许可证旁注，共 23 个文件。
- `licenses/`：7 份上游许可证正文和 REUSE.toml。
- Conan `cpp_info.resdirs` 与运行环境变量 `BREEZE_GRUB_THEME_DIR` 指向完整主题目录。

```sh
conan install --requires=breeze-grub/6.7.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

本地尚未发布时，应先从版本目录执行 `conan create`；上述命令使用本地缓存或已发布的制品。Conan 消费者可以通过 `VirtualRunEnv` 获取 `BREEZE_GRUB_THEME_DIR`，或从依赖的 `cpp_info.resdirs` 定位资源。复制或分发主题时须保留整个目录及许可证。

## HarmonyOS 适配

主题资源不依赖 CPU 架构，不生成 C/C++ 库，不需要 Qt、KDE 或 GRUB 作为打包依赖。上游随包提供预生成字体，开发者工具 `mkfont.sh` 所需的 grub-mkfont/Unifont 不参与安装。

交付范围为资源包。实际引导菜单显示仍需要使用 GRUB 的启动环境；本配方不安装 GRUB、不修改系统启动配置，也不将资源检查等同于引导画面验证。

消费者测试验证资源内容及引用，并在 OHOS SDK 编译的程序中执行完整主题复制、重命名、重新读取。原生 OHOS CI 支持 clang/CMake 和签名工具；开发机可通过 HDC 在虚拟机运行同一消费者。版本目录 notes.md 记录实测平台与命令。

## 上游

- 项目：https://invent.kde.org/plasma/breeze-grub
- 正式发布：https://download.kde.org/stable/plasma/6.7.2/
- 许可证：按各文件 SPDX 标记，保留上游 LICENSES 与 REUSE 元数据。
