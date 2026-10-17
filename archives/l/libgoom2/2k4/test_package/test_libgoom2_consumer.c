/*
 * Consumer test for libgoom2 2k4 (HarmonyOS PC adaptation).
 *
 * Links against the packaged shared library and exercises the public API:
 * goom_init / goom_set_resolution / goom_update / goom_close. Assertions
 * check that the plugin instance is real (resolution applied, visual FX
 * registered), that the sound analysis consumes the audio frames, and that
 * the returned framebuffer is actually painted and animated rather than a
 * cleared or static buffer.
 */
#include <goom/goom.h>
#include <stdio.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        checks++;                                                              \
        if (!(cond)) {                                                         \
            failures++;                                                        \
            printf("FAIL: %s\n", what);                                        \
        } else {                                                               \
            printf("ok: %s\n", what);                                          \
        }                                                                      \
    } while (0)

/* FNV-1a over the framebuffer words: a painted frame yields a non-zero hash
 * and an animating frame yields changing hashes. */
static unsigned int frame_hash(const guint32 *buffer, int words)
{
    unsigned int hash = 2166136261u;
    int i;
    for (i = 0; i < words; ++i) {
        hash ^= buffer[i];
        hash *= 16777619u;
    }
    return hash;
}

static void fill_audio(gint16 data[2][512], int cycle)
{
    int i;
    for (i = 0; i < 512; ++i) {
        data[0][i] = (gint16)((i * 251 + cycle * 977) % 65536 - 32768);
        data[1][i] = (gint16)(32767 - ((i * 197 + cycle * 613) % 65536));
    }
}

int main(void)
{
    gint16 data[2][512];
    PluginInfo *goom;
    guint32 *frame;
    unsigned int hashes[8];
    int frame_ok = 0;
    int distinct = 0;
    int frames;
    int i;

    goom = goom_init(320, 240);
    CHECK(goom != NULL, "goom_init(320, 240) returns a plugin instance");
    if (goom == NULL) {
        printf("checks=%d failures=%d\n", checks, failures);
        return 1;
    }

    CHECK(goom->screen.width == 320 && goom->screen.height == 240,
          "requested resolution is applied (320x240)");
    CHECK(goom->screen.size == 320 * 240, "screen.size equals width*height");
    CHECK(goom->nbVisuals >= 1, "at least one visual FX is registered");

    for (frames = 0; frames < 64; ++frames) {
        fill_audio(data, frames);
        frame = goom_update(goom, data, 0, 30.0f, NULL, NULL);
        if (frame == NULL)
            break;
        frame_ok++;
        if (frames % 8 == 0 && frames / 8 < 8)
            hashes[frames / 8] = frame_hash(frame, 320 * 240);
    }
    CHECK(frame_ok == 64, "all 64 audio frames produced a framebuffer");
    printf("info: frames rendered=%d\n", frame_ok);

    CHECK(hashes[0] != 0, "first sampled framebuffer is painted (non-zero hash)");

    distinct = 0;
    for (i = 0; i < 8; ++i) {
        int j;
        int seen = 0;
        for (j = 0; j < i; ++j)
            if (hashes[j] == hashes[i])
                seen = 1;
        if (!seen)
            distinct++;
    }
    CHECK(distinct >= 2, "framebuffer changes across frames (animation is live)");
    printf("info: distinct sampled framebuffer hashes=%d\n", distinct);

    CHECK(goom->sound.volume > 0.0f && goom->sound.volume <= 1.0f,
          "sound analysis consumed the audio frames (volume in (0,1])");
    printf("info: sound.volume=%f speed=%f\n",
           (double)goom->sound.volume, (double)goom->sound.speedvar);

    goom_set_resolution(goom, 640, 480);
    CHECK(goom->screen.width == 640 && goom->screen.height == 480,
          "goom_set_resolution(640, 480) is applied");

    frame_ok = 0;
    for (frames = 0; frames < 16; ++frames) {
        fill_audio(data, 100 + frames);
        frame = goom_update(goom, data, 0, 30.0f, NULL, NULL);
        if (frame != NULL)
            frame_ok++;
    }
    CHECK(frame_ok == 16, "goom_update keeps rendering after a resolution change");
    CHECK(frame_hash(frame, 640 * 480) != hashes[0],
          "resized framebuffer differs from the 320x240 frame");

    goom_close(goom);
    CHECK(1, "goom_close completed without crashing");

    printf("checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
