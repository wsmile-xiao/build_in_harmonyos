/* test_package/test.c — mlddc 1.0-1 消费者测试 (HarmonyOS PC / aarch64-linux-ohos)
 *
 * mlddc 是 CLI 工具（非库），无可链接库目标；本测试直接消费包内产物：
 *   A1  bin/mlddc 存在
 *   A2  bin/mlddc 可执行 (access X_OK)
 *   A3  bin/mlddc 是 ELF64 LSB 文件 (魔数 + EI_CLASS + EI_DATA)
 *   A4  ELF e_machine == 0xB7 (AArch64) —— 目标架构正确
 *   A5  ELF e_type ∈ {ET_EXEC, ET_DYN} —— 合法可执行文件 (ET_DYN 即 PIE)
 *   A6  真实执行: mlddc < /dev/null 退出码 10 (Invalid user data 预期错误路径)
 *   A7  bin/mlupd 存在且可执行
 *   A8  bin/mlupd 以 "#!" 开头 (shell 脚本, OH 原生 sh 可解析)
 *   A9  bin/mymldata 存在且为 3 行数据模板
 *   A10 share/doc/mlddc/README 已安装
 *
 * 用法: test_mlddc <package_folder>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static int passed = 0;
static int failed = 0;

static void ok(const char *name) {
    printf("PASS %s\n", name);
    passed++;
}

static void fail(const char *name, const char *detail) {
    printf("FAIL %s %s\n", name, detail ? detail : "");
    failed++;
}

static void expect(int cond, const char *name, const char *detail) {
    if (cond) ok(name);
    else fail(name, detail);
}

static long file_size(const char *path) {
    struct stat st;
    if (stat(path, &st) != 0) return -1;
    return (long)st.st_size;
}

/* 读前 n 字节，返回实际读取长度 */
static size_t read_head(const char *path, unsigned char *buf, size_t n) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 0;
    size_t got = fread(buf, 1, n, fp);
    fclose(fp);
    return got;
}

static int count_lines(const char *path) {
    unsigned char buf[4096];
    size_t got = read_head(path, buf, sizeof(buf));
    if (got == 0) return 0;
    int lines = 0;
    for (size_t i = 0; i < got; i++)
        if (buf[i] == '\n') lines++;
    if (buf[got - 1] != '\n') lines++;   /* 末行无换行也算一行 */
    return lines;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL test_mlddc: missing package_folder argument\n");
        return 2;
    }
    const char *pkg = argv[1];

    char mlddc[1024], mlupd[1024], mymldata[1024], readme[1024], readme_md[1024];
    snprintf(mlddc, sizeof(mlddc), "%s/bin/mlddc", pkg);
    snprintf(mlupd, sizeof(mlupd), "%s/bin/mlupd", pkg);
    snprintf(mymldata, sizeof(mymldata), "%s/bin/mymldata", pkg);
    snprintf(readme, sizeof(readme), "%s/share/doc/mlddc/README", pkg);
    snprintf(readme_md, sizeof(readme_md), "%s/share/doc/mlddc/README.md", pkg);

    /* ── A1 / A2 ── */
    expect(file_size(mlddc) > 0, "A1 mlddc binary present", "(missing)");
    expect(access(mlddc, X_OK) == 0, "A2 mlddc executable", "(no +x)");

    /* ── A3 / A4 / A5: ELF 头 ── */
    unsigned char hdr[64];
    size_t got = read_head(mlddc, hdr, sizeof(hdr));
    int elf_magic = (got >= 20) && hdr[0] == 0x7f && hdr[1] == 'E' &&
                    hdr[2] == 'L' && hdr[3] == 'F';
    expect(elf_magic && hdr[4] == 2 && hdr[5] == 1,
           "A3 mlddc is ELF64 LSB", "(bad EI_CLASS/EI_DATA or magic)");

    if (elf_magic) {
        unsigned int e_machine = (unsigned int)hdr[18] | ((unsigned int)hdr[19] << 8);
        unsigned int e_type = (unsigned int)hdr[16] | ((unsigned int)hdr[17] << 8);
        expect(e_machine == 0xB7, "A4 e_machine == AArch64 (0xB7)", "(wrong arch)");
        expect(e_type == 2 || e_type == 3,
               "A5 ELF executable type (ET_EXEC/ET_DYN)", "(not an executable)");
        if (e_type == 3) printf("INFO A5 binary is PIE (ET_DYN)\n");
        else printf("INFO A5 binary is ET_EXEC (non-PIE)\n");
    } else {
        fail("A4 e_machine == AArch64 (0xB7)", "(no ELF header)");
        fail("A5 ELF executable type (ET_EXEC/ET_DYN)", "(no ELF header)");
    }

    /* ── A6: 真实执行（无输入 → 退出码 10，预期错误路径） ── */
    if (access(mlddc, X_OK) == 0) {
        char cmd[2048];
        snprintf(cmd, sizeof(cmd), "'%s' < /dev/null > /dev/null 2>&1", mlddc);
        int rc = system(cmd);
        int code = (rc == -1) ? -1 : WEXITSTATUS(rc);
        char detail[128];
        snprintf(detail, sizeof(detail), "(exit %d, expected 10)", code);
        expect(code == 10, "A6 mlddc runs and returns 10 on empty input", detail);
    } else {
        fail("A6 mlddc runs and returns 10 on empty input", "(not executable)");
    }

    /* ── A7 / A8: mlupd 包装脚本 ── */
    expect(access(mlupd, X_OK) == 0, "A7 mlupd wrapper present + executable", "(missing)");
    unsigned char shebang[2] = {0, 0};
    if (read_head(mlupd, shebang, 2) == 2)
        expect(shebang[0] == '#' && shebang[1] == '!',
               "A8 mlupd is a shell script (#!)", "(no shebang)");
    else
        fail("A8 mlupd is a shell script (#!)", "(unreadable)");

    /* ── A9: mymldata 数据模板 ── */
    int lines = count_lines(mymldata);
    char ldetail[64];
    snprintf(ldetail, sizeof(ldetail), "(lines=%d, expected 3)", lines);
    expect(file_size(mymldata) > 0 && lines == 3,
           "A9 mymldata template has 3 lines", ldetail);

    /* ── A10: 文档 ── */
    expect(file_size(readme) > 0 || file_size(readme_md) > 0,
           "A10 README doc installed", "(missing)");

    printf("mlddc 1.0-1 consumer tests: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
