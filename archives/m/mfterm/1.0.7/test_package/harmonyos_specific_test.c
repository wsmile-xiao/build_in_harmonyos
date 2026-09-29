/*
 * harmonyos_specific_test.c — mfterm 1.0.7 鸿蒙平台特有测试
 *
 * 编译期：__OHOS__ / __aarch64__ 硬绑定（非鸿蒙 AArch64 工具链直接 #error）
 * 运行期：对安装产物 bin/mfterm 校验平台属性（argv[1] 传入路径）：
 *   1. ELF64 / AArch64 机器类型
 *   2. musl 动态链接器 /lib/ld-musl-aarch64.so.1（OHOS 无 glibc ld.so）
 *   3. NEEDED 运行库含 libusb-1.0.so.0（libnfc 传递依赖，链接完整性）
 *   4. .note.ohos.ident 段存在（OHOS 签名/标识产物，OHOS clang 特有）
 *   5. libnfc ABI 在鸿蒙 musl 上可用（nfc_version() 返回非 NULL）
 *
 * 用法: harmonyos_specific_test <mfterm-binary>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <nfc/nfc.h>

#if !defined(__OHOS__)
#error "This test must be compiled with the HarmonyOS (OHOS) toolchain (__OHOS__ undefined)"
#endif

#if !defined(__aarch64__)
#error "This test must be compiled for AArch64 (__aarch64__ undefined)"
#endif

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg) do {                                   \
    checks++;                                                   \
    if (cond) {                                                 \
        printf("  ok: %s\n", msg);                              \
    } else {                                                    \
        printf("  FAIL: %s\n", msg);                            \
        failures++;                                             \
    }                                                           \
} while (0)

/* 将路径转义为单引号包裹的 shell 单词（' → '\''），杜绝 argv 路径注入 popen 命令 */
static void shell_quote(const char *in, char *out, size_t outsz)
{
    size_t o = 0;
    if (outsz < 3) { out[0] = '\0'; return; }
    out[o++] = '\'';
    for (size_t i = 0; in[i] != '\0'; i++) {
        if (in[i] == '\'') {
            if (o + 6 > outsz) break;
            out[o++] = '\''; out[o++] = '\\';
            out[o++] = '\''; out[o++] = '\'';
        } else {
            if (o + 3 > outsz) break;
            out[o++] = in[i];
        }
    }
    out[o++] = '\'';
    out[o] = '\0';
}

/* 最小 ELF64 解析：读 EI_CLASS 与 e_machine 足够 */
static int check_elf_header(const char *path)
{
    unsigned char e_ident[16];
    unsigned char hdr[64];
    FILE *f = fopen(path, "rb");
    if (!f) {
        printf("  FAIL: cannot open %s\n", path);
        failures++;
        return -1;
    }
    if (fread(hdr, 1, sizeof(hdr), f) != sizeof(hdr)) {
        printf("  FAIL: cannot read ELF header of %s\n", path);
        failures++;
        fclose(f);
        return -1;
    }
    fclose(f);
    memcpy(e_ident, hdr, 16);

    checks++;
    if (e_ident[0] == 0x7f && e_ident[1] == 'E' && e_ident[2] == 'L' && e_ident[3] == 'F') {
        printf("  ok: ELF magic\n");
    } else {
        printf("  FAIL: ELF magic\n");
        failures++;
    }
    checks++;
    if (e_ident[4] == 2 /* ELFCLASS64 */) {
        printf("  ok: ELF64 (EI_CLASS=ELFCLASS64)\n");
    } else {
        printf("  FAIL: expected ELF64, EI_CLASS=%d\n", e_ident[4]);
        failures++;
    }
    /* e_machine at offset 18 (little-endian): 0xB7 = 183 = EM_AARCH64 */
    unsigned machine = hdr[18] | (hdr[19] << 8);
    checks++;
    if (machine == 0xB7) {
        printf("  ok: AArch64 (e_machine=EM_AARCH64)\n");
    } else {
        printf("  FAIL: expected EM_AARCH64(183), e_machine=%u\n", machine);
        failures++;
    }
    return 0;
}

static void check_needed(const char *path)
{
    char cmd[4096];
    char quoted[4096];
    FILE *p;
    char line[512];
    int found_usb = 0, found_musl = 0;
    int n;

    /* readelf 由 OHOS sysroot 提供；输出行: " (NEEDED)  Shared library: [libusb-1.0.so.0]" */
    shell_quote(path, quoted, sizeof(quoted));
    n = snprintf(cmd, sizeof(cmd), "readelf -d %s 2>/dev/null", quoted);
    if (n < 0 || (size_t)n >= sizeof(cmd)) {
        printf("  FAIL: readelf -d command truncated (path too long)\n");
        failures++;
        return;
    }
    p = popen(cmd, "r");
    if (!p) {
        printf("  FAIL: popen readelf\n");
        failures++;
        return;
    }
    while (fgets(line, sizeof(line), p)) {
        if (strstr(line, "(NEEDED)") && strstr(line, "libusb-1.0.so.0"))
            found_usb = 1;
        if (strstr(line, "(NEEDED)") && strstr(line, "libc.so"))
            found_musl = 1;
    }
    pclose(p);

    CHECK(found_usb, "NEEDED contains libusb-1.0.so.0 (libnfc transitive dep)");
    CHECK(found_musl, "NEEDED contains libc.so (musl libc)");
}

static void check_interp_and_ohos_ident(const char *path)
{
    char cmd[8192];
    char quoted[4096];
    FILE *p;
    char buf[4096];
    size_t n;
    int len;

    /* 一次性读 program headers + section headers，找 musl 解释器与
     * .note.ohos.ident 段（OHOS clang 产物特有） */
    shell_quote(path, quoted, sizeof(quoted));
    len = snprintf(cmd, sizeof(cmd),
                   "{ readelf -l %s 2>/dev/null; readelf -S %s 2>/dev/null; }",
                   quoted, quoted);
    if (len < 0 || (size_t)len >= sizeof(cmd)) {
        printf("  FAIL: readelf -l/-S command truncated (path too long)\n");
        failures++;
        return;
    }
    p = popen(cmd, "r");
    if (!p) {
        printf("  FAIL: popen readelf -l/-S\n");
        failures++;
        return;
    }
    n = fread(buf, 1, sizeof(buf) - 1, p);
    pclose(p);
    buf[n] = 0;

    CHECK(strstr(buf, "Requesting program interpreter: /lib/ld-musl-aarch64.so.1") != NULL,
          "PT_INTERP is /lib/ld-musl-aarch64.so.1 (OHOS musl)");
    CHECK(strstr(buf, ".note.ohos.ident") != NULL,
          ".note.ohos.ident section present (OHOS toolchain signature)");
}

int main(int argc, char **argv)
{
    const char *mfterm;
    const char *nfc_ver;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <mfterm-binary>\n", argv[0]);
        return 2;
    }
    mfterm = argv[1];

    printf("[1/4] ELF64 / AArch64 header of installed mfterm\n");
    check_elf_header(mfterm);

    printf("[2/4] musl dynamic linker (PT_INTERP)\n");
    check_interp_and_ohos_ident(mfterm);

    printf("[3/4] NEEDED runtime libraries\n");
    check_needed(mfterm);

    printf("[4/4] libnfc ABI usable on HarmonyOS musl (nfc_version)\n");
    nfc_ver = nfc_version();
    CHECK(nfc_ver != NULL, "nfc_version() returned non-NULL");
    if (nfc_ver) {
        /* 依赖锁定 libnfc/1.8.0：版本串必须报 1.8.x
         *（原 `|| strlen(nfc_ver) > 0` 会短路，使 1.8 判断恒真） */
        CHECK(strstr(nfc_ver, "1.8") != NULL,
              "nfc_version() reports libnfc 1.8.x");
        printf("  info: libnfc version: %s\n", nfc_ver);
    }

    printf("\nHarmonyOS-specific test: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
