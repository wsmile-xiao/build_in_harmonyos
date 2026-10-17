#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <twolame.h>

int main(void) {
    twolame_options *opts;
    short pcm[1024];
    unsigned char mp2[2048];
    int ret;

    /* 消费者验证：初始化 twolame 编码器 */
    opts = twolame_init();
    if (opts == NULL) {
        fprintf(stderr, "twolame_init failed\n");
        return 1;
    }

    /* 配置编码参数（与上游 frontend 默认一致） */
    if (twolame_set_num_channels(opts, 2) != 0) {
        fprintf(stderr, "twolame_set_num_channels failed\n");
        twolame_close(&opts);
        return 1;
    }
    if (twolame_set_in_samplerate(opts, 44100) != 0) {
        fprintf(stderr, "twolame_set_in_samplerate failed\n");
        twolame_close(&opts);
        return 1;
    }
    if (twolame_set_bitrate(opts, 192) != 0) {
        fprintf(stderr, "twolame_set_bitrate failed\n");
        twolame_close(&opts);
        return 1;
    }
    if (twolame_init_params(opts) != 0) {
        fprintf(stderr, "twolame_init_params failed\n");
        twolame_close(&opts);
        return 1;
    }

    /* 填充 1024 个采样并执行真实编码 */
    memset(pcm, 0, sizeof(pcm));
    ret = twolame_encode_buffer(opts, pcm, pcm, sizeof(pcm) / sizeof(short) / 2, mp2, sizeof(mp2));
    if (ret < 0) {
        fprintf(stderr, "twolame_encode_buffer failed (ret=%d)\n", ret);
        twolame_close(&opts);
        return 1;
    }

    /* flush 并关闭 */
    ret = twolame_encode_flush(opts, mp2, sizeof(mp2));
    if (ret < 0) {
        fprintf(stderr, "twolame_encode_flush failed (ret=%d)\n", ret);
        twolame_close(&opts);
        return 1;
    }

    twolame_close(&opts);
    printf("test twolame 0.4.0: encode OK\n");
    return 0;
}
