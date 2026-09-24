/* consumer_vgm_to_wav — 消费者用例：下游“VGM→WAV 音乐转换器”场景。
 *
 * 端到端走完真实消费链路，覆盖全部四个子库与依赖：
 *   zlib（直接 gzwrite 生成 .vgz 夹具）
 *   → vgm-utils FileLoader（gzip 魔数检测 + 透明解压）
 *   → vgm-player PlayerA/VGMPlayer（加载、播放、渲染）
 *   → vgm-emu SN76496（实际发声）
 *   → 写出标准 RIFF/WAVE 文件后回读逐字段校验。
 *
 * 与 test.cpp 的区别：test.cpp 逐 API 断言；本用例按下游应用的真实
 * 使用方式（造文件→加载→整段渲染→落盘→回读校验）组织，并额外覆盖
 * gzip 压缩 VGM（.vgz）输入路径与 vgm-utils 对 zlib 的运行时消费。
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include <zlib.h>

#include "stdtype.h"
#include "player/playerbase.hpp"
#include "player/vgmplayer.hpp"
#include "player/playera.hpp"
#include "utils/DataLoader.h"
#include "utils/FileLoader.h"

static int failures = 0;

#define CHECK(cond, msg)                                          \
    do {                                                          \
        if (!(cond)) {                                            \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
            failures++;                                           \
        } else {                                                  \
            printf("ok: %s\n", msg);                              \
        }                                                         \
    } while (0)

/* 与 test.cpp 相同的最小 VGM 1.50：SN76496 单音 4330 ticks（~98ms） */
static void make_minimal_vgm(std::vector<unsigned char>& out)
{
    const unsigned char data[] = {
        0x50, 0x8F,       /* latch tone ch0, freq low nibble 0xF        */
        0x50, 0x3F,       /* freq high 6 bits -> 10-bit freq 0x3FF      */
        0x50, 0x90,       /* latch vol ch0, attenuation 0 = loudest     */
        0x61, 0xAA, 0x10, /* wait 0x10AA = 4266 samples                 */
        0x61, 0x40, 0x00, /* wait 0x0040 =   64 samples                 */
        0x66              /* end of sound data                          */
    };
    out.assign(0x40, 0x00);
    out[0] = 'V'; out[1] = 'g'; out[2] = 'm'; out[3] = ' ';
    out[8] = 0x50; out[9] = 0x01;               /* version 0x0150 (1.50) */
    out[0x0C] = 0x99; out[0x0D] = 0x9E; out[0x0E] = 0x36; out[0x0F] = 0x00; /* SN76489 clock 3579545 = 0x369E99 */
    out[0x18] = 0xEA; out[0x19] = 0x10;         /* total samples 4330 = 0x10EA */
    out[0x24] = 60;                             /* rate 60 Hz */
    out[0x28] = 0x09;                           /* PSG feedback 9 */
    out[0x2A] = 16;                             /* PSG shift reg width */
    out[0x34] = 0x0C;                           /* data offset (rel 0x34) -> 0x40 */
    out.insert(out.end(), data, data + sizeof(data));
    unsigned eofOff = (unsigned)(out.size() - 0x04);
    out[4] = (unsigned char)(eofOff & 0xFF);
    out[5] = (unsigned char)((eofOff >> 8) & 0xFF);
    out[6] = (unsigned char)((eofOff >> 16) & 0xFF);
    out[7] = (unsigned char)((eofOff >> 24) & 0xFF);
}

static void put_u16le(unsigned char* p, unsigned v)
{
    p[0] = (unsigned char)(v & 0xFF);
    p[1] = (unsigned char)((v >> 8) & 0xFF);
}

static void put_u32le(unsigned char* p, unsigned v)
{
    put_u16le(p, v & 0xFFFF);
    put_u16le(p + 2, (v >> 16) & 0xFFFF);
}

static unsigned get_u32le(const unsigned char* p)
{
    return (unsigned)p[0] | ((unsigned)p[1] << 8) |
           ((unsigned)p[2] << 16) | ((unsigned)p[3] << 24);
}

static unsigned get_u16le(const unsigned char* p)
{
    return (unsigned)p[0] | ((unsigned)p[1] << 8);
}

int main(void)
{
    const char* vgzPath = "consumer_min.vgz";
    const char* wavPath = "consumer_out.wav";
    const UINT32 EXPECT_TICKS = 4330;   /* VGM 头 total samples */

    printf("== libvgm consumer: VGM(.vgz) -> WAV ==\n");

    /* ---- 1. 用打包的 zlib 直接生成 gzip 压缩 VGM 夹具 ---- */
    std::vector<unsigned char> vgm;
    make_minimal_vgm(vgm);
    gzFile gz = gzopen(vgzPath, "wb");
    CHECK(gz != NULL, "zlib: gzopen fixture for writing");
    if (!gz)
        return 1;
    int w = gzwrite(gz, vgm.data(), (unsigned)vgm.size());
    CHECK(w == (int)vgm.size(), "zlib: gzwrite full VGM payload");
    CHECK(gzclose(gz) == Z_OK, "zlib: gzclose fixture");
    if (w != (int)vgm.size())
        return 1;

    /* ---- 2. FileLoader 加载 .vgz（gzip 魔数检测 + 透明解压） ---- */
    DATA_LOADER* loader = FileLoader_Init(vgzPath);
    CHECK(loader != NULL, "vgm-utils: FileLoader_Init on .vgz");
    if (!loader)
        return 1;
    DataLoader_SetPreloadBytes(loader, 0x100);
    CHECK(DataLoader_Load(loader) == 0, "vgm-utils: DataLoader_Load inflates gzip");

    /* ---- 3. PlayerA 整段渲染 ---- */
    PlayerA player;
    player.RegisterPlayerEngine(new VGMPlayer);
    CHECK(player.SetOutputSettings(44100, 2, 16, 2048) == 0,
          "vgm-player: SetOutputSettings(44100, 2ch, 16bit)");
    {
        PlayerA::Config pCfg = player.GetConfiguration();
        pCfg.masterVol = 0x10000;
        pCfg.loopCount = 1;
        pCfg.fadeSmpls = 0;
        pCfg.endSilenceSmpls = 0;
        pCfg.pbSpeed = 1.0;
        player.SetConfiguration(pCfg);
    }
    CHECK(player.LoadFile(loader) == 0, "vgm-player: LoadFile via gzip input path");
    CHECK(dynamic_cast<VGMPlayer*>(player.GetPlayer()) != NULL,
          "vgm-player: VGMPlayer auto-selected for compressed .vgz");
    CHECK(player.Start() == 0, "vgm-player: Start");

    const UINT32 framesPerCall = 1024;
    std::vector<INT16> pcm;
    for (UINT32 iter = 0; iter < 20; iter++) {
        INT16 buf[2048];
        UINT32 gotBytes = player.Render(framesPerCall * 2 * sizeof(INT16), buf);
        UINT32 gotFrames = gotBytes / (2 * sizeof(INT16));
        pcm.insert(pcm.end(), buf, buf + gotFrames * 2);
        if (player.GetState() & PLAYSTATE_FIN)
            break;
    }
    UINT32 totalFrames = (UINT32)(pcm.size() / 2);
    printf("rendered %u frames (%u ticks expected), state 0x%02X\n",
           totalFrames, EXPECT_TICKS, player.GetState());
    CHECK(totalFrames >= EXPECT_TICKS - 128 && totalFrames <= EXPECT_TICKS + 4096,
          "vgm-emu/player: rendered frame count matches VGM total ticks");
    CHECK(player.Stop() == 0, "vgm-player: Stop");

    /* ---- 4. 写标准 RIFF/WAVE（16bit 立体声 PCM，44 字节头） ---- */
    UINT32 dataSize = (UINT32)(pcm.size() * sizeof(INT16));
    {
        FILE* f = fopen(wavPath, "wb");
        CHECK(f != NULL, "consumer: create WAV output file");
        if (!f)
            return 1;
        unsigned char hdr[44];
        memcpy(hdr + 0, "RIFF", 4);
        put_u32le(hdr + 4, 36 + dataSize);
        memcpy(hdr + 8, "WAVE", 4);
        memcpy(hdr + 12, "fmt ", 4);
        put_u32le(hdr + 16, 16);          /* fmt chunk size */
        put_u16le(hdr + 20, 1);           /* PCM */
        put_u16le(hdr + 22, 2);           /* channels */
        put_u32le(hdr + 24, 44100);       /* sample rate */
        put_u32le(hdr + 28, 44100 * 4);   /* byte rate */
        put_u16le(hdr + 32, 4);           /* block align */
        put_u16le(hdr + 34, 16);          /* bits per sample */
        memcpy(hdr + 36, "data", 4);
        put_u32le(hdr + 40, dataSize);
        fwrite(hdr, 1, 44, f);
        fwrite(pcm.data(), sizeof(INT16), pcm.size(), f);
        fclose(f);
    }

    /* ---- 5. 回读逐字段校验（下游拿到的 WAV 必须可独立解析） ---- */
    {
        FILE* f = fopen(wavPath, "rb");
        CHECK(f != NULL, "consumer: reopen WAV for verification");
        if (!f)
            return 1;
        unsigned char hdr[44];
        CHECK(fread(hdr, 1, 44, f) == 44, "WAV: 44-byte header present");
        CHECK(memcmp(hdr + 0, "RIFF", 4) == 0 && memcmp(hdr + 8, "WAVE", 4) == 0,
              "WAV: RIFF/WAVE magic");
        CHECK(memcmp(hdr + 12, "fmt ", 4) == 0 && memcmp(hdr + 36, "data", 4) == 0,
              "WAV: fmt/data chunk layout");
        CHECK(get_u16le(hdr + 20) == 1 && get_u16le(hdr + 22) == 2 &&
              get_u32le(hdr + 24) == 44100 && get_u16le(hdr + 34) == 16,
              "WAV: PCM 2ch 44100Hz 16bit fields");
        CHECK(get_u32le(hdr + 40) == dataSize &&
              get_u32le(hdr + 4) == 36 + dataSize,
              "WAV: chunk sizes consistent with rendered bytes");
        std::vector<INT16> back(pcm.size());
        CHECK(fread(back.data(), sizeof(INT16), back.size(), f) == back.size(),
              "WAV: data chunk readable in full");
        fclose(f);
        UINT32 nonZero = 0;
        for (size_t i = 0; i < back.size(); i++)
            if (back[i] != 0)
                nonZero++;
        CHECK(nonZero > 100, "WAV: rendered audio is non-silent");
    }

    /* ---- 6. 清理 ---- */
    player.UnloadFile();
    DataLoader_Deinit(loader);

    if (failures) {
        fprintf(stderr, "%d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("PASS: consumer VGM(.vgz) -> WAV pipeline over libvgm + zlib\n");
    return 0;
}
