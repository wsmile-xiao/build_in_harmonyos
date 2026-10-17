//-----------------------------------------------------------------------------
// test_oaml.cpp — oaml 1.3.4 鸿蒙消费者用例（HarmonyOS PC / aarch64）
//
// R34: 实质调用被测包 API（非空壳）。覆盖 C++ 消费者路径：
//   GetVersion → Init(defs) → PlayTrack → MixToBuffer（真实解码+混音）
//   → IsPlaying/IsTrackPlaying/GetPlayingInfo → StopPlaying → Shutdown
//
// 无需音频设备（RtAudio 在 OHOS 上禁用，oamlBase 对 __HAVE_RTAUDIO 有守卫，
// MixToBuffer 是无头混音路径，正是游戏引擎嵌入 oaml 的标准用法）。
// 测试所需 tone.wav 与 oaml.defs 由本程序在运行时生成（自包含，无外部数据）。
//-----------------------------------------------------------------------------
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>

#include "oaml.h"

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        g_checks++;                                                         \
        if (cond) {                                                         \
            printf("[PASS] %s\n", msg);                                     \
        } else {                                                            \
            g_failures++;                                                   \
            printf("[FAIL] %s\n", msg);                                     \
        }                                                                   \
    } while (0)

static void put_u32(FILE *f, unsigned v) {
    fputc(v & 0xFF, f);
    fputc((v >> 8) & 0xFF, f);
    fputc((v >> 16) & 0xFF, f);
    fputc((v >> 24) & 0xFF, f);
}

static void put_u16(FILE *f, unsigned v) {
    fputc(v & 0xFF, f);
    fputc((v >> 8) & 0xFF, f);
}

// 生成 2 秒 44100Hz 单声道 16-bit PCM 正弦波 WAV（440Hz）
static int write_wav(const char *path) {
    const unsigned SR = 44100, SECS = 2, N = SR * SECS;
    const unsigned dataBytes = N * 2;
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    fwrite("RIFF", 1, 4, f);
    put_u32(f, 36 + dataBytes);
    fwrite("WAVE", 1, 4, f);
    fwrite("fmt ", 1, 4, f);
    put_u32(f, 16);
    put_u16(f, 1);          // PCM
    put_u16(f, 1);          // mono
    put_u32(f, SR);
    put_u32(f, SR * 2);     // byte rate
    put_u16(f, 2);          // block align
    put_u16(f, 16);         // bits
    fwrite("data", 1, 4, f);
    put_u32(f, dataBytes);
    for (unsigned i = 0; i < N; i++) {
        double v = sin(2.0 * M_PI * 440.0 * i / SR) * 16000.0;
        put_u16(f, (unsigned short)(short)v);
    }
    fclose(f);
    return 0;
}

// 上游 oaml.defs（老式根 <track> 格式，oamlBase::ReadDefs 解析）：
// 不写 <type> → 归入 loopAudios（主循环）
static int write_defs(const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    fprintf(f,
        "<track>\n"
        "\t<name>music</name>\n"
        "\t<audio>\n"
        "\t\t<name>main</name>\n"
        "\t\t<filename>tone.wav</filename>\n"
        "\t</audio>\n"
        "</track>\n");
    fclose(f);
    return 0;
}

// oaml 内部 verbose 开关（oamlBase::ReadInternalDefs("oamlInternal.defs")）
static int write_internal_defs(const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    fprintf(f, "<base>\n\t<verbose>1</verbose>\n</base>\n");
    fclose(f);
    return 0;
}

int main() {
    oamlApi oaml;
    printf("oaml version: %s\n", oaml.GetVersion());
    CHECK(oaml.GetVersion() != NULL && strlen(oaml.GetVersion()) > 0,
          "oamlApi::GetVersion returns non-empty string");

    CHECK(write_wav("tone.wav") == 0, "generate tone.wav (2s 44100Hz sine)");
    CHECK(write_defs("oaml.defs") == 0, "generate oaml.defs");
    write_internal_defs("oamlInternal.defs");

    CHECK(oaml.Init("oaml.defs") == OAML_OK, "Init(oaml.defs) == OAML_OK");
    CHECK(strcmp(oaml.GetDefsFile(), "oaml.defs") == 0, "GetDefsFile round-trip");

    // 必须先设定音频格式再 PlayTrack：否则 OpenFile 的 soxr 重采样分支会按
    // sampleRate=0 计算（totalSamples=0），播放状态机失效（上游 oamlTest 同序：
    // 先 InitAudioDevice 内含 SetAudioFormat，再 PlayTrack）
    oaml.SetAudioFormat(44100, 1, 2, false);

    CHECK(oaml.PlayTrack("music") == OAML_OK, "PlayTrack(music) == OAML_OK");

    // MixToBuffer 直到混出非零采样（异步加载线程完成解码需要时间）
    // 注意 size 语义 = 采样点数（frames*channels，与 RtAudio 回调 nBufferFrames*2 一致）
    int nonzeroIters = -1;
    for (int i = 0; i < 50; i++) {
        short buf[4096];
        memset(buf, 0, sizeof(buf));
        oaml.Update();
        oaml.MixToBuffer(buf, (int)(sizeof(buf) / sizeof(buf[0])));
        int nz = 0;
        for (unsigned k = 0; k < sizeof(buf) / sizeof(buf[0]); k++)
            if (buf[k] != 0) nz++;
        if (nz > 1000) { nonzeroIters = i; break; }
        usleep(100 * 1000);
    }
    printf("mixed nonzero after %d iterations\n", nonzeroIters);
    CHECK(nonzeroIters >= 0, "MixToBuffer produces real decoded audio (non-silence)");

    CHECK(oaml.IsPlaying(), "IsPlaying() == true while main loop playing");
    CHECK(oaml.IsTrackPlaying("music"), "IsTrackPlaying(music) == true");
    const char *info = oaml.GetPlayingInfo();
    printf("playing info: %s\n", info ? info : "(null)");
    CHECK(info != NULL && strstr(info, "music") != NULL,
          "GetPlayingInfo reports the playing track");

    oaml.StopPlaying();
    CHECK(!oaml.IsPlaying(), "IsPlaying() == false after StopPlaying");

    oaml.Shutdown();
    printf("----\n");
    printf("oaml consumer test: %d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
