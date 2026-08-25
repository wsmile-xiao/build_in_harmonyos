#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static void put_be16(unsigned char *data, size_t offset, unsigned int value)
{
    data[offset] = (unsigned char)(value >> 8);
    data[offset + 1] = (unsigned char)value;
}

/* A tiny valid AY file whose Z80 init routine enables one audible AY tone. */
static int write_fixture(const char *path)
{
    static const unsigned char init_code[] = {
        0x3e, 0x00, 0x01, 0xfd, 0xff, 0xed, 0x79,
        0x3e, 0x20, 0x01, 0xfd, 0xbf, 0xed, 0x79,
        0x3e, 0x07, 0x01, 0xfd, 0xff, 0xed, 0x79,
        0x3e, 0x38, 0x01, 0xfd, 0xbf, 0xed, 0x79,
        0x3e, 0x08, 0x01, 0xfd, 0xff, 0xed, 0x79,
        0x3e, 0x0f, 0x01, 0xfd, 0xbf, 0xed, 0x79,
        0xc9
    };
    unsigned char ay[160] = {0};
    FILE *file;

    memcpy(ay, "ZXAYEMUL", 8);
    ay[8] = 0;
    ay[9] = 0;
    put_be16(ay, 12, 18);  /* author at offset 30 */
    put_be16(ay, 14, 21);  /* misc at offset 35 */
    ay[16] = 0;             /* one track */
    ay[17] = 0;
    put_be16(ay, 18, 6);    /* track table at offset 24 */
    put_be16(ay, 24, 16);   /* track name at offset 40 */
    put_be16(ay, 26, 24);   /* track data at offset 50 */
    memcpy(ay + 30, "test\0", 5);
    memcpy(ay + 35, "test\0", 5);
    memcpy(ay + 40, "tone\0", 5);

    /* Track data: stack pointer is at 80, memory blocks at 90. */
    put_be16(ay, 60, 20);
    put_be16(ay, 62, 28);
    ay[80] = 0xff;
    ay[81] = 0xfe;
    put_be16(ay, 90, 0x8000);
    put_be16(ay, 92, sizeof(init_code));
    put_be16(ay, 94, 12);
    memcpy(ay + 106, init_code, sizeof(init_code));

    file = fopen(path, "wb");
    if (file == NULL)
        return 0;
    if (fwrite(ay, 1, 106 + sizeof(init_code), file) != 106 + sizeof(init_code))
    {
        fclose(file);
        return 0;
    }
    return fclose(file) == 0;
}

static int produces_pcm(void)
{
    const char *ay_path = "aylet-test.ay";
    const char *pcm_path = "aylet-test.pcm";
    struct stat pcm_stat;
    pid_t child;
    int status;
    int output;

    if (!write_fixture(ay_path))
        return 0;

    child = fork();
    if (child < 0)
        return 0;
    if (child == 0)
    {
        int fd = open(pcm_path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (fd < 0)
            _exit(127);
        if (dup2(fd, STDOUT_FILENO) < 0)
            _exit(127);
        close(fd);
        execlp("aylet", "aylet", "-s", "-t", "1", ay_path, (char *)NULL);
        _exit(127);
    }

    sleep(1);
    kill(child, SIGTERM);
    waitpid(child, &status, 0);
    output = stat(pcm_path, &pcm_stat) == 0 && pcm_stat.st_size > 0;
    unlink(ay_path);
    unlink(pcm_path);
    return output;
}

int main(void)
{
    if (system("aylet -h >/dev/null 2>&1") != 0)
        return 1;
    return produces_pcm() ? 0 : 1;
}
