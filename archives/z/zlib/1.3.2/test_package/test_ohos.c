/*
 * test_ohos.c — zlib 鸿蒙特有测试（OpenHarmony / HarmonyOS PC 消费链路）
 *
 * 本配方对 zlib 的 OHOS 适配核心结论：
 *   `./configure --static` + `CFLAGS="-fPIC -O2"`
 *   —— 产出的是 PIC 静态库 libz.a：既能被下游共享库（cairo/libpng/qpdf 等）
 *   静态吸收，又不会引入运行期 libz.so（不污染系统 /lib/libz.so*）。
 * 本测试在真实鸿蒙运行时上逐条验证该结论成立。
 *
 * 检查项：
 *   D1 编译期：断言 __OHOS__（目标三元组 aarch64-linux-ohos）
 *   D2 运行期：uname() 报告 HarmonyOS —— 证明测试确实跑在鸿蒙 PC 上
 *   D3 运行期：zlibVersion() 与配方版本一致
 *   D4 运行期：deflate/inflate 往返（真实调用被测包 API，R34）
 *   D5 运行期：compress2/uncompress 往返 + crc32/adler32 已知向量
 *   D6 运行期：dlopen 由静态 libz.a 编成的共享库探针（PIC 可吸收性）
 *
 * 用法：./test_ohos [PIC探针.so路径]，默认 ./libz_ohos_probe.so
 */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

#include "zlib.h"

#define OHOS_TEST_EXPECTED_VERSION "1.3.2"
#define PAYLOAD \
    "OpenHarmony zlib consumer path: deflate/inflate round trip on HarmonyOS PC."

static int failures;

static void check(int condition, const char *name, const char *detail) {
    if (condition) {
        printf("PASS: %s\n", name);
    } else {
        printf("FAIL: %s%s%s\n", name, detail ? " -- " : "", detail ? detail : "");
        failures++;
    }
}

/* D4: 原始 deflate/inflate 往返 */
static void check_deflate_inflate(void) {
    static const char *payload = PAYLOAD;
    unsigned char packed[512];
    unsigned char unpacked[512];
    z_stream zs;
    uLong bound = (uLong)sizeof(packed);
    uLong out_len = (uLong)sizeof(unpacked);
    int rc;

    memset(&zs, 0, sizeof(zs));
    rc = deflateInit(&zs, Z_BEST_COMPRESSION);
    check(rc == Z_OK, "D4.1 deflateInit(Z_BEST_COMPRESSION) on HarmonyOS", NULL);
    if (rc != Z_OK) {
        return;
    }
    zs.next_in = (Bytef *)payload;
    zs.avail_in = (uInt)strlen(payload);
    zs.next_out = packed;
    zs.avail_out = (uInt)bound;
    rc = deflate(&zs, Z_FINISH);
    bound = zs.total_out;
    deflateEnd(&zs);
    check(rc == Z_STREAM_END && bound > 0, "D4.2 deflate(Z_FINISH) produced a stream", NULL);
    if (rc != Z_STREAM_END) {
        return;
    }

    memset(&zs, 0, sizeof(zs));
    rc = inflateInit(&zs);
    check(rc == Z_OK, "D4.3 inflateInit on HarmonyOS", NULL);
    if (rc != Z_OK) {
        return;
    }
    zs.next_in = packed;
    zs.avail_in = (uInt)bound;
    zs.next_out = unpacked;
    zs.avail_out = (uInt)out_len;
    rc = inflate(&zs, Z_FINISH);
    out_len = zs.total_out;
    inflateEnd(&zs);
    check(rc == Z_STREAM_END && out_len == strlen(payload) &&
              memcmp(unpacked, payload, out_len) == 0,
          "D4.4 inflate round trip restores the original payload", NULL);
}

/* D5: compress2/uncompress + 校验和已知向量 */
static void check_checksums(void) {
    static const char *payload = PAYLOAD;
    static const char *rfc_vector = "123456789";
    unsigned char packed[512];
    unsigned char unpacked[512];
    uLong packed_len = (uLong)sizeof(packed);
    uLong unpacked_len = (uLong)sizeof(unpacked);
    int rc;

    rc = compress2(packed, &packed_len, (const Bytef *)payload, (uLong)strlen(payload),
                   Z_BEST_SPEED);
    check(rc == Z_OK && packed_len > 0, "D5.1 compress2() on HarmonyOS", NULL);
    rc = uncompress(unpacked, &unpacked_len, packed, packed_len);
    check(rc == Z_OK && unpacked_len == strlen(payload) &&
              memcmp(unpacked, payload, unpacked_len) == 0,
          "D5.2 uncompress() round trip restores the original payload", NULL);

    /* RFC 1950 adler32 / RFC 1952 crc32 标准测试向量 */
    check(crc32(0L, Z_NULL, 0) == 0L && crc32(0L, (const Bytef *)rfc_vector, 9) == 0xCBF43926UL,
          "D5.3 crc32() matches RFC 1952 test vector", NULL);
    check(adler32(1L, (const Bytef *)rfc_vector, 9) == 0x091E01DEUL,
          "D5.4 adler32() matches RFC 1950 test vector", NULL);
}

/* D6: 静态 libz.a 是 PIC —— 能被共享库吸收并在鸿蒙运行期加载 */
static void check_pic_probe(const char *so_path) {
    char buf[64];
    void *handle;
    int (*probe)(char *, unsigned int);
    const char *err;

    handle = dlopen(so_path, RTLD_NOW);
    err = dlerror();
    check(handle != NULL, "D6.1 dlopen() of the libz.a-backed shared object",
          handle ? NULL : (err ? err : "unknown dlerror"));
    if (handle == NULL) {
        return;
    }
    probe = (int (*)(char *, unsigned int))dlsym(handle, "ohos_pic_probe");
    err = dlerror();
    check(probe != NULL, "D6.2 dlsym(ohos_pic_probe) resolves in the shared object",
          probe ? NULL : (err ? err : "unknown dlerror"));
    if (probe == NULL) {
        dlclose(handle);
        return;
    }
    memset(buf, 0, sizeof(buf));
    probe(buf, (unsigned int)sizeof(buf));
    check(strcmp(buf, OHOS_TEST_EXPECTED_VERSION) == 0,
          "D6.3 zlib version reported from inside the shared object", buf);
    dlclose(handle);
}

int main(int argc, char **argv) {
    const char *so_path = (argc > 1) ? argv[1] : "./libz_ohos_probe.so";
    struct utsname sys_info;

#if !defined(__OHOS__)
    fprintf(stderr, "FAIL: D1 test_ohos must be compiled for OpenHarmony (__OHOS__)\n");
    return 1;
#endif
    check(1, "D1 compiled for OpenHarmony (__OHOS__ target aarch64-linux-ohos)", NULL);

    memset(&sys_info, 0, sizeof(sys_info));
    if (uname(&sys_info) != 0) {
        check(0, "D2 uname() identifies the HarmonyOS runtime", "uname() failed");
    } else {
        check(strcmp(sys_info.sysname, "HarmonyOS") == 0,
              "D2 uname() identifies the HarmonyOS runtime", sys_info.sysname);
    }

    check(strcmp(zlibVersion(), OHOS_TEST_EXPECTED_VERSION) == 0,
          "D3 zlibVersion() matches the packaged version", zlibVersion());

    check_deflate_inflate();
    check_checksums();
    check_pic_probe(so_path);

    if (failures != 0) {
        printf("HarmonyOS-specific zlib test FAILED: %d check(s) failed\n", failures);
        return 1;
    }
    printf("HarmonyOS-specific zlib test: all checks passed\n");
    return 0;
}
