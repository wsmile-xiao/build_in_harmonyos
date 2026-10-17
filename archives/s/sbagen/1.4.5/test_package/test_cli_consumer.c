/* test_cli_consumer.c — sbagen 1.4.5 消费者测试（C 侧）
 *
 * 以一个真实的 C 程序消费打包产物 bin/sbagen：
 *   1) fork+execv 直接调用二进制（OHOS 无 /bin/sh，故不用 system()/popen()），
 *      合成 2 秒立体声 WAV（-Q -W -i -o <out> -L 00:00:02 "200+10/20"）；
 *   2) 解析 RIFF/WAVE 头：2ch / 44100Hz / 16bit / data 长度 = 44100*2*2*2；
 *   3) 逐帧检查左右声道非静音且互不相同（双耳拍频左右载波不同：200Hz/210Hz）；
 *   4) 调用 -h 检查帮助文本含 SBaGen 与版本号 1.4.5。
 *
 * 用法: ./test_cli_consumer <sbagen-binary> <workdir>
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define WAV_FRAMES 88200                       /* 2s @ 44100Hz */
#define WAV_DATA (WAV_FRAMES * 4)              /* stereo 16-bit    */
#define WAV_TOTAL (WAV_DATA + 44)              /* + canonical header */

static int g_checks = 0;
static int g_failed = 0;

static void ck(int cond, const char *what) {
    g_checks++;
    if (cond) {
        printf("  [ok]   %s\n", what);
    } else {
        g_failed++;
        printf("  [FAIL] %s\n", what);
    }
}

static uint16_t le16(const unsigned char *p) {
    return (uint16_t)(p[0] | (p[1] << 8));
}

static uint32_t le32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* 直接在子进程里 execv 目标程序，stdout+stderr 重定向到 console_path
 * （为 NULL 时退回 out_path）。console 与 -o/-W 产物路径分离，避免被测
 * 程序的诊断输出与产物写进同一 inode。返回退出码（异常结束返回 128）。*/
static int run_capture(const char *bin, char *const argv[],
                       const char *out_path, const char *tmpdir,
                       const char *console_path) {
    pid_t pid = fork();
    if (pid < 0) {
        return 127;
    }
    if (pid == 0) {
        const char *redir = console_path ? console_path : out_path;
        int fd = open(redir, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) {
            _exit(127);
        }
        if (dup2(fd, STDOUT_FILENO) < 0 || dup2(fd, STDERR_FILENO) < 0) {
            _exit(127);
        }
        close(fd);
        /* E002：OHOS /tmp 只读，把可写临时目录传给被测程序 */
        if (tmpdir && tmpdir[0]) {
            setenv("TMPDIR", tmpdir, 1);
        }
        execv(bin, argv);
        _exit(127);                            /* execv 失败 */
    }
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        return 128;
    }
    if (!WIFEXITED(status)) {
        return 128;
    }
    return WEXITSTATUS(status);
}

static long read_file(const char *path, unsigned char *buf, size_t cap) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return -1;
    }
    size_t n = fread(buf, 1, cap, f);
    fclose(f);
    return (long)n;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <sbagen-binary> <workdir>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    const char *work = argv[2];
    const char *tmpdir = getenv("TMPDIR");

    char wav[1024], help[1024], console[1024];
    snprintf(wav, sizeof wav, "%s/c_consumer.wav", work);
    snprintf(help, sizeof help, "%s/c_consumer_help.txt", work);
    snprintf(console, sizeof console, "%s/c_consumer.log", work);

    /* ---- [1] 合成 2 秒 WAV ---- */
    char *gen_argv[] = {(char *)bin, "-Q", "-W", "-i", "-o", wav,
                        "-L", "00:00:02", "200+10/20", NULL};
    int rc = run_capture(bin, gen_argv, wav, tmpdir, console);
    printf("[test_cli_consumer] WAV synthesis (rc=%d)\n", rc);
    ck(rc == 0, "exec bin/sbagen 合成 WAV 退出码为 0");

    static unsigned char buf[WAV_TOTAL + 4096];
    long n = read_file(wav, buf, sizeof buf);
    ck(n == WAV_TOTAL, "WAV 文件大小 = 352844（352800 样本 + 44 头）");
    if (n < 44) {
        printf("[test_cli_consumer] %d/%d checks passed\n", g_checks - g_failed, g_checks);
        return 1;
    }

    /* ---- [2] RIFF/WAVE 头解析 ---- */
    ck(memcmp(buf, "RIFF", 4) == 0 && memcmp(buf + 8, "WAVE", 4) == 0,
       "RIFF/WAVE 魔数正确");

    size_t off = 12;
    uint16_t ch = 0, bits = 0;
    uint32_t rate = 0, data_off = 0, data_len = 0;
    while (off + 8 <= (size_t)n) {
        uint32_t clen = le32(buf + off + 4);
        if (memcmp(buf + off, "fmt ", 4) == 0) {
            ch = le16(buf + off + 10);
            rate = le32(buf + off + 12);
            bits = le16(buf + off + 22);
        } else if (memcmp(buf + off, "data", 4) == 0) {
            data_off = (uint32_t)(off + 8);
            data_len = clen;
            break;
        }
        off += 8 + clen + (clen & 1);
    }
    ck(ch == 2, "fmt: 立体声 2 声道");
    ck(rate == 44100, "fmt: 采样率 44100 Hz");
    ck(bits == 16, "fmt: 16 bit 样本");
    ck(data_len == WAV_DATA, "data 块长度 = 352800（2s × 44100 × 2ch × 2B）");

    /* ---- [3] 声道内容校验（真实音频、双耳拍频左右不同） ---- */
    if (data_len == WAV_DATA && data_off + data_len <= (uint32_t)n) {
        const unsigned char *d = buf + data_off;
        long nonzero = 0, differ = 0;
        for (size_t i = 0; i < WAV_FRAMES; i++) {
            int16_t l = (int16_t)le16(d + 4 * i);
            int16_t r = (int16_t)le16(d + 4 * i + 2);
            if (l != 0 || r != 0) {
                nonzero++;
            }
            if (l != r) {
                differ++;
            }
        }
        ck(nonzero > (long)WAV_FRAMES / 2, "左右声道含真实音频数据（非静音）");
        ck(differ > (long)WAV_FRAMES / 2, "左右声道互不相同（双耳拍频 L/R 载波不同）");
    } else {
        ck(0, "左右声道含真实音频数据（非静音）");
        ck(0, "左右声道互不相同（双耳拍频 L/R 载波不同）");
    }

    /* ---- [4] 帮助与版本 ---- */
    char *help_argv[] = {(char *)bin, "-h", NULL};
    int hrc = run_capture(bin, help_argv, help, tmpdir, NULL);
    static unsigned char hbuf[65536];
    long hn = read_file(help, hbuf, sizeof hbuf - 1);
    if (hn < 0) {
        hn = 0;
    }
    hbuf[hn] = 0;
    ck(hrc == 0, "-h 退出码为 0");
    ck(strstr((char *)hbuf, "SBaGen") != NULL, "-h 输出含 SBaGen");
    ck(strstr((char *)hbuf, "1.4.5") != NULL, "-h 输出含版本号 1.4.5");

    printf("[test_cli_consumer] %d/%d checks passed\n", g_checks - g_failed, g_checks);
    return g_failed == 0 ? 0 : 1;
}
