/* test_mda_lv2.c — mda-lv2 1.2.12 test_package 主测试
 *
 * 三级验证（R34 非空壳——真实调用 LV2 插件 API）：
 *  1. bundle 结构：manifest.ttl 声明全部 36 个插件 URI、9 个 presets
 *     TTL、36 个插件数据 TTL 存在
 *  2. ELF 校验：逐个 .so 检查 ELF64/AArch64（机器码读取 ELF 头，
 *     不依赖 readelf）
 *  3. 真实加载验证：dlopen TestTone.so → lv2_descriptor() →
 *     instantiate（NULL 结尾 features 数组）→ connect_port → run(480)
 *     → cleanup 完整生命周期
 */
#include <dlfcn.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* mda-lv2 插件清单（mda.lv2/meson.build plugins 列表，36 个） */
static const char *kPlugins[36] = {
    "Ambience", "Bandisto", "BeatBox", "Combo", "DX10", "DeEss",
    "Degrade", "Delay", "Detune", "Dither", "DubDelay", "Dynamics",
    "EPiano", "Image", "JX10", "Leslie", "Limiter", "Loudness",
    "MultiBand", "Overdrive", "Piano", "RePsycho", "RezFilter", "RingMod",
    "RoundPan", "Shepard", "Splitter", "Stereo", "SubSynth", "TalkBox",
    "TestTone", "ThruZero", "Tracker", "Transient", "VocInput", "Vocoder",
};
static const char *kPresets[9] = {
    "DX10", "Detune", "EPiano", "JX10", "Leslie",
    "Piano", "Splitter", "ThruZero", "Vocoder",
};
#define NPLUGINS 36
#define NPRESETS 9
#define MDA_URI_PREFIX "http://drobilla.net/plugins/mda/"

/* LV2 核心结构（不依赖 lv2 头——插件 ABI 层验证，兼容本测试自包含） */
typedef void *LV2_Handle;
typedef struct {
    const char *URI;
    void *instantiate;
    void *connect_port;
    void *activate;
    void *run;
    void *deactivate;
    void *cleanup;
    void *extension_data;
} LV2_Descriptor_Min;
typedef struct { const char *URI; void *data; } LV2_Feature_Min;

static int fails = 0;

static void check(int cond, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    if (cond) printf("  [ok] ");
    else { printf("  [FAIL] "); fails++; }
    vprintf(fmt, ap);
    printf("\n");
    va_end(ap);
}

/* ELF64 头校验（little-endian AArch64）：e_ident 魔数、Class、机器码 */
static int check_elf64_aarch64(const char *path, const char *name) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    unsigned char e_ident[20];
    uint16_t e_machine;
    if (fread(e_ident, 1, 20, f) != 20) { fclose(f); return -2; }
    fclose(f);
    if (memcmp(e_ident, "\x7f" "ELF", 4) != 0) return -3;
    if (e_ident[4] != 2) return -4;            /* ELFCLASS64 */
    if (e_ident[5] != 1) return -5;            /* ELFDATA2LSB */
    e_machine = (uint16_t)e_ident[18] | ((uint16_t)e_ident[19] << 8);
    if (e_machine != 0xB7) return -6;          /* EM_AARCH64 = 183 */
    (void)name;
    return 0;
}

/* 阶段 1：bundle 结构校验 */
static void test_bundle_structure(const char *bundle) {
    char path[1024];
    int i, n;

    /* manifest.ttl 存在且声明全部 36 插件 URI */
    snprintf(path, sizeof(path), "%s/manifest.ttl", bundle);
    FILE *fp = fopen(path, "r");
    check(fp != NULL, "manifest.ttl exists");
    if (!fp) return;
    char buf[65536];
    n = (int)fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    fclose(fp);
    check(n > 0, "manifest.ttl non-empty (%d bytes)", n);
    /* manifest.ttl 用 Turtle 前缀缩写：@prefix mda: <URI_PREFIX> +
     * mda:<Plugin> 条目。两级校验：前缀声明 + 36 个插件条目 */
    check(strstr(buf, MDA_URI_PREFIX) != NULL,
          "manifest.ttl declares mda prefix %s", MDA_URI_PREFIX);
    for (i = 0; i < NPLUGINS; i++) {
        char entry[128];
        snprintf(entry, sizeof(entry), "mda:%s", kPlugins[i]);
        char *pos = strstr(buf, entry);
        check(pos != NULL, "manifest.ttl declares mda:%s", kPlugins[i]);
        (void)pos;
    }

    /* 9 个 presets TTL + 36 个插件数据 TTL */
    for (i = 0; i < NPRESETS; i++) {
        snprintf(path, sizeof(path), "%s/%s-presets.ttl", bundle, kPresets[i]);
        check(access(path, R_OK) == 0, "%s-presets.ttl installed", kPresets[i]);
    }
    for (i = 0; i < NPLUGINS; i++) {
        snprintf(path, sizeof(path), "%s/%s.ttl", bundle, kPlugins[i]);
        check(access(path, R_OK) == 0, "%s.ttl installed", kPlugins[i]);
    }
}

/* 阶段 2：全部 36 个 .so 的 ELF64/AArch64 校验 */
static void test_elf_all_plugins(const char *bundle) {
    char path[1024];
    for (int i = 0; i < NPLUGINS; i++) {
        snprintf(path, sizeof(path), "%s/%s.so", bundle, kPlugins[i]);
        int rc = check_elf64_aarch64(path, kPlugins[i]);
        check(rc == 0, "%s.so is ELF64/AArch64 (rc=%d)", kPlugins[i], rc);
    }
}

/* 阶段 3：TestTone 真实生命周期（dlopen → instantiate → run → cleanup） */
static int test_lifecycle_testtone(const char *bundle) {
    char so[1024];
    snprintf(so, sizeof(so), "%s/TestTone.so", bundle);

    void *h = dlopen(so, RTLD_NOW);
    check(h != NULL, "dlopen(TestTone.so)");
    if (!h) { fprintf(stderr, "    dlerror: %s\n", dlerror()); return 1; }

    const LV2_Descriptor_Min *(*get_desc)(uint32_t) =
        (const LV2_Descriptor_Min *(*)(uint32_t))dlsym(h, "lv2_descriptor");
    check(get_desc != NULL, "dlsym(lv2_descriptor)");
    if (!get_desc) { dlclose(h); return 1; }

    const LV2_Descriptor_Min *desc = get_desc(0);
    check(desc != NULL && desc->URI != NULL, "lv2_descriptor(0) valid");
    if (!desc || !desc->URI) { dlclose(h); return 1; }
    check(strcmp(desc->URI, MDA_URI_PREFIX "TestTone") == 0,
          "descriptor URI == .../mda/TestTone (got %s)", desc->URI);

    /* instantiate：features 必须是 NULL 结尾数组（wrapper lvz_instantiate
     * 遍历 features[i]，传 NULL 指针会段错误——LV2 规范要求） */
    const LV2_Feature_Min *const feats[] = { NULL };
    LV2_Handle inst = ((LV2_Handle (*)(const void *, double, const char *,
                                       const LV2_Feature_Min *const *))desc->instantiate)(
        (const void *)desc, 48000.0, bundle, feats);
    check(inst != NULL, "instantiate(48000 Hz)");
    if (!inst) { dlclose(h); return 1; }

    /* TestTone 端口布局（TestTone.ttl）：0-7 控制、8-9 音频入、10-11 音频出 */
    float ctl[8], inbuf[2][480], outbuf[2][480];
    for (int i = 0; i < 8; i++) {
        ctl[i] = 0.0f;
        ((void (*)(LV2_Handle, uint32_t, void *))desc->connect_port)(inst, i, &ctl[i]);
    }
    for (int i = 0; i < 2; i++) {
        memset(inbuf[i], 0, sizeof(inbuf[i]));
        memset(outbuf[i], 0, sizeof(outbuf[i]));
        ((void (*)(LV2_Handle, uint32_t, void *))desc->connect_port)(inst, 8 + i, inbuf[i]);
        ((void (*)(LV2_Handle, uint32_t, void *))desc->connect_port)(inst, 10 + i, outbuf[i]);
    }

    ((void (*)(LV2_Handle, uint32_t))desc->run)(inst, 480);
    check(1, "run(480 frames)");

    ((void (*)(LV2_Handle))desc->cleanup)(inst);
    check(1, "cleanup()");

    dlclose(h);
    check(1, "dlclose()");
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_mda_lv2 <bundle-dir>\n");
        return 2;
    }
    const char *bundle = argv[1];
    printf("== Phase 1: bundle structure (%s) ==\n", bundle);
    test_bundle_structure(bundle);
    printf("== Phase 2: ELF64/AArch64 all 36 plugins ==\n");
    test_elf_all_plugins(bundle);
    printf("== Phase 3: TestTone full lifecycle (dlopen/instantiate/run/cleanup) ==\n");
    test_lifecycle_testtone(bundle);
    if (fails) {
        printf("FAILED: %d check(s) failed\n", fails);
        return 1;
    }
    printf("PASS: bundle structure + 36 ELF64/AArch64 + TestTone lifecycle\n");
    return 0;
}
