# DRAFT-13503: AMR-NB 参考编解码器测试三要点(GP3 精确帧长/解码器冷启动收敛/CLI 魔数)

## 要点(libamrnb 11.0.0.0 真机实证)

1. **GP3 存储格式帧字节数是精确常数**(1 TOC 字节 + RFC 4867 payload):
   MR475/MR515/MR59/MR67/MR74/MR795/MR102/MR122 = **13/14/16/18/20/21/27/32** 字节,
   可作强断言;
2. **解码器冷启动**:3GPP 参考解码器从复位态起前 2-3 帧输出幅度爬升——单帧往返的
   峰值断言必失败(实测单帧远低于阈值;6 帧后第 3 帧起 peak=4152 ≈ 输入 52%)。
   多帧往返、第 3 帧起测峰值;
3. **CLI 冒烟**:amrnb-encoder 输出流前缀是 6 字节 `#!AMR\n`(encoder.c 的
   AMR_MAGIC_NUMBER)+ 每帧 GP3 字节;320 采样(2 帧)MR122 → 6+2×32=70 字节。

## 接口备忘

- 头文件:`<amrnb/interf_enc.h>`(自带 sp_enc.h:enum Mode)+ `<amrnb/interf_dec.h>`;
- 原名 `Encoder_Interface_init/Encode/exit`、`Decoder_Interface_init/Decode/exit`
  经 any-cflags 补丁宏映射到 GP3/IF2/ETSI 变体(默认 GP3);
- DTX:`Encoder_Interface_init(1)` + 静音 → SID 小帧(0 < n ≤ 32)。

## 反例(烧掉一轮真机 CI 的教训)

单帧 `peak >= 4000` 断言在完全健康的编解码器上失败——测试问题而非库问题。
