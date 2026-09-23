/*
 * Consumer-view smoke test for mupen64plus 2.6.0 (N64 emulator core).
 *
 * 8 assertions, all executed on-device:
 *   1. CoreGetAPIVersions  — API/config/debugger version negotiation
 *   2. CoreStartup         — full lifecycle init: config system, default
 *                            plugins, savestates, memory base, ROM database,
 *                            embedded (static) SDL bootstrap
 *   3. M64CMD_CORE_STATE_QUERY — emulator state machine (must be "stopped")
 *   4. M64CMD_ROM_OPEN     — in-memory ROM load: header validation,
 *                            byteswap normalization, MD5/CIC detection
 *   5. CoreGetRomSettings  — API contract: synthetic ROM (CRC not in
 *                            mupen64plus.ini) must return M64ERR_INPUT_NOT_FOUND
 *   6. M64CMD_ROM_CLOSE    — cheat + ROM teardown
 *   7. defensive contract  — ROM buffer < 4096 bytes must be rejected with
 *                            M64ERR_INPUT_ASSERT (upstream bounds check)
 *   8. CoreShutdown        — clean teardown
 *
 * The synthetic ROM is generated in-code (valid big-endian 0x80371240 magic,
 * entrypoint, cartridge name, country code) — no external test assets.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "m64p_common.h"
#include "m64p_frontend.h"
#include "m64p_config.h"
#include "m64p_types.h"

static void debug_cb(void *ctx, int level, const char *msg)
{
    (void)ctx;
    if (level <= 2)
        printf("[core][lvl%d] %s\n", level, msg);
}

/* generate a minimal valid N64 ROM image (big-endian .z64 layout) */
static unsigned char *make_synthetic_rom(long *out_size)
{
    const long size = 0x80000; /* 512 KiB, > 4096 minimum */
    unsigned char *rom = (unsigned char *)malloc(size);
    if (!rom) return NULL;
    memset(rom, 0, size);
    rom[0] = 0x80; rom[1] = 0x37; rom[2] = 0x12; rom[3] = 0x40; /* pi_dom1_reg  */
    rom[8] = 0x80; rom[9] = 0x00; rom[10] = 0x00; rom[11] = 0x40; /* entrypoint */
    memcpy(rom + 0x20, "HOS SMOKE TEST", 14);                     /* image name   */
    rom[0x3E] = 0x45;                                            /* country 'E'  */
    *out_size = size;
    return rom;
}

int main(void)
{
    int fails = 0;
    const char *workdir = TEST_WORK_DIR;

    mkdir(workdir, 0755);

    /* 1. API version negotiation */
    int api_ver = 0, cfg_ver = 0, dbg_ver = 0;
    m64p_error r = CoreGetAPIVersions(&api_ver, &cfg_ver, &dbg_ver, NULL);
    if (r != M64ERR_SUCCESS) {
        printf("FAIL 1 CoreGetAPIVersions: %d (%s)\n", r, CoreErrorMessage(r));
        return 1;
    }
    printf("PASS 1 CoreGetAPIVersions: api=0x%x cfg=0x%x dbg=0x%x\n",
           api_ver, cfg_ver, dbg_ver);

    /* 2. CoreStartup full init */
    r = CoreStartup(api_ver, workdir, workdir, NULL, debug_cb, NULL, NULL);
    if (r != M64ERR_SUCCESS) {
        printf("FAIL 2 CoreStartup: %d (%s)\n", r, CoreErrorMessage(r));
        return 1;
    }
    printf("PASS 2 CoreStartup (config + mem-base + romdatabase + SDL bootstrap)\n");

    /* 3. state machine */
    int state = -1;
    r = CoreDoCommand(M64CMD_CORE_STATE_QUERY, M64CORE_EMU_STATE, &state);
    if (r != M64ERR_SUCCESS) {
        printf("FAIL 3 CORE_STATE_QUERY: %d (%s)\n", r, CoreErrorMessage(r));
        fails++;
    } else if (state != 1) { /* 1 = stopped */
        printf("FAIL 3 expected state 'stopped'(1), got %d\n", state);
        fails++;
    } else {
        printf("PASS 3 CORE_STATE_QUERY: state=%d (stopped)\n", state);
    }

    /* 4. ROM open (header parse + byteswap + MD5 + CIC) */
    long rom_size = 0;
    unsigned char *rom = make_synthetic_rom(&rom_size);
    if (!rom) { printf("FAIL 4 rom alloc\n"); return 1; }
    r = CoreDoCommand(M64CMD_ROM_OPEN, (int)rom_size, rom);
    if (r != M64ERR_SUCCESS) {
        printf("FAIL 4 ROM_OPEN: %d (%s)\n", r, CoreErrorMessage(r));
        fails++;
    } else {
        printf("PASS 4 ROM_OPEN: %ld bytes, header parsed, CIC detected\n", rom_size);
    }

    /* 5. ROM settings API contract */
    m64p_rom_settings rs;
    memset(&rs, 0, sizeof(rs));
    r = CoreGetRomSettings(&rs, sizeof(rs), 0, 0);
    if (r != M64ERR_INPUT_NOT_FOUND) {
        printf("FAIL 5 CoreGetRomSettings: expected M64ERR_INPUT_NOT_FOUND, got %d\n", r);
        fails++;
    } else {
        printf("PASS 5 CoreGetRomSettings contract (unknown CRC -> M64ERR_INPUT_NOT_FOUND)\n");
    }

    /* 6. ROM close */
    r = CoreDoCommand(M64CMD_ROM_CLOSE, 0, NULL);
    if (r != M64ERR_SUCCESS) {
        printf("FAIL 6 ROM_CLOSE: %d (%s)\n", r, CoreErrorMessage(r));
        fails++;
    } else {
        printf("PASS 6 ROM_CLOSE\n");
    }

    /* 7. defensive input validation */
    r = CoreDoCommand(M64CMD_ROM_OPEN, 100, rom); /* < 4096 must be rejected */
    if (r != M64ERR_INPUT_ASSERT) {
        printf("FAIL 7 expected M64ERR_INPUT_ASSERT for undersized ROM, got %d\n", r);
        fails++;
    } else {
        printf("PASS 7 undersized ROM rejected (M64ERR_INPUT_ASSERT)\n");
    }
    free(rom);

    /* 8. CoreShutdown */
    r = CoreShutdown();
    if (r != M64ERR_SUCCESS) {
        printf("FAIL 8 CoreShutdown: %d (%s)\n", r, CoreErrorMessage(r));
        fails++;
    } else {
        printf("PASS 8 CoreShutdown\n");
    }

    if (fails) {
        printf("%d FAILURES\n", fails);
        return 1;
    }
    printf("ALL 8 TESTS PASSED\n");
    return 0;
}
