# libgoom2

Goom 音频可视化效果库：把音频采样流转换成动画视觉效果（卷积模糊、飞星、3D
曲面、触手、IFS 等），供音乐播放器嵌入使用。上游为 XMMS goom 插件的 2004
重写版（goom2k4）。

- 上游：https://sourceforge.net/projects/goom/
- 许可证：LGPL（上游 COPYING 未标注版本，随源码分发）
- 类型：库（共享库 libgoom2；XMMS 插件与 SDL 演示程序不在适配范围）

## HarmonyOS PC 适配要点

- 上游自带 2004 年的 `config.guess`/`config.sub`：既不识别 `uname -s = HarmonyOS`，
  也不认识 aarch64。补丁分别补齐 HarmonyOS 分支与 `linux-ohos` 白名单后
  `config.sub "$(config.guess)"` 原样往返 `aarch64-unknown-linux-ohos`，
  构建为原生编译，不使用伪造 `--build/--host` 三元组的做法（E007/E072）。
- HMDFS 上 `configure` 的 `umask 077` mktemp 临时目录创建后不可写，
  `config.status` 静默失败（退出码仍为 0，Makefile 未生成）；补丁放宽为
  `umask 022`（E011，tslib 1.22 同款）。
- OHOS 适配版 conan 不把 `tools.build:compiler_executables` 映射为 CC/CXX，
  配方以 `_compiler_env()` 运行期注入编译器（adplay/1.9 先例）。
- 共享库构建（`AM_DISABLE_STATIC`，上游 default）：`libgoom2.so.0`，
  NEEDED 仅 libc.so；XMMS/SDL 前端由上游 configure 自动关闭。

详见各版本目录下的 `notes.md`。

## 版本

- `2k4` — 首次适配（built）
