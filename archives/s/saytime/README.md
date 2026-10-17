# saytime

[Jef Poskanzer](https://www.cs.cmu.edu/~jef/) 1990 年写给 SPARCstation 的
**报时语音程序**（源码头注释原话：`audio time hack for the SPARCstation`）。

## 它做什么

按当前时刻从 30 段预录语音里挑出对应的一句，拼成一条音频流：

```
$ saytime | some-player
```

| 当前时刻 | 拼出的句子 |
|---|---|
| 08:00:00 | The time is eight o'clock exactly. |
| 08:08:01 | The time is eight oh-eight and one second. |
| 08:08:45 | The time is eight oh-eight and eight seconds. |

输出是**无头裸 PCM**（8-bit μ-law），拼接结果本身就是音频设备期望的字节流。

## 语音目录

优先级：

```
$SAYTIME_SOUNDS 环境变量  >  编译期内置的包内 share/saytime/sounds
```

不设环境变量时用包内自带的 30 段英文语音；换成自己的语音包只需
`export SAYTIME_SOUNDS=/path/to/clips`，**不需要重编译**。

## 快速验证

```
$ export SAYTIME_SOUNDS=/usr/share/saytime/sounds
$ saytime > out.au
saytime: /dev/audio unavailable (No such file or directory), writing the audio stream to stdout
$ wc -c < out.au
31201
```

那行 stderr 是**预期内的**：OHOS PC 没有 SPARCstation 的 `/dev/audio`
设备节点，程序自动把音频流改写到 stdout。渲染后端由调用方决定。

以上正是本包消费者测试（17 条断言）的断言依据 —— 零网络、零真实音频设备。

## 版本

| 版本 | Conan 引用 | 状态 |
|---|---|---|
| 1.0 | `saytime/1.0` | 已适配（aarch64） |

## 授权

MIT（源码头即 MIT 式授权声明）。
