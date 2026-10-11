# qrq

高速摩尔斯电码（CW）训练器，类似 DOS 经典程序 Rufz。以 50 组随机呼号为
一轮，逐次提高速度，主要用于业余无线电竞赛中的呼号高速抄收训练。

- 上游主页：https://fkurz.net/ham/qrq.html
- 上游版本：0.3.5（2022-01-24）
- 许可证：GPL-2.0-or-later
- 构建系统：Makefile（无 configure）

## HarmonyOS 适配要点

上游仅提供 OSS / PulseAudio / CoreAudio / WinMM 四种音频输出后端，均不适
用于 HarmonyOS。本适配新增了一个基于鸿蒙原生 **OHAudio**（`libohaudio`）
的后端 `ohosaudio.c`，通过 `make USE_OHOS=YES` 选择，链接系统库 `libohaudio`。

- 终端界面依赖 `ncurses/6.5`（Conan 制品仓）。
- 音频后端采用回调（pull）模型：`write_audio()` 累积波形，`close_audio()`
  启动 `OH_AudioRenderer` 并等待全部采样被消费。
- 新增源码（`compat/ohosaudio.c/.h`）通过 conanfile.py `export_sources` 传递，
  而非 new-file 补丁（E254：toybox `patch --dry-run` 会真实创建目标文件）。
- 上游 Makefile 的 `make install` 依赖 `/usr/bin/install`（鸿蒙缺失），
  配方在 `package()` 中直接收集产物。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.3.5 | built | 首次适配，新增 OHAudio 后端 |
