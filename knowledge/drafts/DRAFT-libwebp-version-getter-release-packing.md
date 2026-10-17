# DRAFT: 运行期版本号 API 断言：先读实现确认打包语义，勿按直觉推值

- **严重度**: 2
- **类别**: test, api, methodology
- **软件**: libwebp 1.6.0.1（webmproject/libwebp，鸿蒙 PC 适配）
- **阶段**: test_package（R34）
- **状态**: UNMATCHED 草稿，待人工/AI 审核晋升

## 症状

libwebp 1.6.0.1 真机首轮探针版本断言 FAIL（2 条），[dbg] 打印
`dec_ver=0x00010600 enc_ver=0x00010600`：
- 断言 1（`>= 0x01060000`，按发行版号 1.6.0 直觉展开）：FAIL——0x010600（67072）
  比 0x01060000（17170432）少一个字节的零；
- 断言 2（改为 ABI 阈值 0x0210）：恰好通过，但语义错误（混用两套数）。

## 根因

libwebp 的版本号 getter 实现（src/dec/vp8_dec.c:36-38）：

```c
int WebPGetDecoderVersion(void) {
  return (DEC_MAJ_VERSION << 16) | (DEC_MIN_VERSION << 8) | DEC_REV_VERSION;
}
```

返回**三字节打包发行版号**（decode.h 注释："each of major/minor/revision.
E.g: v2.5.7 is 0x020507"），1.6.0 → 0x010600。而 `WEBP_DECODER_ABI_VERSION`
= 0x0210（1.6.0 起）是另一套数（ABI/SONAME 语义）。1.5.0 实现相同，说明该语义
一直如此，非 1.6.0 变更——纯粹的断言设计错误。

库的版本号体系常并存多套数：发行版号、ABI/SONAME 版本、协议版本，getter 返回
哪一套由实现决定，且打包位宽各不相同（SDL 三版本函数分离；OpenSSL
OPENSSL_VERSION_NUMBER / zlib ZLIB_VERNUM 是 0xMNNFFPPS 五段打包）。

## 修正方案

```c
/* 先打印实值再定断言：1.6.0 → 0x010600（三字节打包发行版号，非 ABI 0x0210） */
int dec_ver = WebPGetDecoderVersion();
printf("[dbg] dec_ver=0x%08x enc_ver=0x%08x\n", dec_ver, enc_ver);
CHECK(dec_ver >= 0x010600, "WebPGetDecoderVersion >= 0x010600 (release packing, 1.6.0)");
CHECK(enc_ver >= 0x010600, "WebPGetEncoderVersion >= 0x010600 (release packing, 1.6.0)");
```

修正后真机探针 11/11 ALL GREEN。

## 验证

- libwebp 1.6.0.1 OHOS aarch64 test_package：11/11 断言通过
  （conan-verify G0-G4/L2/L4/L5 全绿，2026-09-27 华为 PC，Conan 2.29.1）
- 实现核对：1.5.0 与 1.6.0 的 vp8_dec.c 版本函数逐字节一致（语义未变更）

## 关键词

version getter, release packing, ABI version, runtime assert, libwebp, R34
