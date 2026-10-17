/* test_ohos_load_all.c — HarmonyOS PC 专项：全部 36 插件真实加载验证
 *
 * OHOS musl ldso + libc++_shared.so 环境下的加载兼容性：
 *  - dlopen 全部 36 个插件 .so（RTLD_NOW 全符号重定位）
 *  - lv2_descriptor(0) 取描述符并校验 URI 与插件名一致
 *  - 抽样 4 个插件（EPiano/Piano 合成器 + TestTone 信号发生 +
 *    Bandisto 效果器）做 instantiate+run+cleanup 生命周期
 */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const char *kPlugins[36] = {
    "Ambience", "Bandisto", "BeatBox", "Combo", "DX10", "DeEss",
    "Degrade", "Delay", "Detune", "Dither", "DubDelay", "Dynamics",
    "EPiano", "Image", "JX10", "Leslie", "Limiter", "Loudness",
    "MultiBand", "Overdrive", "Piano", "RePsycho", "RezFilter", "RingMod",
    "RoundPan", "Shepard", "Splitter", "Stereo", "SubSynth", "TalkBox",
    "TestTone", "ThruZero", "Tracker", "Transient", "VocInput", "Vocoder",
};
#define NPLUGINS 36
#define MDA_URI_PREFIX "http://drobilla.net/plugins/mda/"

typedef void *LV2_Handle;
typedef struct {
    const char *URI;
    void *instantiate, *connect_port, *activate, *run,
         *deactivate, *cleanup, *extension_data;
} LV2_Descriptor_Min;
typedef struct { const char *URI; void *data; } LV2_Feature_Min;

static int fails = 0;

/* 生命周期验证（端口布局由各插件 .ttl 决定；统一按最大 2 进 2 出 +
 * 控制端口扫描连接，实际通过即可——wrapper 对多余 connect_port 无害） */
static int lifecycle(const LV2_Descriptor_Min *desc, const char *bundle,
                     const char *name) {
    const LV2_Feature_Min *const feats[] = { NULL };
    LV2_Handle inst = ((LV2_Handle (*)(const void *, double, const char *,
                                       const LV2_Feature_Min *const *))desc->instantiate)(
        (const void *)desc, 44100.0, bundle, feats);
    if (!inst) {
        printf("  [FAIL] %s instantiate failed\n", name);
        fails++;
        return 1;
    }
    /* 连接 32 个端口槽（多数插件远少于此；wrapper 只存指针，未用端口
     * 传有效缓冲即可——连接 NULL 控制端口会致 run 读 0，这里给静音缓冲） */
    static float ports[32][256];
    for (uint32_t i = 0; i < 32; i++)
        ((void (*)(LV2_Handle, uint32_t, void *))desc->connect_port)(
            inst, i, ports[i % 32]);
    ((void (*)(LV2_Handle, uint32_t))desc->run)(inst, 256);
    ((void (*)(LV2_Handle))desc->cleanup)(inst);
    printf("  [ok] %s instantiate+run(256)+cleanup\n", name);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_ohos_load_all <bundle-dir>\n");
        return 2;
    }
    const char *bundle = argv[1];

    /* Part 1: dlopen 全部 36 插件 + lv2_descriptor(0) URI 校验 */
    printf("== OHOS Part 2: dlopen all 36 plugins + lv2_descriptor ==\n");
    int loaded = 0;
    for (int i = 0; i < NPLUGINS; i++) {
        char so[1024], want[256];
        snprintf(so, sizeof(so), "%s/%s.so", bundle, kPlugins[i]);
        snprintf(want, sizeof(want), "%s%s", MDA_URI_PREFIX, kPlugins[i]);

        void *h = dlopen(so, RTLD_NOW);
        if (!h) {
            printf("  [FAIL] dlopen(%s): %s\n", kPlugins[i], dlerror());
            fails++;
            continue;
        }
        const LV2_Descriptor_Min *(*get_desc)(uint32_t) =
            (const LV2_Descriptor_Min *(*)(uint32_t))dlsym(h, "lv2_descriptor");
        if (!get_desc) {
            printf("  [FAIL] dlsym(lv2_descriptor) on %s\n", kPlugins[i]);
            fails++;
            dlclose(h);
            continue;
        }
        const LV2_Descriptor_Min *desc = get_desc(0);
        if (!desc || !desc->URI || strcmp(desc->URI, want) != 0) {
            printf("  [FAIL] %s URI mismatch (got %s)\n", kPlugins[i],
                   desc && desc->URI ? desc->URI : "(null)");
            fails++;
            dlclose(h);
            continue;
        }
        loaded++;
        /* 保留 4 个样本句柄做生命周期（其余关闭） */
        if (!strcmp(kPlugins[i], "EPiano") || !strcmp(kPlugins[i], "Piano") ||
            !strcmp(kPlugins[i], "TestTone") || !strcmp(kPlugins[i], "Bandisto")) {
            lifecycle(desc, bundle, kPlugins[i]);
        }
        dlclose(h);
    }
    printf("  dlopen+descriptor OK: %d/36\n", loaded);
    if (loaded != 36) fails++;

    if (fails) {
        printf("FAILED: %d check(s) failed\n", fails);
        return 1;
    }
    printf("PASS: all 36 plugins load on OHOS; 4 sampled full lifecycle OK\n");
    return 0;
}
