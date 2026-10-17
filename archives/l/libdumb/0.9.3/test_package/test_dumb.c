/* Deterministic, self-authored MOD fixture: a looping nonzero sample and C-3. */
#include <dumb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)

static int check_io(void)
{
    const char bytes[] = {1, 2, 3, 4, 5, 6};
    DUMBFILE *f = dumbfile_open_memory(bytes, sizeof(bytes));
    CHECK(f != NULL);
    CHECK(dumbfile_igetw(f) == 513);
    CHECK(dumbfile_mgetw(f) == 772);
    CHECK(dumbfile_pos(f) == 4);
    CHECK(dumbfile_getc(f) == 5);
    CHECK(dumbfile_skip(f, 1) == 0);
    CHECK(dumbfile_getc(f) < 0);
    CHECK(dumbfile_error(f));
    dumbfile_close(f);
    puts("PASS memory_io");
    return 0;
}

static int check_mod(void)
{
    unsigned char mod[1084 + 1024 + 64] = {0};
    short pcm[4096 * 2];
    DUMBFILE *f;
    DUH *duh;
    DUH_SIGRENDERER *sr;
    long count, i;
    int nonzero = 0;
    memcpy(mod, "Harmony decoder", 15);
    mod[42] = 0; mod[43] = 32; /* Sample length: 32 big endian words. */
    mod[45] = 64;              /* Sample volume. */
    mod[49] = 32;              /* Loop length: 32 words. */
    mod[950] = 1;
    memcpy(mod + 1080, "M.K.", 4);
    mod[1084] = 1; mod[1085] = 0xac; mod[1086] = 0x10; /* Period 428, sample 1. */
    for (i = 0; i < 64; ++i) mod[2108 + i] = i < 32 ? 80 : (unsigned char)-80;
    f = dumbfile_open_memory((const char *)mod, sizeof(mod));
    CHECK(f != NULL);
    duh = dumb_read_mod(f);
    dumbfile_close(f);
    CHECK(duh != NULL);
    CHECK(duh_get_length(duh) > 0);
    puts("PASS mod_decode");
    sr = duh_start_sigrenderer(duh, 0, 2, 0);
    CHECK(sr != NULL);
    CHECK(duh_sigrenderer_get_n_channels(sr) == 2);
    memset(pcm, 0x55, sizeof(pcm));
    count = duh_render(sr, 16, 0, 1.0f, 65536.0f / 44100.0f, 4096, pcm);
    CHECK(count == 4096);
    for (i = 0; i < count * 2; ++i) if (pcm[i] != 0) nonzero = 1;
    CHECK(nonzero);
    CHECK(duh_sigrenderer_get_position(sr) > 0);
    puts("PASS stereo_pcm_render");
    duh_end_sigrenderer(sr);
    unload_duh(duh);
    return 0;
}

static int check_errors(void)
{
    const char invalid[] = "invalid";
    DUMBFILE *f = dumbfile_open_memory(invalid, sizeof(invalid));
    CHECK(f != NULL);
    CHECK(dumb_read_mod(f) == NULL);
    dumbfile_close(f);
    CHECK(dumb_load_mod("missing-libdumb-test.mod") == NULL);
    puts("PASS invalid_and_missing_module");
    return 0;
}

int main(void)
{
    int result;
    dumb_register_stdfiles();
    result = check_io() || check_mod() || check_errors();
    dumb_exit();
    return result;
}
