/*
 * 鸿蒙专项测试：uvg266_ohos_test
 *
 * 目的：在 OHOS aarch64 工具链（clang 15 + libc++）构建并运行的 HarmonyOS
 * 专项用例，验证 uvg266 库在 OHOS 设备二进制形态下可真实编码并产出合法的
 * VVC (H.266) 比特流：
 *   1. 通过公共头文件 uvg266.h 使用公开 API（uvg_api_get / config_alloc /
 *      config_init / config_parse / encoder_open / picture_alloc_csp /
 *      encoder_encode / encoder_headers / chunk_free / picture_free）。
 *   2. 输入 5 帧确定性渐变图案（无需 ffmpeg 外部输入）。
 *   3. 校验 encoder_headers() 输出 VPS/SPS/PPS，且 encoder_encode() 输出
 *      含 VVC NAL 起始码 0x00000001 的非空比特流。
 *
 * 该用例与 test_package 消费者测试（单帧编码）互补：本用例聚焦多帧、NAL
 * 结构与 OHOS 目标形态验证。
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <uvg266.h>

/* 检测 buf[0..7] 中是否出现 4 字节起始码 0x00 00 00 01 */
static int has_nal_start_code(const uint8_t *buf, size_t len)
{
  size_t i;
  for (i = 0; i + 3 < len; i++) {
    if (buf[i] == 0x00 && buf[i+1] == 0x00 &&
        buf[i+2] == 0x00 && buf[i+3] == 0x01) {
      return 1;
    }
  }
  return 0;
}

int main(void)
{
  const uvg_api *api = uvg_api_get(8);
  if (!api) { fprintf(stderr, "FAIL: uvg_api_get(8) returned NULL\n"); return 1; }

  uvg_config *cfg = api->config_alloc();
  if (!cfg) { fprintf(stderr, "FAIL: config_alloc() returned NULL\n"); return 1; }
  if (!api->config_init(cfg)) { fprintf(stderr, "FAIL: config_init() failed\n"); return 1; }

  if (!api->config_parse(cfg, "preset", "ultrafast")) {
    fprintf(stderr, "FAIL: config_parse(preset) failed\n"); return 1;
  }
  if (!api->config_parse(cfg, "threads", "0")) {
    fprintf(stderr, "FAIL: config_parse(threads) failed\n"); return 1;
  }
  if (!api->config_parse(cfg, "input-res", "64x64")) {
    fprintf(stderr, "FAIL: config_parse(input-res) failed\n"); return 1;
  }
  /* gop=0（全 I 帧）保证每帧立即输出，避免默认 gop=8 的
   * 帧缓冲延迟导致少量输入下无可见输出 */
  if (!api->config_parse(cfg, "gop", "0")) {
    fprintf(stderr, "FAIL: config_parse(gop) failed\n"); return 1;
  }

  uvg_encoder *enc = api->encoder_open(cfg);
  if (!enc) { fprintf(stderr, "FAIL: encoder_open() returned NULL\n"); return 1; }

  /* 1. 参数集：VPS/SPS/PPS 必须非空且含 NAL 起始码 */
  uvg_data_chunk *hdrs = NULL;
  uint32_t hdr_len = 0;
  if (!api->encoder_headers(enc, &hdrs, &hdr_len)) {
    fprintf(stderr, "FAIL: encoder_headers() failed\n"); return 1;
  }
  if (hdrs == NULL || hdr_len == 0 ||
      !has_nal_start_code((const uint8_t *)hdrs->data, hdr_len)) {
    fprintf(stderr, "FAIL: encoder_headers() produced no valid NAL headers\n");
    if (hdrs) api->chunk_free(hdrs);
    return 1;
  }
  api->chunk_free(hdrs);
  printf("OK: encoder_headers() -> %u bytes with NAL start code\n", hdr_len);

  /* 2. 5 帧确定性渐变图案，循环喂入并收集比特流 */
  uint32_t total_bytes = 0;
  int nal_found = 0;
  int fed = 0;
  for (;;) {
    uvg_picture *pic = NULL;
    if (fed < 5) {
      pic = api->picture_alloc_csp(UVG_CSP_420, 64, 64);
      if (!pic) { fprintf(stderr, "FAIL: picture_alloc_csp() failed\n"); return 1; }
      int x, y;
      for (y = 0; y < pic->height; y++) {
        for (x = 0; x < pic->width; x++) {
          pic->y[y * pic->stride + x] = (uint8_t)((x * 4 + y * 4 + fed * 16) & 0xFF);
        }
      }
      for (y = 0; y < pic->height / 2; y++) {
        for (x = 0; x < pic->width / 2; x++) {
          pic->u[y * (pic->stride / 2) + x] = 128;
          pic->v[y * (pic->stride / 2) + x] = 96;
        }
      }
      pic->pts = fed;
      fed++;
    }

    uvg_data_chunk *out = NULL;
    uvg_picture *rec = NULL, *src = NULL;
    uint32_t len = 0;
    uvg_frame_info info;
    memset(&info, 0, sizeof(info));

    if (!api->encoder_encode(enc, pic, &out, &len, &rec, &src, &info)) {
      fprintf(stderr, "FAIL: encoder_encode() returned 0\n");
      return 1;
    }
    if (out == NULL && pic == NULL) {
      break; /* flush 完成 */
    }
    if (out != NULL) {
      if (has_nal_start_code((const uint8_t *)out->data, len)) {
        nal_found = 1;
      }
      total_bytes += len;
      api->chunk_free(out);
    }
    if (pic != NULL) {
      api->picture_free(pic);
    }
    if (pic == NULL && out == NULL) {
      break;
    }
    if (fed >= 5 && out == NULL) {
      /* 帧喂完后继续 flush */
    }
    if (fed >= 5 && out == NULL && rec == NULL) {
      break;
    }
  }

  if (total_bytes == 0) {
    fprintf(stderr, "FAIL: no bitstream produced\n");
    return 1;
  }
  if (!nal_found) {
    fprintf(stderr, "FAIL: no NAL start code in encoded bitstream\n");
    return 1;
  }

  printf("OK: uvg266_ohos_test encoded %u bytes, NAL start code present\n",
         total_bytes);

  api->encoder_close(enc);
  api->config_destroy(cfg);
  return 0;
}