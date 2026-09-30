/* libvo-amrwbenc 0.1.3 完整消费者用例（平台 rule12）
 *
 * 不是断言集合，而是把「AMR-WB 编码」这件事真正跑一遍并检查可核对的产物：
 *   ① 生成一段真实 WAV（16 kHz 单声道 16 bit，1 秒双音）
 *   ② 用**交付的** amrwb-enc 命令行工具编码成 #!AMR-WB 码流
 *   ③ 校验码流结构：魔数、帧数（20 ms/帧 → 50 帧）、每帧长度、帧头 FT 字段
 *   ④ 用库的 C API（E_IF_init/E_IF_encode/E_IF_exit）编码同样输入，
 *      与 CLI 产物**逐字节一致**（API 与工具走同一条编码链路）
 *   ⑤ 遍历 9 种 AMR-WB 模式（6.6k~23.85k），逐个校验帧长与文件总长
 *   ⑥ 用同源的参考解码器（opencore-amr）把码流解码回 PCM，与原信号做
 *      延迟搜索后的相关系数/SNR 校验（闭环验证：编出来的码流真的能解码）
 *
 * 用法: test_probe <amrwb-enc 路径> <工作目录>
 */
#include <opencore-amrwb/dec_if.h>

#include <vo-amrwbenc/enc_if.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SAMPLE_RATE 16000
#define SAMPLES 16000          /* 1 秒 */
#define FRAME 320              /* 20 ms */
#define NFRAMES (SAMPLES / FRAME)

/* AMR-WB 各模式的帧长（字节，含 1 字节帧头）——RFC 4867 表中各模式的位数向上取整 + 1 */
static const int MODE_BYTES[9] = {18, 24, 33, 37, 41, 47, 51, 59, 61};
static const int MODE_RATE[9] = {6600, 8850, 12650, 14250, 15850, 18250, 19850, 23050, 23850};

static int g_checks = 0;
static int g_failed = 0;

static void check(int ok, const char *what, const char *detail)
{
    ++g_checks;
    if (!ok) {
        ++g_failed;
    }
    printf("  [%s] %s", ok ? "ok" : "FAIL", what);
    if (detail && detail[0]) {
        printf("  %s", detail);
    }
    printf("\n");
}

static short g_pcm[SAMPLES];

static void gen_pcm(void)
{
    for (int i = 0; i < SAMPLES; ++i) {
        double t = (double)i / SAMPLE_RATE;
        double v = 12000.0 * sin(2 * M_PI * 440.0 * t)
                 + 4000.0 * sin(2 * M_PI * 880.0 * t)
                 + 2000.0 * sin(2 * M_PI * 1320.0 * t);
        g_pcm[i] = (short)v;
    }
}

static int write_wav(const char *path)
{
    FILE *f = fopen(path, "wb");
    if (!f) {
        return 0;
    }
    int data = SAMPLES * 2;
    unsigned char hdr[44] = {'R', 'I', 'F', 'F'};
    int riff = 36 + data;
    memcpy(hdr + 4, &riff, 4);
    memcpy(hdr + 8, "WAVEfmt ", 8);
    int fmt = 16;
    memcpy(hdr + 16, &fmt, 4);
    short pcm = 1, ch = 1;
    memcpy(hdr + 20, &pcm, 2);
    memcpy(hdr + 22, &ch, 2);
    int rate = SAMPLE_RATE;
    memcpy(hdr + 24, &rate, 4);
    int byterate = SAMPLE_RATE * 2;
    memcpy(hdr + 28, &byterate, 4);
    short align = 2, bits = 16;
    memcpy(hdr + 32, &align, 2);
    memcpy(hdr + 34, &bits, 2);
    memcpy(hdr + 36, "data", 4);
    memcpy(hdr + 40, &data, 4);
    fwrite(hdr, 1, 44, f);
    fwrite(g_pcm, 2, SAMPLES, f);
    fclose(f);
    return 1;
}

static long file_size(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        return -1;
    }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fclose(f);
    return n;
}

/* 用库 API 编码整个信号，写出的字节流与 CLI 的格式完全一致（魔数 + 每帧一次 E_IF_encode） */
static int api_encode(const char *out_path, int mode)
{
    FILE *out = fopen(out_path, "wb");
    if (!out) {
        return 0;
    }
    fwrite("#!AMR-WB\n", 1, 9, out);
    void *amr = E_IF_init();
    for (int f = 0; f < NFRAMES; ++f) {
        unsigned char outbuf[500];
        int n = E_IF_encode(amr, mode, g_pcm + f * FRAME, outbuf, 0);
        if (n <= 0) {
            E_IF_exit(amr);
            fclose(out);
            return 0;
        }
        fwrite(outbuf, 1, n, out);
    }
    E_IF_exit(amr);
    fclose(out);
    return 1;
}

/* 逐字节比较两个文件 */
static int files_equal(const char *a, const char *b, long *size_out)
{
    FILE *fa = fopen(a, "rb");
    FILE *fb = fopen(b, "rb");
    if (!fa || !fb) {
        if (fa) fclose(fa);
        if (fb) fclose(fb);
        return 0;
    }
    int same = 1;
    long n = 0;
    for (;;) {
        int ca = fgetc(fa), cb = fgetc(fb);
        if (ca != cb) {
            same = 0;
            break;
        }
        if (ca == EOF) {
            break;
        }
        ++n;
    }
    fclose(fa);
    fclose(fb);
    if (size_out) {
        *size_out = n;
    }
    return same;
}

/* 校验 .awb 结构：魔数 + 帧数 + 每帧长度 + 帧头 FT 字段 */
static int verify_stream(const char *path, int mode, int *frames_out)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        return 0;
    }
    char magic[9];
    if (fread(magic, 1, 9, f) != 9 || memcmp(magic, "#!AMR-WB\n", 9) != 0) {
        fclose(f);
        return 0;
    }
    int frames = 0, bad = 0;
    for (;;) {
        int c = fgetc(f);
        if (c == EOF) {
            break;
        }
        if (c != ((mode << 3) | 0x04)) {   /* 帧头：FT=mode（bits 6..3），低 3 位固定 0b100 */
            ++bad;
            break;
        }
        unsigned char payload[64];
        if (fread(payload, 1, MODE_BYTES[mode] - 1, f) != (size_t)(MODE_BYTES[mode] - 1)) {
            ++bad;
            break;
        }
        ++frames;
    }
    fclose(f);
    if (frames_out) {
        *frames_out = frames;
    }
    return !bad;
}

static double corr_at(const short *a, const short *b, int n, int lag)
{
    double sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
    int m = 0;
    for (int i = 0; i < n; ++i) {
        int j = i + lag;
        if (j < 0 || j >= n) {
            continue;
        }
        double x = a[i], y = b[j];
        sa += x; sb += y; saa += x * x; sbb += y * y; sab += x * y; ++m;
    }
    if (m < 100) {
        return -2.0;
    }
    return (m * sab - sa * sb) / sqrt((m * saa - sa * sa) * (m * sbb - sb * sb));
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <amrwb-enc path> <workdir>\n", argv[0]);
        return 2;
    }
    const char *cli = argv[1];
    const char *dir = argv[2];
    char wav[512], cli_awb[512], api_awb[512], mode_awb[512], cmd[1600];

    printf("libvo-amrwbenc 消费者用例：AMR-WB 编码全流程 + 参考解码器闭环\n");
    snprintf(wav, sizeof(wav), "%s/in16k.wav", dir);
    snprintf(cli_awb, sizeof(cli_awb), "%s/cli.awb", dir);
    snprintf(api_awb, sizeof(api_awb), "%s/api.awb", dir);
    snprintf(mode_awb, sizeof(mode_awb), "%s/mode.awb", dir);

    /* ① 生成真实 WAV */
    gen_pcm();
    check(write_wav(wav) && file_size(wav) == 44 + SAMPLES * 2,
          "生成 16 kHz 单声道 WAV（16000 采样）", wav);

    /* ② 用交付的 CLI 编码 */
    snprintf(cmd, sizeof(cmd), "\"%s\" -r 23850 \"%s\" \"%s\"", cli, wav, cli_awb);
    int rc = system(cmd);
    check(rc == 0 && file_size(cli_awb) == 9 + NFRAMES * MODE_BYTES[8],
          "amrwb-enc -r 23850 编码成功（23.85 kbit/s）",
          "size 期望 3059 字节");

    /* ③ 码流结构 */
    int frames = 0;
    int ok = verify_stream(cli_awb, 8, &frames);
    check(ok && frames == NFRAMES,
          "码流结构：魔数 #!AMR-WB + 50 帧 × 61 字节 + 帧头 FT=8",
          "帧数 50 / 帧长 61");

    /* ④ API 与 CLI 逐字节一致 */
    long n = 0;
    check(api_encode(api_awb, 8) && files_equal(cli_awb, api_awb, &n) && n == 3059,
          "E_IF_* API 编码结果与 CLI 产物逐字节一致", "3059 字节");

    /* ⑤ 9 种模式：帧长与文件总长 */
    int modes_ok = 1, modes_checked = 0;
    for (int m = 0; m < 9; ++m) {
        int mf = 0;
        long want = 9 + (long)NFRAMES * MODE_BYTES[m];
        int good = api_encode(mode_awb, m)
                && file_size(mode_awb) == want
                && verify_stream(mode_awb, m, &mf)
                && mf == NFRAMES;
        if (!good) {
            printf("       mode %d (%d bps) 失败: size=%ld 期望=%ld frames=%d\n",
                   m, MODE_RATE[m], file_size(mode_awb), want, mf);
            modes_ok = 0;
        }
        modes_checked += good;
    }
    check(modes_ok && modes_checked == 9,
          "9 种 AMR-WB 模式全部通过（6.6k/8.85k/12.65k/14.25k/15.85k/18.25k/19.85k/23.05k/23.85k）",
          "帧长 18/24/33/37/41/47/51/59/61 字节");

    /* ⑥ 参考解码器闭环：解码回 PCM 并做延迟搜索后的相关性校验 */
    {
        FILE *fa = fopen(cli_awb, "rb");
        static short decoded[NFRAMES * FRAME];
        int total = 0, bad = 0;
        if (fa) {
            char magic[9];
            if (fread(magic, 1, 9, fa) != 9) {
                bad = 1;
            } else {
                void *dec = D_IF_init();
                for (;;) {
                    int c = fgetc(fa);
                    if (c == EOF) {
                        break;
                    }
                    int ft = (c >> 3) & 0x0f;
                    if (ft > 8) {
                        ++bad;
                        break;
                    }
                    unsigned char buf[64];
                    buf[0] = (unsigned char)c;
                    if (fread(buf + 1, 1, MODE_BYTES[ft] - 1, fa) != (size_t)(MODE_BYTES[ft] - 1)) {
                        ++bad;
                        break;
                    }
                    short out[FRAME];
                    D_IF_decode(dec, buf, out, 0);
                    memcpy(decoded + total, out, sizeof(out));
                    total += FRAME;
                }
                D_IF_exit(dec);
            }
            fclose(fa);
        }
        double best = -2.0;
        int best_lag = 0;
        for (int lag = 0; lag <= 2000; lag += 4) {
            double c = corr_at(g_pcm, decoded, total < SAMPLES ? total : SAMPLES, lag);
            if (c > best) {
                best = c;
                best_lag = lag;
            }
        }
        double se = 0, soo = 0;
        for (int i = 0; i + best_lag < SAMPLES && i + best_lag < total; ++i) {
            double o = g_pcm[i], d = decoded[i + best_lag];
            se += (o - d) * (o - d);
            soo += o * o;
        }
        double snr = 10.0 * log10(soo / (se > 0 ? se : 1e-9));
        char detail[160];
        snprintf(detail, sizeof(detail), "解码 %d 样本 / 最佳延迟 %d 样本 / 相关系数 %.4f / SNR %.2f dB",
                 total, best_lag, best, snr);
        check(!bad && total == SAMPLES && best >= 0.97 && snr >= 10.0,
              "opencore-amr 参考解码器闭环（解码回 16000 样本，相关系数 ≥0.97）", detail);
    }

    printf("消费者用例完成：%d/%d 步通过\n", g_checks - g_failed, g_checks);
    if (g_failed) {
        printf("FAILED: %d\n", g_failed);
        return 1;
    }
    printf("Verdict: PASS\n");
    return 0;
}
