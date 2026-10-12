# 上游零测试的解码器库：test_package 程序化合成最小格式字节流全 API 实测

> Draft: `DRAFT-GIFDEC-SYNTHETIC-GIF-LZW-TEST`
> Stem: `gifdec-0.0-git.1dcbae1-synthetic-gif-lzw-test` — pairs with the same-stem `.kv`

## 基本信息

- **状态**: pending-editor-review
- **类别**: testing, conan, packaging
- **触发工具**: conan|clang|cmake|ctest
- **阶段**: testing|packaging
- **严重度**: 2
- **来源**: gifdec 0.0-git.1dcbae1 适配 PR（j669539，2026-10-04）

## 问题特征

一类小型解码器/解析器库（gifdec、minimp3 形态）上游不提供任何测试套件：
仓库只有核心源码 + example 演示。gifdec 的 example.c 是 SDL2 交互播放器，
需要 GUI 库与真实 GIF 文件——CI worker 均不可用。适配时面临两难：

1. 无测试可跑 → CI L1a 直接 fail（test_package 无执行痕迹）；
2. 把真实格式样本文件（.gif）打包进 test_package → 二进制资产进 git 仓库
   （JC2/JC3 垃圾文件门禁风险）+ 版权/来源不清。

## 根因

上游"example 即文档"的开发模式没有把任何断言固化成测试程序；
而消费者侧验证（R34/R40）又必须在 Conan 生命周期内真实执行解码路径。

## 解决方案（代码级）

test_package 的测试源文件内嵌格式规范的字节级常量数组，程序化合成最小
合法输入流，写临时目录后走真实公开 API 全链路验证：

```c
/* GIF89a 最小 1×1 流：头 + LSD + 2 色 GCT + 图像描述符 + LZW + trailer */
static const uint8_t GIF_1X1[] = {
    'G','I','F','8','9','a',
    0x01,0x00, 0x01,0x00,    /* width=1, height=1 */
    0xF0, 0x00, 0x00,        /* GCT flag + 2 entries, bgindex, aspect */
    0x00,0x00,0x00,          /* GCT[0] = black */
    0xFF,0x00,0x00,          /* GCT[1] = red */
    0x2C, 0x00,0x00, 0x00,0x00, 0x01,0x00, 0x01,0x00, 0x00,  /* image desc */
    0x02, 0x01,              /* LZW min code size=2, sub-block len=1 */
    0x04,                    /* LZW: [clear=4][code0] -> 6 bits LSB-first */
    0x00, 0x3B               /* terminator, trailer */
};
```

- **LZW 手工位打包**（LSB-first 变长码）：min code size=2 时
  `[clear][code0]` → 单字节 `0x04`；`[clear][code0][code1]` → 9 bit 跨字节
  `0x44 0x00`；
- **packed 字节易错点**：LCT size 在 packed 低 3 位，2 色表须写 `0x80`
  （`0x81`=4 色表 12 字节，流错位后 read_image_data 返回 -1）；
- **错误契约同法合成**：坏签名/GIF87a 版本/无 GCT/垃圾分隔符负样本；
- **关键纪律**：断言锚点先在未修改上游源码上独立编译实测校准（本例
  独立锚点程序 49/49 全过后冻结），防想当然——如 NETSCAPE loop_count
  要到首次 gd_get_frame 遍历块流后才解析；
- **临时文件**：test() 里先 mkdir build_folder 子目录再 cmake.test()
  （ctest COMMAND 引用的目录必须先存在）。

## 降级方案

格式过于复杂无法手工合成时：①用上游源码树自带最小测试资产随包分发
（MANIFEST.yml 声明来源）；②仅验证打开/关闭/错误契约 + 链接性（L1e）。
两条退路都削弱 R40 验证完整性，仅作下策。

## 实证

gifdec 0.0-git.1dcbae1 本地 conan create（ohos-aarch64, clang 15）：
test_gifdec **49/49 断言全过**（9 场景：1×1/2×1 最小流、GCE 延时/透明度、
NETSCAPE loop、LCT 覆盖、双帧 canvas、rewind、错误契约 5 项）。

## 适用范围

- 上游零测试套件的解码器/解析器库（图像/音频/压缩格式）
- 上游 example 依赖 GUI 框架（SDL2/GTK）无法进 CI 的库
- 格式规范可字节级手工构造的二进制格式（GIF/LZW/MP3 帧头等）
