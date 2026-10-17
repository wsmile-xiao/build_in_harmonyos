# libportaudiocxx

PortAudioCpp —— PortAudio V19 C API 的原生 C++ 绑定，随 PortAudio 官方 19.7.0
发布包以 `bindings/cpp/` 形式分发。

| 项目 | 信息 |
| --- | --- |
| 上游 | https://github.com/PortAudio/portaudio （bindings/cpp） |
| 官网 | https://www.portaudio.com/ |
| 许可证 | MIT |
| 版本 | 19.7.0（上游 PortAudio 发布包 `pa_stable_v190700_20210406.tgz`） |

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| portaudio | 19.7.0 | PortAudio C 库（本仓库已适配，same-tarball） |

## HarmonyOS 适配要点

1. **独立构建**：C++ 绑定在 `bindings/cpp/` 内独立 configure/make，链接依赖包
   `portaudio/19.7.0` 的静态库，而非上游默认的源码树内 `libportaudio.la`。
2. **构建系统 patch**：上游 `lib/Makefile.in` 将 `LIBADD` 硬编码为
   `$(top_builddir)/$(PORTAUDIO_ROOT)/lib/libportaudio.la`，且 automake 推导的
   `DEPENDENCIES` 指向同一文件；两者改为 `-lportaudio` 与空依赖，使包自洽。
3. **示例排除**：`bin/` 下的 `devs`/`sine` 示例需要真实音频设备，`SUBDIRS`
   移除 `bin`。
4. **config.sub**：识别 `aarch64-linux-ohos` 三元组（与 portaudio 适配一致）。
5. **HMDFS**：configure 临时目录 umask 由 077 放宽到 022，避免 HMDFS 拒绝创建。
6. **无后端行为**：OHOS 的 portaudio 包禁用 ALSA/JACK/OSS/ASIHPI/CoreAudio，
   `hostApiCount()==0`、`deviceCount()==0` 是平台特有行为，测试对此做了断言。

## 版本

| 版本 | 状态 | 构建日期 |
| --- | --- | --- |
| 19.7.0 | built | 2026-09-14 |
