/* test_libvgm — consumer-level verification of the four libvgm libraries.
 *
 * Part 1 (vgm-emu, C API): start an SN76496 core, latch a loud low tone,
 *        render one second via devDef->Update(), assert non-silent output.
 * Part 2 (vgm-player + vgm-utils + zlib): generate a minimal VGM 1.50
 *        file on disk, load via FileLoader + PlayerA, render 16-bit stereo
 *        frames, assert VGMPlayer engine selection and non-silent audio.
 *
 * Modeled on upstream emutest.c (Part 1) and vgm2wav.cpp (Part 2).
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "stdtype.h"
#include "emu/EmuStructs.h"
#include "emu/SoundEmu.h"
#include "emu/SoundDevs.h"
#include "emu/cores/sn764intf.h"

#include "player/playerbase.hpp"
#include "player/vgmplayer.hpp"
#include "player/playera.hpp"
#include "utils/DataLoader.h"
#include "utils/FileLoader.h"

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (!(cond)) {                                          \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
            failures++;                                         \
        } else {                                                \
            printf("ok: %s\n", msg);                            \
        }                                                       \
    } while (0)

/* ---------- Part 1: vgm-emu direct SN76496 render (from emutest.c) ---------- */
static int test_emu(void)
{
    DEV_GEN_CFG devCfg;
    SN76496_CFG snCfg;
    DEV_INFO snDefInf;
    DEVFUNC_WRITE_A8D8 snWrite;
    UINT8 retVal;
    UINT32 smplCount, curSmpl, nonZero;
    DEV_SMPL* smplData[2];

    devCfg.emuCore = 0;    /* default core */
    devCfg.srMode = DEVRI_SRMODE_NATIVE;
    devCfg.flags = 0x00;
    devCfg.clock = 3579545;
    devCfg.smplRate = 44100;
    snCfg._genCfg = devCfg;
    snCfg.shiftRegWidth = 0x10;
    snCfg.noiseTaps = 0x09;
    snCfg.negate = 1;
    snCfg.stereo = 1;
    snCfg.clkDiv = 8;
    snCfg.segaPSG = 0;
    snCfg.t6w28_tone = NULL;

    retVal = SndEmu_Start(DEVID_SN76496, (DEV_GEN_CFG*)&snCfg, &snDefInf);
    CHECK(retVal == 0, "SndEmu_Start(SN76496) returns 0");
    if (retVal != 0)
        return failures;

    CHECK(snDefInf.devDef != NULL && snDefInf.devDef->Reset != NULL &&
          snDefInf.devDef->Update != NULL, "SN76496 device def has Reset/Update");
    CHECK(snDefInf.sampleRate > 0, "device reports positive sample rate");

    snDefInf.devDef->Reset(snDefInf.dataPtr);
    retVal = SndEmu_GetDeviceFunc(snDefInf.devDef, RWF_REGISTER | RWF_WRITE,
                                  DEVRW_A8D8, 0, (void**)&snWrite);
    CHECK(retVal == 0 && snWrite != NULL, "got A8D8 register write function");
    if (retVal != 0 || snWrite == NULL) {
        SndEmu_Stop(&snDefInf);
        return failures;
    }

    /* latch channel 0 tone frequency 0x3FF (lowest tone ~109 Hz, loud) */
    snWrite(snDefInf.dataPtr, 1, 0xDE);          /* ch1 volume -> quiet  */
    snWrite(snDefInf.dataPtr, 0, (0x8 << 4) | 0x0F); /* latch tone ch0, low nibble */
    snWrite(snDefInf.dataPtr, 0, 0x3F);          /* tone high 6 bits */
    snWrite(snDefInf.dataPtr, 0, (0x9 << 4) | 0x00); /* ch0 volume attenuation 0 = loudest */
    snWrite(snDefInf.dataPtr, 0, 0xE0 | 0x00);

    smplCount = snDefInf.sampleRate;             /* one second */
    smplData[0] = (DEV_SMPL*)malloc(smplCount * sizeof(DEV_SMPL));
    smplData[1] = (DEV_SMPL*)malloc(smplCount * sizeof(DEV_SMPL));
    memset(smplData[0], 0, smplCount * sizeof(DEV_SMPL));
    memset(smplData[1], 0, smplCount * sizeof(DEV_SMPL));
    snDefInf.devDef->Update(snDefInf.dataPtr, smplCount, smplData);

    nonZero = 0;
    for (curSmpl = 0; curSmpl < smplCount; curSmpl++) {
        if (smplData[0][curSmpl] != 0)
            nonZero++;
    }
    CHECK(nonZero > 100, "SN76496 render is non-silent");

    free(smplData[0]);
    free(smplData[1]);
    retVal = SndEmu_Stop(&snDefInf);
    CHECK(retVal == 0, "SndEmu_Stop returns 0");
    return failures;
}

/* ---------- Part 2: PlayerA renders a generated minimal VGM ---------- */

/* VGM 1.50: 0x40-byte header + SN76489 commands, one low loud tone for
 * 4330 ticks (~98 ms at 44.1 kHz). */
static void make_minimal_vgm(std::vector<unsigned char>& out)
{
    const unsigned char data[] = {
        0x50, 0x8F,      /* latch tone ch0, freq low nibble 0xF          */
        0x50, 0x3F,      /* freq high 6 bits -> 10-bit freq 0x3FF        */
        0x50, 0x90,      /* latch vol ch0, attenuation 0 = loudest       */
        0x61, 0xAA, 0x10,/* wait 0x10AA = 4266 samples                   */
        0x61, 0x40, 0x00,/* wait 0x0040 =   64 samples                   */
        0x66             /* end of sound data                            */
    };
    out.assign(0x40, 0x00);
    out[0] = 'V'; out[1] = 'g'; out[2] = 'm'; out[3] = ' ';
    /* EOF offset (relative to 0x04) = total size - 4, filled below */
    out[8] = 0x50; out[9] = 0x01;               /* version 0x0150 (1.50) */
    out[0x0C] = 0x99; out[0x0D] = 0x9E; out[0x0E] = 0x36; out[0x0F] = 0x00; /* SN76489 clock 3579545 = 0x369E99 */
    out[0x18] = 0xEA; out[0x19] = 0x10;         /* total samples 4330 = 0x10EA */
    out[0x24] = 60;                             /* rate 60 Hz */
    out[0x28] = 0x09;                           /* PSG feedback 9 */
    out[0x2A] = 16;                             /* PSG shift reg width */
    out[0x34] = 0x0C;                           /* data offset (rel 0x34) -> 0x40 */
    out.insert(out.end(), data, data + sizeof(data));
    /* patch EOF offset */
    unsigned eofOff = (unsigned)(out.size() - 0x04);
    out[4] = (unsigned char)(eofOff & 0xFF);
    out[5] = (unsigned char)((eofOff >> 8) & 0xFF);
    out[6] = (unsigned char)((eofOff >> 16) & 0xFF);
    out[7] = (unsigned char)((eofOff >> 24) & 0xFF);
}

static int test_player(void)
{
    const char* vgmPath = "test_min.vgm";

    {
        std::vector<unsigned char> vgm;
        make_minimal_vgm(vgm);
        FILE* f = fopen(vgmPath, "wb");
        if (!f) {
            fprintf(stderr, "FAIL: cannot write %s\n", vgmPath);
            failures++;
            return failures;
        }
        fwrite(vgm.data(), 1, vgm.size(), f);
        fclose(f);
    }

    PlayerA player;
    player.RegisterPlayerEngine(new VGMPlayer);
    CHECK(player.GetRegisteredPlayers().size() == 1, "VGMPlayer engine registered");

    CHECK(player.SetOutputSettings(44100, 2, 16, 2048) == 0,
          "SetOutputSettings(44100, 2ch, 16bit) accepted");
    {
        PlayerA::Config pCfg = player.GetConfiguration();
        pCfg.masterVol = 0x10000;   /* 1.0 */
        pCfg.loopCount = 1;
        pCfg.fadeSmpls = 0;
        pCfg.endSilenceSmpls = 0;
        pCfg.pbSpeed = 1.0;
        player.SetConfiguration(pCfg);
    }

    DATA_LOADER* loader = FileLoader_Init(vgmPath);
    CHECK(loader != NULL, "FileLoader_Init succeeds");
    if (!loader)
        return failures;
    DataLoader_SetPreloadBytes(loader, 0x100);
    CHECK(DataLoader_Load(loader) == 0, "DataLoader_Load succeeds");
    CHECK(player.LoadFile(loader) == 0, "PlayerA::LoadFile accepts minimal VGM");
    if (player.GetPlayer() == NULL) {
        fprintf(stderr, "FAIL: no player engine selected\n");
        failures++;
        DataLoader_Deinit(loader);
        return failures;
    }
    VGMPlayer* vgm = dynamic_cast<VGMPlayer*>(player.GetPlayer());
    CHECK(vgm != NULL, "VGMPlayer engine auto-selected for .vgm");
    if (!vgm) {
        player.UnloadFile();
        DataLoader_Deinit(loader);
        return failures;
    }

    CHECK(player.Start() == 0, "PlayerA::Start succeeds");
    CHECK(vgm->GetTotalPlayTicks(1) > 0, "VGM reports positive total ticks");

    /* render loop: file is ~4330 frames; cap at 20480 frames (~0.46 s) */
    const UINT32 framesPerCall = 1024;
    std::vector<INT16> buf(framesPerCall * 2);
    UINT32 totalFrames = 0, nonZeroSamples = 0, iter;
    for (iter = 0; iter < 20; iter++) {
        UINT32 gotBytes;
        memset(buf.data(), 0, buf.size() * sizeof(INT16));
        gotBytes = player.Render(framesPerCall * 2 * sizeof(INT16), buf.data());
        UINT32 gotFrames = gotBytes / (2 * sizeof(INT16));
        if (player.GetState() & PLAYSTATE_FIN)
            break;
        for (UINT32 i = 0; i < gotFrames * 2; i++) {
            if (buf[i] != 0)
                nonZeroSamples++;
        }
        totalFrames += gotFrames;
    }
    printf("rendered %u frames, %u non-zero samples, final state 0x%02X\n",
           totalFrames, nonZeroSamples, player.GetState());
    CHECK(totalFrames > 0, "PlayerA::Render produced frames");
    CHECK(nonZeroSamples > 100, "PlayerA::Render output is non-silent");

    CHECK(player.Stop() == 0, "PlayerA::Stop succeeds");
    player.UnloadFile();
    DataLoader_Deinit(loader);

    return failures;
}

int main(void)
{
    printf("== libvgm test_package ==\n");
    test_emu();
    test_player();
    if (failures) {
        fprintf(stderr, "%d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("PASS: libvgm emu + player APIs functional\n");
    return 0;
}
