// zmusic 1.3.0 consumer test — 鸿蒙特有测试（上游无 tests/ 目录）
//
// 端到端验证 ZMusic C API 在 OHOS aarch64 上的真实可用性:
//   1. ZMusic_GetConfiguration()            库初始化与配置枚举
//   2. ZMusic_OpenSongMem()                 内存 MOD 解码（内置 DUMB 解码器）
//   3. ZMusic_GetStreamInfo()               流元信息（采样率/声道）
//   4. ZMusic_Start() + ZMusic_FillStream() 播放并渲染出非零 PCM
//   5. ZMusic_IdentifyMIDIType()            MIDI 格式识别
//
// 测试数据为内嵌构造的最小 ProTracker MOD（1 段正弦波采样 + 1 个音符），
// 不依赖外部文件，可离线重复执行。
#include <zmusic.h>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

static int failures = 0;

#define CHECK(cond, msg)                                          \
    do {                                                          \
        if (!(cond)) { printf("FAIL: %s\n", msg); failures++; }    \
        else { printf("ok  : %s\n", msg); }                       \
    } while (0)

// 布局: 20B 标题 | 31*30B 采样头 | 1B 曲长 | 1B 0x7F | 128B 序列表 | "M.K." | pattern | 采样数据
static std::vector<uint8_t> make_mod()
{
    const size_t pat_off = 1084;
    const size_t pat_size = 64 * 4 * 4;             // 64 行 * 4 通道 * 4 字节
    const size_t smp_off = pat_off + pat_size;
    const uint32_t smp_len_bytes = 128;             // 64 words
    std::vector<uint8_t> d(smp_off + smp_len_bytes, 0);

    std::memcpy(d.data(), "zmusic ohos smoke test", 22);         // 标题
    d[950] = 1;                                                   // 曲长 = 1
    d[951] = 0x7F;                                                // 兼容标记
    d[952] = 0;                                                   // 序列表[0] = pattern 0
    std::memcpy(d.data() + 1080, "M.K.", 4);                      // 4 通道标记

    // 采样 0 头部（30 字节，位于 [20,50)）
    uint8_t* sh = d.data() + 20;
    std::memcpy(sh, "sine", 4);
    sh[22] = (uint8_t)((smp_len_bytes / 2) >> 8);                 // length(words) 高字节
    sh[23] = (uint8_t)((smp_len_bytes / 2) & 0xFF);               // length(words) 低字节
    sh[24] = 0;                                                   // finetune
    sh[25] = 64;                                                  // volume
    sh[26] = 0; sh[27] = 0;                                       // loop start
    sh[28] = sh[22]; sh[29] = sh[23];                             // loop length = 全长

    // pattern 第 0 行 / 通道 0：C-3 (period 428)，采样 1，无效果
    const int period = 428;
    d[pat_off + 0] = (uint8_t)((period >> 8) & 0x0F);
    d[pat_off + 1] = (uint8_t)(period & 0xFF);
    d[pat_off + 2] = 0x10;                                        // 采样号低 4 位 = 1
    d[pat_off + 3] = 0;

    // 采样数据：8-bit 有符号正弦波
    // 注意：不使用 M_PI —— 它不是 ISO C/C++ 标准符号，musl 在严格模式下
    // （-std=c++17 且不定义 _GNU_SOURCE）不提供该宏，此处自给常量保证可移植。
    constexpr double kPi = 3.14159265358979323846;
    for (uint32_t i = 0; i < smp_len_bytes; i++)
        d[smp_off + i] = (uint8_t)(int8_t)(std::sin(2.0 * kPi * i / smp_len_bytes) * 100.0);
    return d;
}

int main()
{
    // 1) 配置枚举：库已正确初始化
    const ZMusicConfigurationSetting* cfg = ZMusic_GetConfiguration();
    CHECK(cfg != nullptr, "ZMusic_GetConfiguration() 返回非 NULL");
    int n = 0;
    if (cfg) for (const ZMusicConfigurationSetting* p = cfg; p->name != nullptr; ++p) n++;
    CHECK(n > 0, "配置项数量 > 0");
    printf("     config entries = %d\n", n);

    // 2) 内存 MOD 解码（内置 DUMB 解码器）
    std::vector<uint8_t> mod = make_mod();
    ZMusic_MusicStream song = ZMusic_OpenSongMem(mod.data(), mod.size(), MDEV_DEFAULT, nullptr);
    CHECK(song != nullptr, "ZMusic_OpenSongMem() 打开 MOD 成功");
    if (!song) { printf("   last error: %s\n", ZMusic_GetLastError()); return 1; }

    // 3) 流信息
    SoundStreamInfo info;
    std::memset(&info, 0, sizeof(info));
    ZMusic_GetStreamInfo(song, &info);
    printf("     sampleRate=%d channels=%d bufferSize=%d\n",
           info.mSampleRate, info.mNumChannels, info.mBufferSize);
    CHECK(info.mSampleRate > 0, "ZMusic_GetStreamInfo() 采样率有效");
    CHECK(info.mNumChannels != 0, "ZMusic_GetStreamInfo() 声道数有效");

    // 4) 启动 + 渲染 PCM
    CHECK(ZMusic_Start(song, 0, false) != 0, "ZMusic_Start() 启动播放");
    std::vector<float> pcm(8192, 0.0f);
    zmusic_bool filled = ZMusic_FillStream(song, pcm.data(), (int)(pcm.size() * sizeof(float)));
    CHECK(filled != 0, "ZMusic_FillStream() 渲染 PCM 成功");

    // 渲染结果必须含非零音频，证明解码器 + 混音链路真实工作
    float peak = 0.0f;
    for (float s : pcm) peak = std::fabs(s) > peak ? std::fabs(s) : peak;
    printf("     FillStream -> %d, peak amplitude = %.6f\n", (int)filled, peak);
    CHECK(peak > 0.0f, "渲染出的 PCM 含非零音频数据（DUMB 解码链路可用）");

    ZMusic_Stop(song);
    ZMusic_Close(song);

    // 5) MIDI 类型识别
    uint32_t id[2] = {0, 0};
    std::memcpy(&id[0], "MThd", 4);
    EMIDIType t = ZMusic_IdentifyMIDIType(id, 8);
    CHECK(t == MIDI_MIDI, "ZMusic_IdentifyMIDIType() 识别 MThd 为 MIDI_MIDI");

    printf("\n%s (failures=%d)\n", failures == 0 ? "ALL PASS" : "HAS FAILURES", failures);
    return failures == 0 ? 0 : 1;
}
