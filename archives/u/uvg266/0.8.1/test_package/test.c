/*
 * test_package 消费者验证：真实调用 uvg266 公共 API（R34）。
 *
 * 通过公开头文件 uvg266.h 使用库：获取 8-bit API，分配并初始化配置，
 * 打开编码器，配置最小编码参数，编码一帧黑帧并断言输出比特流非空。
 * 不包含任何库私有头文件，不调用内部符号。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <uvg266.h>

int main(void)
{
  const uvg_api *api = uvg_api_get(8);
  if (!api) {
    fprintf(stderr, "FAIL: uvg_api_get(8) returned NULL\n");
    return 1;
  }

  uvg_config *cfg = api->config_alloc();
  if (!cfg) {
    fprintf(stderr, "FAIL: config_alloc() returned NULL\n");
    return 1;
  }
  if (!api->config_init(cfg)) {
    fprintf(stderr, "FAIL: config_init() failed\n");
    api->config_destroy(cfg);
    return 1;
  }

  /* 最小可编码配置：64x64 单帧、ultrafast、单线程 */
  if (!api->config_parse(cfg, "preset", "ultrafast")) {
    fprintf(stderr, "FAIL: config_parse(preset) failed\n");
    api->config_destroy(cfg);
    return 1;
  }
  if (!api->config_parse(cfg, "threads", "0")) {
    fprintf(stderr, "FAIL: config_parse(threads) failed\n");
    api->config_destroy(cfg);
    return 1;
  }
  if (!api->config_parse(cfg, "input-res", "64x64")) {
    fprintf(stderr, "FAIL: config_parse(input-res) failed\n");
    api->config_destroy(cfg);
    return 1;
  }

  uvg_encoder *enc = api->encoder_open(cfg);
  if (!enc) {
    fprintf(stderr, "FAIL: encoder_open() returned NULL\n");
    api->config_destroy(cfg);
    return 1;
  }

  uvg_picture *pic = api->picture_alloc_csp(UVG_CSP_420, 64, 64);
  if (!pic) {
    fprintf(stderr, "FAIL: picture_alloc_csp() returned NULL\n");
    api->encoder_close(enc);
    api->config_destroy(cfg);
    return 1;
  }
  memset(pic->y, 0, (size_t)pic->width * pic->height);
  memset(pic->u, 128, (size_t)((pic->width / 2) * (pic->height / 2)));
  memset(pic->v, 128, (size_t)((pic->width / 2) * (pic->height / 2)));

  /* 与上游 encmain.c 一致的用法：循环喂入帧（含 flush NULL），
   * 直到拿到非空比特流或输入结束。 */
  uint32_t out_len = 0;
  uvg_data_chunk *out = NULL;
  uvg_picture *rec = NULL, *src = NULL;
  uvg_frame_info info;
  memset(&info, 0, sizeof(info));
  int fed = 0;
  for (;;) {
    uvg_picture *in = (fed < 3) ? pic : NULL;
    out = NULL;
    out_len = 0;
    if (!api->encoder_encode(enc, in, &out, &out_len, &rec, &src, &info)) {
      fprintf(stderr, "FAIL: encoder_encode() returned 0\n");
      api->picture_free(pic);
      api->encoder_close(enc);
      api->config_destroy(cfg);
      return 1;
    }
    if (out == NULL && in == NULL) {
      /* 输入与输出均已耗尽 */
      break;
    }
    if (out != NULL) {
      api->chunk_free(out);
    }
    if (fed < 3) {
      fed++;
    } else {
      break;
    }
  }
  if (out_len == 0) {
    fprintf(stderr, "FAIL: encoder_encode() produced no bitstream\n");
    api->picture_free(pic);
    api->encoder_close(enc);
    api->config_destroy(cfg);
    return 1;
  }

  printf("OK: uvg266 consumer encoded %u bytes of VVC bitstream\n", out_len);

  api->picture_free(pic);
  api->encoder_close(enc);
  api->config_destroy(cfg);
  return 0;
}
