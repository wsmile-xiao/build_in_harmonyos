/*
 * waon 0.11 consumer test — HarmonyOS PC (OHOS / aarch64)
 *
 * Exercises the packaged binary end to end: a 440 Hz sine WAV is synthesised
 * here in plain C (no fixtures shipped), transcribed by `waon`, and the
 * resulting Standard MIDI File is parsed byte by byte. Upstream 0.11 has no
 * automated test suite, so this file is the verification surface.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>

#ifndef WAON_BIN
#error "WAON_BIN must be defined by the build"
#endif

#define SR 44100
#define SECS 0.70
#define NSAMP ((int)(SR * SECS))

static int total = 0;
static int failed = 0;

static void check(int cond, const char *what)
{
    total++;
    if (cond)
        printf("ok   %d - %s\n", total, what);
    else {
        printf("NOT OK %d - %s\n", total, what);
        failed++;
    }
}

static void put16(FILE *f, unsigned int v)
{
    fputc((int)(v & 0xff), f);
    fputc((int)((v >> 8) & 0xff), f);
}

static void put32(FILE *f, unsigned long v)
{
    fputc((int)(v & 0xff), f);
    fputc((int)((v >> 8) & 0xff), f);
    fputc((int)((v >> 16) & 0xff), f);
    fputc((int)((v >> 24) & 0xff), f);
}

/* 16-bit mono PCM WAV with a sine at `freq` Hz */
static int write_wav(const char *path, double freq)
{
    int i;
    long data_bytes = (long)NSAMP * 2;
    FILE *f = fopen(path, "wb");
    if (!f)
        return 0;
    fwrite("RIFF", 1, 4, f);
    put32(f, (unsigned long)(36 + data_bytes));
    fwrite("WAVE", 1, 4, f);
    fwrite("fmt ", 1, 4, f);
    put32(f, 16);          /* fmt chunk size            */
    put16(f, 1);           /* PCM                       */
    put16(f, 1);           /* mono                      */
    put32(f, SR);
    put32(f, (unsigned long)(SR * 2));
    put16(f, 2);           /* block align               */
    put16(f, 16);          /* bits per sample           */
    fwrite("data", 1, 4, f);
    put32(f, (unsigned long)data_bytes);
    for (i = 0; i < NSAMP; i++) {
        int s = (int)(0.55 * 32767.0 * sin(2.0 * 3.14159265358979 * freq * i / SR));
        put16(f, (unsigned int)(s & 0xffff));
    }
    fclose(f);
    return 1;
}

static long file_size(const char *p)
{
    struct stat st;
    return stat(p, &st) == 0 ? (long)st.st_size : -1;
}

static int run_cmd(char *buf, size_t sz, const char *fmt, const char *a, const char *b)
{
    snprintf(buf, sz, fmt, a, b);
    fprintf(stderr, "[cmd] %s\n", buf);
    return system(buf);
}

/*
 * Minimal SMF reader: counts note-on / note-off events and records the
 * pitches seen. Handles running status and meta events.
 */
static void parse_midi(const char *path, int *n_notes, int *n_offs,
                       int *min_pitch, int *max_pitch, int *hdr_ok)
{
    unsigned char *img;
    long sz;
    long i;
    FILE *f = fopen(path, "rb");
    *n_notes = *n_offs = *hdr_ok = 0;
    *min_pitch = 128;
    *max_pitch = -1;
    if (!f)
        return;
    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < 22 || sz > (1 << 22)) {
        fclose(f);
        return;
    }
    img = malloc((size_t)sz);
    if (!img || fread(img, 1, (size_t)sz, f) != (size_t)sz) {
        free(img);
        fclose(f);
        return;
    }
    fclose(f);
    *hdr_ok = (memcmp(img, "MThd", 4) == 0 && memcmp(img + 14, "MTrk", 4) == 0);
    i = 22;           /* 14-byte MThd + 8-byte MTrk chunk header */
    {
        int status = 0;
        for (; i + 0 < sz;) {
            /* delta time varint */
            while (i < sz && (img[i] & 0x80))
                i++;
            if (i >= sz)
                break;
            i++;                   /* final byte of the varint            */
            if (i >= sz)
            break;
            if (img[i] & 0x80) {
                status = img[i];
                i++;
            }
            if (status == 0xff) {  /* meta: type, len varint, data         */
                int type;
                unsigned long len = 0;
                if (i + 1 >= sz)
                    break;
                type = img[i++];
                do {
                    if (i >= sz)
                        break;
                    len = (len << 7) | (img[i] & 0x7f);
                } while (img[i++] & 0x80);
                i += (long)len;
                (void)type;
                continue;
            }
            switch (status & 0xf0) {
            case 0x90:             /* note on                              */
                if (i + 1 >= sz)
                    break;
                {
                    int pitch = img[i];
                    int vel = img[i + 1];
                    i += 2;
                    if (vel > 0) {
                        (*n_notes)++;
                        if (pitch < *min_pitch)
                            *min_pitch = pitch;
                        if (pitch > *max_pitch)
                            *max_pitch = pitch;
                    } else
                        (*n_offs)++;
                }
                break;
            case 0x80:             /* note off                             */
                if (i + 1 >= sz)
                    break;
                (*n_offs)++;
                i += 2;
                break;
            case 0xc0:
            case 0xd0:
                i += 1;
                break;
            default:
                i += 2;
                break;
            }
        }
    }
    free(img);
}

int main(void)
{
    char cmd[1200];
    const char *wav = "waon_test_440.wav";
    const char *mid = "waon_test_out.mid";
    long sz;
    int rc;
    int notes = 0, offs = 0, lo = 0, hi = 0, hdr = 0;
    FILE *p;
    char line[512];
    int saw_waon = 0, saw_ver = 0;

    printf("== waon consumer test: %s ==\n", WAON_BIN);

    /* T1 the packaged executable is there and runs */
    snprintf(cmd, sizeof cmd, "\"%s\" -v > waon_ver.txt 2>&1", WAON_BIN);
    rc = system(cmd);
    check(rc != -1, "T1 waon --version executed (not ENOEXEC)");
    p = fopen("waon_ver.txt", "r");
    if (p) {
        while (fgets(line, sizeof line, p)) {
            if (strstr(line, "WaoN"))
                saw_waon = 1;
            if (strstr(line, "0.11"))
                saw_ver = 1;
        }
        fclose(p);
    }
    check(saw_waon, "T1 banner identifies WaoN");
    check(saw_ver, "T1 banner reports version 0.11");

    /* T2 upstream exits non-zero after --version (documented 0.11 behaviour) */
    check(WEXITSTATUS(rc) == 1, "T1 waon --version exits 1 as upstream does");

    /* T3 synthesise the fixture */
    check(write_wav(wav, 440.0), "T3 440 Hz WAV fixture written");
    sz = file_size(wav);
    check(sz == 44 + (long)NSAMP * 2, "T3 WAV length matches header math");

    /* T4 real transcription run */
    rc = run_cmd(cmd, sizeof cmd, "\"%s\" -i \"%s\" -o waon_test_out.mid 2>&1 < /dev/null", WAON_BIN, wav);
    check(rc == 0, "T4 waon transcribes the WAV with exit 0");

    /* T5 a MIDI file came out */
    sz = file_size(mid);
    check(sz > 14, "T5 output MIDI file exists and is non-empty");

    /* T6..T8 parse it */
    parse_midi(mid, &notes, &offs, &lo, &hi, &hdr);
    printf("[info] note-on=%d note-off=%d pitch range=[%d,%d]\n", notes, offs, lo, hi);
    check(hdr == 1, "T6 stream starts with the MThd header");
    check(notes >= 1, "T7 at least one MIDI note-on was emitted");
    check(offs >= 1, "T7 matching note-off (or zero-velocity on) emitted");
    check(notes >= 1 && lo >= 67 && hi <= 71,
          "T8 A440 maps into the expected MIDI note window (67..71)");

    /* T9 error path: a missing input must not succeed */
    rc = run_cmd(cmd, sizeof cmd, "\"%s\" -i no_such_file.wav -o \"%s\" 2>&1 < /dev/null", WAON_BIN, "waon_bad.mid");
    check(rc != 0, "T9 missing input fails instead of pretending success");

    /* T10 stereo fixture also transcribes (snd.c channel path) */
    {
        FILE *f = fopen("waon_test_stereo.wav", "wb");
        int i;
        long data_bytes = (long)NSAMP * 4;
        if (f) {
            fwrite("RIFF", 1, 4, f);
            put32(f, (unsigned long)(36 + data_bytes));
            fwrite("WAVE", 1, 4, f);
            fwrite("fmt ", 1, 4, f);
            put32(f, 16);
            put16(f, 1);
            put16(f, 2);          /* stereo */
            put32(f, SR);
            put32(f, (unsigned long)(SR * 4));
            put16(f, 4);
            put16(f, 16);
            fwrite("data", 1, 4, f);
            put32(f, (unsigned long)data_bytes);
            for (i = 0; i < NSAMP; i++) {
                int l = (int)(0.5 * 32767.0 * sin(2.0 * 3.14159265358979 * 440.0 * i / SR));
                int r = (int)(0.5 * 32767.0 * sin(2.0 * 3.14159265358979 * 660.0 * i / SR));
                put16(f, (unsigned int)(l & 0xffff));
                put16(f, (unsigned int)(r & 0xffff));
            }
            fclose(f);
        }
        rc = run_cmd(cmd, sizeof cmd, "\"%s\" -i waon_test_stereo.wav -o waon_test_stereo.mid 2>&1 < /dev/null", WAON_BIN, NULL);
        check(rc == 0, "T10 stereo WAV transcribes with exit 0");
        check(file_size("waon_test_stereo.mid") > 14, "T10 stereo MIDI output written");
    }

    printf("\n%d/%d checks passed\n", total - failed, total);
    return failed == 0 ? 0 : 1;
}
