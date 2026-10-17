# klick

> 命令行 JACK 节拍器：支持 tempo map、节奏型语言与点击轨 WAV 导出。

## 简介

klick 由 Dominic Sacré 维护（2007—2009 起），是一个只走命令行的 JACK 节拍器。它以 tempo map
给出随时间变化的速度与拍号，用一套紧凑的节奏型字符串描述重音与 subdivision，并可以把点击轨
导出为 WAV 文件。上游用 SCons 构建：压缩包顶层只有一个 SConstruct，没有 configure、
CMakeLists.txt 或 Makefile.am。

本归档收录 0.12.2。包内产物为 bin/klick 与 share/klick/samples/ 下的 8 个点击采样
（click / noise / sine / square 各含 emphasis 与 normal 两枚，采样按 GPL 取自 Ardour、
GTick 与 Freepats）；采样目录由编译期常量 DATA_DIR 指到 share/klick。

## OHOS 适配要点

- 构建器：SCons 4.10.1 由配方在 generate() 内装进本次构建独占的隔离前缀，再以
  PYTHONPATH 交给 build()/package()（与 gpsd/3.26 同路数）。不走 tool_requires，
  因为 ohpcd 上没有 scons 配方，且这样能保证 build() 内不再有网络动作。
- 取依赖：上游 SConstruct 用 pkg-config 探测 jack / samplerate / sndfile，OHOS 上没有
  可靠的系统 .pc 库可探。补丁 0001 把这段探测换成 KLICK_DEPFLAGS 注入槽，由 Conan 显式
  给出每一条 -I / -L，以及各依赖在自己 cpp_info 上声明的 -D 编译宏；链接表与
  HAVE_SNDFILE_OGG 也改为显式声明（Conan 的 libsndfile 自带 vorbis / ogg）。
- 编译器：一律取 profile 的 tools.build:compiler_executables（键 c 与 cpp），经
  环境变量 CC / CXX 交给 SConstruct，不留裸 shell 变量的余地（R33）。
- 依赖声明的编译宏必须自己转发：手写 SCons 命令行不经过 CMakeToolchain /
  AutotoolsToolchain 这类生成器，所以 boost/1.84.0 声明在 boost_headers 组件上的
  BOOST_SP_NO_PTHREAD_SETCANCELSTATE 不会自动到达编译器——OHOS libc 头不声明
  pthread_setcancelstate，boost 的 sp_thread_sleep.hpp 已按该宏打补丁并等消费者定义它。
- 功能裁剪：OSC 与 RUBBERBAND 两个可选功能编译关闭，因为依赖 liblo、rubberband 在
  ohpcd 未发布（控制组实证）。核心节拍器链路（jack / libsndfile / libsamplerate /
  boost 头文件）不受影响。

## 排除与替代

- klick 的 OSC 控制入口与基于 Rubber Band 的音高变换在本包不可用；需要这两项时，
  等 liblo / rubberband 发布后重编即可（配方里只需把 OSC=0 / RUBBERBAND=0 翻回
  1 并补 requires，其余不变）。
- 无 jackd 的环境（含 CI 与设备 shell）跑不了节拍器会话，只能验证到 -V / -h 的
  早期退出路径，细则见 0.12.2/notes.md。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.84.0 | 上游只用头文件（shared_ptr、shared_array、lambda） |
| jack | 1.9.22 | 音频客户端接口 |
| libsndfile | 1.2.2 | WAV 点击轨导出 |
| libsamplerate | 0.2.2 | 采样率转换 |

## 功能验证

```bash
klick -V          # 打印 klick 0.12.2 版本横幅，退出码 0
klick -h          # 打印 Usage: 用法块，退出码 0
```

两者的处理都在 Options::parse 的早期分支完成，不触碰 JACK 连接，因此在无 jackd 的
环境里同样可判定「产物可加载 + 参数解析可用」。

## 参考

- [官网](https://das.nasophon.de/klick/)
- [源码包](https://das.nasophon.de/download/klick-0.12.2.tar.gz)
