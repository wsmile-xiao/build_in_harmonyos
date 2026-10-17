# AudioResamplerate

音频重采样程序/库。基于 [Secret Rabbit Code (libsamplerate)](http://www.mega-nerd.com/SRC/index.html)
与 [iniparser](http://ndevilla.free.fr/iniparser) 构建，提供 `libresamplerate`（采样率转换核心）、
`libiniparser`（配置文件解析）与 `liblog`（日志）三个共享库，以及 `bin/resamplerate` 命令行演示程序。

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.1 | built | 首版适配；纯 Makefile 构建，OHOS aarch64 编译通过，conan create 1/1 测试通过 |

## 上游仓库

- https://github.com/AnSwErYWJ/AudioResamplerate (GPL-3.0)

## 构建系统

- 顶层 Makefile：`make iniparser` / `make log` / `make resamplerate` / `make all`

## OHOS 适配要点

1. 官方 tarball 自带 x86-64 预编译 `lib/*.so`（提交进源码树的构建产物）——配方 build() 先
   `make clean cleanso` 清除，全部从源码重建为 aarch64。
2. 上游 Makefile 不自动创建 `bin/` 目录——配方先 `mkdir -p bin` 再 `make all`。
3. 纯 Makefile 构建（无 configure/autotools），配方直接驱动 make 并显式传 `CC=clang`（R33）。
4. `float_cast.h` 的 lrint/lrintf 缺失警告为平台回退分支，仅警告不影响功能。
5. 无 runtime 依赖（纯 C，仅 libc）。

## 消费者验证

- `2.1/consumer/consumer_audioresamplerate.c`：业务上层组件视角，仅用公开 API src_new/src_process 完成 16k→48k 重采样。
- `2.1/consumer/ohos_test_audioresamplerate.c`：鸿蒙专项测试（端序自检 + 转换器枚举 + 真实重采样校验）。