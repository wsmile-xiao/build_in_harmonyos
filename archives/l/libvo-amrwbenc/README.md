# libvo-amrwbenc

**VisualOn AMR-WB 编码器**（Adaptive Multi-Rate Wideband，即 G.722.2，16 kHz 宽带语音），
提供 C API（`enc_if.h`）与命令行工具 `amrwb-enc`。上游：
<https://sourceforge.net/projects/opencore-amr/>（GitHub 镜像 `mstorsjo/vo-amrwbenc`），
许可证 Apache-2.0。

它是 AMR-WB **编码**侧；解码侧由同源的 `opencore-amr`（本仓库已适配 0.1.6）提供，
两者合起来才构成完整的 AMR-WB 编解码链路（本包 test_package 的闭环验证正是这么做的）。

## OHOS（鸿蒙 PC / aarch64）适配状态

| 版本 | 状态 | 依赖 | 交付 |
|------|------|------|------|
| 0.1.3 | 已适配（消费者用例 6/6、自检 9/9） | 无 | `libvo-amrwbenc.{so,a}`、`include/vo-amrwbenc/enc_if.h`、`bin/amrwb-enc`、`vo-amrwbenc.pc` |

## 使用

```ini
[requires]
libvo-amrwbenc/0.1.3
```

命令行：

```sh
amrwb-enc -r 23850 in16k.wav out.awb     # 16 kHz 单声道 WAV → #!AMR-WB 码流
```

C API：

```c
#include <vo-amrwbenc/enc_if.h>
void *st = E_IF_init();
int n = E_IF_encode(st, mode /* 0..8 */, pcm320, out, 0);  /* n 含 1 字节帧头 */
E_IF_exit(st);
```

## 适配要点

见 `0.1.3/notes.md`：名义 GNU 三元组 + uname shim（config 识别）、`umask 077`（E011）、
以及上游 `Makefile.in` 漏掉 `bin_PROGRAMS` 时如何交付 `amrwb-enc`。
