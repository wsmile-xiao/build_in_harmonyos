# Boulder 1.02 HarmonyOS PC 适配

## 上游与范围

- 上游：https://github.com/rh-galaxy/boulder
- 固定提交：`7bdb085f6da06c0f201ed20c957ae47ac92eae51`。
- 官方源码 SHA256：`bea4550dea38577d7ab069ec6816e9adc2236423f2f01852d6e30ef2223eeedf`。
- 上游程序标题声明版本为 Boulder v1.02；没有用提交日期虚构发行版本。
- 根目录 `license.txt` 声明代码与数据为 Public Domain；保留 PortAudio 和静态链接 SDL2 的许可证。
- 当前实际使用的 121 个上游源码、PortAudio/Vorbis 源码及游戏资源文件，已逐字节与固定官方归档核对，一致。
- 本归档只涉及 Boulder 游戏及其原有地图编辑器，不涉及 Curtain。

## 适配实现

原项目通过 SDL2 创建桌面窗口。赛事已发布的 SDL2 2.32.10 提供 nativewindow 后端，
但需要应用的 Surface ID，且该后端不能直接把 ArkUI 输入事件转换成 SDL 事件。
新增 ArkUI XComponent 宿主和 NAPI 接口，提供 Surface、渲染线程生命周期和键鼠/触摸转发。
游戏逻辑、渲染、音频、关卡和地图编辑继续使用原 C++ 实现，没有另写替代游戏。

`harmony/game_runner.cpp` 和 `editor_runner.cpp` 使用原有 C_Game/C_Editor，
适配工作线程退出和应用可写目录。游戏与编辑器编译为独立、隐藏 C++ 符号的原生模块，
避免两个上游同名 C_World/C_Object 类型发生符号冲突。

唯一修改的原有源码是 `src/common/input.cpp`：读取转发事件中的鼠标坐标。
原因是 SDL_PushEvent 不更新 SDL_GetMouseState 的内部坐标。F1-F12、方向键、
修饰键、Page/Home/End、数字小键盘均转发；窗口组件失焦时释放按下状态。
资源由 HAP rawfile 解包到 files/data，存档、成绩与 newlevel.map 在应用 files 目录。

CMake 从源码构建两个原生模块和 boulder-check。赛事 Conan 工具链的系统名为
HarmonyOS，而 DevEco 工具链为 OHOS，构建兼容两者。未伪造平台宏或链接 Linux 库。
Conan 成品内的 share/boulder/harmony-project 包含实际构建的模块、ArkUI 页面和资源；
消费者配置自己的调试签名后即可构建 HAP。没有包含账号、密码、证书、私钥或设备签名。

## 已执行验证

- 探索 HAP 在赛事真机原生窗口显示游戏菜单；Enter 进入关卡，右方向键使角色右移。
- 用户明确确认菜单背景音乐可听见。
- 原有地图编辑器可显示和绘制；S 保存，修改后按 L 重载恢复保存内容。
- force-stop 后重新启动应用，再次打开编辑器，已保存钻石仍在。
- F3 切换为 3×3 笔刷，真机点击绘制得到 3×3 区域。
- 真机 CTest：assets、map-roundtrip、missing-assets 全部通过。
- assets 实际调用原图像/地图加载器、SDL WAV 解码和原 Vorbis 解码器，
  处理 14 张图片、25 个关卡、18 个 WAV 音效、1 个 Ogg 音乐文件。
- map-roundtrip 使用原编辑器代码验证尺寸、参数、描述、钻石、带参数的钥匙和边界。

上游无自动测试套件：检查完整官方源码、build/linux/Makefile 及测试文件清单，
Makefile 有 all/utils/clean/install，无 check/test 目标；SDL_test*.h 是依赖头文件。
新增的 CTest 属于适配回归测试，不能称为“上游官方完整测试”。消费者测试执行成品
boulder-check，不以打印版本号或检查文件存在替代实际功能测试。

## 当前限制与构建说明

原生画布保持上游默认 1024×768 像素。当前宿主编辑 newlevel.map，游戏仍按上游逻辑
枚举应用 files 下的自定义地图。没有提供导入任意外部目录的文件选择器。
SSH 进程没有原生应用 Surface，图形游戏通过 HAP 启动；boulder-check 是资源和地图
验证工具，不是图形启动器。自动测试不替代实际画面、输入和听感验证。

初次 init-build 错误地将 build/linux 提升为源码根。已保留错误目录备份，从同一
官方归档恢复完整 .orig/.work；正式补丁必须由官方 refresh-patch --auto 生成。
2026-09-20 清洁 Conan create 与 test_package 通过。实际 Conan 成品生成签名 HAP 后真机复验通过：菜单、Enter 进入关卡、Right 移动、游戏→首页→编辑器→首页→游戏，同一进程持续运行。编辑器仍读取此前保存的钻石地图。
补充打包 SDK libc++_shared.so 到 HAP 私有库目录，并保留 native/NOTICE.txt，解决应用命名空间无法加载系统 C++ 库的问题。未将调试签名加入源码归档。
Conan 验证工具未解析到 package ID，L2/L4/L5 自动步骤因此跳过，不能将跳过当作实际测试；消费者测试和成品 HAP 复验实际执行。
---

**编译结束**: 2026-09-20 16:41
**最终状态**: built
