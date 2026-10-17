# Boulder 1.02 for OpenHarmony PC

本适配保留上游 Boulder 游戏与地图编辑器，新增 ArkUI XComponent / NAPI 宿主，使用 SDL2 nativewindow 和 ohaudio 后端。

## 获取与构建

```sh
conan install --requires=boulder-game/1.02@ohpcd/stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

Conan 包内 `share/boulder/harmony-project` 是可用 DevEco Studio 打开的应用工程，包含本次配方构建的原生模块、SDK C++ 运行库和上游游戏资源。配置自己的设备调试签名，再构建安装 HAP；工程未包含签名凭据。SDK C++ 运行库的 NOTICE 位于 `licenses/ohos-native-runtime/NOTICE.txt`。

## 操作

- 首页选择 Play Boulder：Enter 开始关卡，方向键移动，R 重开。
- 首页选择 Map editor：选择图块后点击绘制，S 保存，L 重载，F3 使用 3×3 笔刷。
- Back to home 返回首页。存档与自定义地图保存在应用私有 files 目录。
- 命令行 `boulder-check assets DATA_DIR` 验证资源，`boulder-check roundtrip DATA_DIR NEW_MAP` 验证地图写入/重载。它不是图形启动器。

## 已知范围

画布为上游默认 1024×768；编辑器入口使用 `newlevel.map`，没有外部目录选择器和滚轮事件转发。游戏逻辑与编辑器复用原项目，不另写替代实现。上游没有自动测试套件，新增测试范围与实际结果见 `1.02/reports/test-report.md`。
