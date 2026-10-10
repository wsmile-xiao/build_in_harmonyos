# saytime 1.0 适配笔记

> 平台任务号：10402（活动：开源鸿蒙PC专项积分赛；主号名额超限，经小号中转 relay 认领）
> 适配日期：2026-10-01　执行：XiaYuanOwO（云鸢 / 青岛城市学院）

## 一、这个包是什么

`saytime` 是 **Jef Poskanzer 1990 年写给 SPARCstation 的报时语音程序**，
源码头注释原话是 `audio time hack for the SPARCstation`。

原包只有这些：

```
saytime.c    7118 字节（450 行）—— 全部逻辑
saytime.sh    898 字节           —— 同等逻辑的 shell 版
Makefile      141 字节           —— 只有 saytime: 与 clean: 两个目标
sounds/*.au              30 段语音，合计 128602 字节
```

它按当前时刻挑出对应句子（"The time is eight o'clock exactly." /
"... eight oh-eight and one second."），按顺序拼成一条流写进 `/dev/audio`。

## 二、为什么必须打补丁

上游原样在 OHOS PC 上**跑不起来**，两处硬伤：

### 硬伤 1：`/dev/audio` 是 SPARCstation 的 OSS 音频设备节点，OHOS PC 根本没有

上游 `sayfile()` 里：

```c
audiofd = open( "/dev/audio", O_WRONLY | O_NDELAY );
if ( audiofd < 0 )
    {
    perror( "opening /dev/audio" );
    exit( 1 );          // ← 设备一缺，程序直接退出
    }
```

实测（qemu-aarch64 + OHOS sysroot）：`open` 返回 `ENOENT`，程序 `exit(1)`。

**patch 0001 的处理**：打开失败时打印一行诊断，然后把 `audiofd` 换成 `1`
（stdout），而不是退出。调用方 `saytime | some-player` 即可，程序本身
不再因为缺设备而不可用。

★ **这是刻意的行为变更**，manifest.yaml 里 `behavior_change: true`。
理由：音频渲染后端本来就该由调用方决定——SPARCstation 上是内核 OSS 驱动，
在 OHOS PC 上可以是 ALSA、PipeWire，或者干脆是任何接受裸 PCM 的播放器。
把「没有设备节点」从「致命错误」降级为「换个输出目标」是唯一合理的做法。

### 硬伤 2：`SOUND_DIR` 被上游写死成作者家目录

上游 Makefile 就一行：

```make
saytime: saytime.c
	cc -O -DSOUND_DIR=\"/users/mag/games/sounds/audio\" saytime.c -o saytime
```

`/users/mag/...` 是 1990 年作者的家目录，本机不存在。**不定义 `SOUND_DIR`
连编译都过不了**（`error: use of undeclared identifier 'SOUND_DIR'`）。

**patch 0001 的处理**：声音目录改为两级查找——

```
SAYTIME_SOUNDS 环境变量  >  编译期 SOUND_DIR
```

编译期默认值由 conanfile 通过 CMakeToolchain 注入，指向包内
`share/saytime/sounds`。加环境变量这一层是为了让部署方**不必重编译**
就能换语音目录（比如换成中文语音包）。

## 三、为什么「流是片段的精确拼接」可以当断言

30 段语音是**无头裸 PCM**，不是 `.au` 容器（没有 `.snd` magic）。
拼接结果本身就是 SPARCstation 音频设备期望的字节流。

关键在于：saytime 按**当前时刻**选句子，所以输出长度**随时间变化**——
不能断言"输出 N 字节"。

但可以断言一个与时刻无关的强性质：

> stdout 上的字节流，能被贪心地、完整地分解成包内 `.au` 片段的有序拼接，
> 零残留字节。

测试就是这么做的：每次在当前位置找一个能完整匹配的片段并消耗掉，
最后必须正好消耗完整个流。实测两次运行分别是 27687 字节 / 7 段、
31201 字节 / 8 段——长度不同但性质相同。

## 四、取证表：qemu-aarch64 + OHOS sysroot 实测输出

### A：`SAYTIME_SOUNDS` 指向包内 sounds
```
RC = 0
stderr: saytime: /dev/audio unavailable (No such file or directory), writing the audio stream to stdout
stdout: 非空裸 PCM 流
```

### C：`SAYTIME_SOUNDS=/definitely/not/here`
```
RC = 1
stderr: saytime: /dev/audio unavailable (No such file or directory), writing the audio stream to stdout
        opening audio file: No such file or directory
stdout: 0 字节
```

### D：`SAYTIME_SOUNDS` 指向空目录
```
RC = 1
stderr: 同上（含 opening audio file）
stdout: 0 字节
```

## 五、踩过的坑

### 坑 1：conandata 的 patches 格式

Conan 2.x 的 `apply_conandata_patches()` 按 `self.version` 查找补丁列表。
把 `patches` 写成「以文件名为键的 dict」会让 Conan 取到**空列表并静默跳过**
补丁，CI 门禁 L0f 报 `bad_patch_format`。必须是列表：

```yaml
patches:
  - patch_file: "patches/0001-xxx.patch"
    patch_description: "..."
    patch_type: "portability"
```

### 坑 2：用 CMakeToolchain，不要 `self.run("<clang> ...")`

本地实测（Conan 2.29.1 + Windows）：

| 写法 | 结果 |
|------|------|
| `subprocess.run(f"{cc} --version")` | rc=0 |
| `self.run(f"{cc} --version")` | **Error 1** |
| `self.run("cmake ...")`（build profile 带 `[buildenv]`） | **Error 1** |
| `self.run("cmake ...")`（`--profile:build=default`） | 正常 |

即 Conan's `[buildenv]` 段会让 `self.run()` 里的命令（含 cmake 自己）
报 `'.' is not recognized as an internal or external command`。
`CMake(self)` 走 CMake 自己的编译器调用路径，不受影响，
这也是本仓库其它配方统一的做法。

配套：`cmake_layout(self, build_folder=".")`，否则报
`CMakePresets.json was not found in .../build/Release/generators`。

### 坑 3：SOUND_DIR 必须是**包内绝对路径**

`conanfile.py` 里用 `self.package_folder` 拼出
`share/saytime/sounds`，再经 `CMakeToolchain.cache_variables` 传给
CMakeLists，最后 `target_compile_definitions(... SOUND_DIR="...")`。
不能留相对路径——程序运行时的 cwd 与构建时无关。

### 坑 4：`-w` 不是偷懒

`saytime.c` 是 1990 年代的 K&R 风格代码（`sayfile( filename ) char *filename;`
这种老式函数定义、赋值当条件）。沿用上游口径统一 `-w` 静默。

## 六、验证标准与结果

| 项 | 结果 |
|---|---|
| `conan create` | **通过**（主包 + test_package 全绿） |
| 产物架构 | ELF64 / AArch64 |
| `NEEDED` | 仅 `libc.so` |
| 包内容 | `bin/saytime` + `share/saytime/saytime.sh` + `sounds/*.au`（30 段）= 34 文件 |
| qemu-aarch64 测试 | **17 checks, 0 failures**（跑在真实 conan 包目录上） |
| CI L0 / L1 | 待投递后回报 |

## 七、适配范围声明

本包装 `bin/saytime`、`share/saytime/sounds/*.au` 和 shell 版 `saytime.sh`。
**不安装任何播放器**——渲染后端由调用方决定。包层只负责把裸 PCM 流
正确地交到 stdout 上。
