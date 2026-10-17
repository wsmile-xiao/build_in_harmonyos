# Boulder 1.02 测试报告

## 环境与来源

OpenHarmony PC aarch64 真机，Clang 15.0.4，Conan 2.29.1，SDL2 2.32.10，SDK 26.0.0.18。
固定上游提交 `7bdb085f6da06c0f201ed20c957ae47ac92eae51`。上游无自动测试套件，统计为 0；以下属于新增适配回归测试。

## 自动测试

- CTest 3/3：assets、map-roundtrip、missing-assets。
- Conan test_package 1/1：运行已安装的验证工具、资源解码、地图保存重载、缺资源负例及原生模块/运行库/许可证检查。
- 实际资源覆盖：14 张图、25 地图、18 WAV 音效、1 Vorbis 音乐。
- 地图断言覆盖尺寸、参数、描述、钻石、钥匙参数、边界。
- 缺资源负例预期输出 `FAIL: asset directory does not exist` 并非用例失败。
- Conan 干净构建通过。完整引用：`boulder-game/1.02@ohpcd/stable#503dd32c9e51e16cbfb1d828c9f149f5:3a4ed3ccc950041ac22b55893315c0cd87789c52#338825b7e094899ad9d16909681cb1a4`。

## 2026-09-20 最终成品真机复验

从上述 Conan 成品内的 harmony-project 构建 HAP，没有用探索工程的原生库替代。HAP 同时包含 libboulderhost.so、libeditorhost.so、libc++_shared.so，安装成功。

- 游戏菜单正常显示，Enter 进入关卡；Right 后角色向右移动。
- 游戏→首页→编辑器→首页→游戏正常，同一应用进程存活。
- 编辑器正常显示，此前保存的钻石地图仍存在。
- 前期探索验证覆盖编辑绘制、S 保存、L 重载、进程重启后持久化、F3 三格笔刷；用户已确认音乐可听见。这些不是本次重新进行的听感测试。

成品截图由操作者保存在本地测试记录；没有把用户签名证书/密码放入归档。

## 限制

画布固定 1024×768，入口编辑 newlevel.map，无外部目录选择器及滚轮转发。
Conan 验证器未解析到 package ID，L2/L4/L5 跳过，不宣称这些自动步骤实际执行；独立消费者测试与 HAP 验证如上。官方 W3 CI 结论以本次 finish 输出为准。

本次官方 finish W3 CI 已通过（exit 0）：L0/L1/L1e/L2/L5 PASS，L4为targets子串误报警告。旧式G0错误调用./configure失败，如实保留，不当作成功证据。
