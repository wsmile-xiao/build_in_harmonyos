#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sfizz.h"

int main(void) {
    // 实质调用 sfizz C API：创建合成器、加载 SFZ 字符串、渲染音频块
    sfizz_synth_t* synth = sfizz_create_synth();
    if (synth == NULL) {
        fprintf(stderr, "sfizz_create_synth failed\n");
        return 1;
    }

    // 不引用外部音频文件的 SFZ 内容：验证解析路径与渲染路径，
    // 避免对测试环境文件系统的依赖
    const char* sfz = "<control> set_cc1=64\n<region> key=60 lokey=60 hikey=60";
    if (!sfizz_load_string(synth, "test.sfz", sfz)) {
        fprintf(stderr, "sfizz_load_string failed\n");
        sfizz_free(synth);
        return 1;
    }

    // 配置并渲染一小段音频，验证合成路径可执行
    sfizz_set_sample_rate(synth, 48000.0f);
    sfizz_set_samples_per_block(synth, 512);
    const int block = 512;
    float* left = (float*)calloc(block, sizeof(float));
    float* right = (float*)calloc(block, sizeof(float));
    if (left == NULL || right == NULL) {
        fprintf(stderr, "alloc failed\n");
        free(left); free(right);
        sfizz_free(synth);
        return 1;
    }
    float* channels[2] = { left, right };
    sfizz_render_block(synth, channels, 2, block);
    free(left);
    free(right);

    // 读取合成器状态，验证 getter API
    int numGroups = sfizz_get_num_groups(synth);
    (void)numGroups;

    sfizz_free(synth);
    printf("sfizz test: create/load/render OK\n");
    return 0;
}
