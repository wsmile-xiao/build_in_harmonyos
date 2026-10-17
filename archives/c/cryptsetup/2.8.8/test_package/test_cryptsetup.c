/*
 * 消费者视角测试 — cryptsetup 2.8.8 / libcryptsetup
 *
 * 验证点（全部为真实 API 调用，非 stub）：
 *   1. 链接 libcryptsetup 并初始化上下文（crypt_init / crypt_free）
 *   2. crypt_get_dir() 返回非空（库内构建期常量，验证符号真被解析）
 *   3. 在普通文件上真实创建 LUKS2 头（crypt_format + 快速 PBKDF2）
 *      —— 该路径同时用到 libjson-c（LUKS2 元数据读写）与 openssl（crypto backend）
 *   4. 重新 crypt_load 校验头可解析：type/cipher/uuid/volume_key_size
 *
 * 不触达 device-mapper 激活路径（crypt_activate），故非 root 亦可运行；
 * dm 路径由 test_package/conanfile.py 的 CLI 用例覆盖（luksDump/luksHeaderBackup）。
 */
#include <libcryptsetup.h>

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define IMG_SIZE (40u * 1024u * 1024u)

static int checks = 0;
static int failures = 0;

static void check(int cond, const char *what) {
    checks++;
    if (cond) {
        printf("ok: %s\n", what);
    } else {
        failures++;
        printf("FAIL: %s\n", what);
    }
}

int main(int argc, char **argv) {
    const char *img = (argc > 1) ? argv[1] : "./consumer-luks2.img";
    struct crypt_device *cd = NULL;
    struct crypt_pbkdf_type pbkdf = {
        .type = "pbkdf2",
        .hash = "sha256",
        .iterations = 1000,
        .flags = CRYPT_PBKDF_NO_BENCHMARK,
    };
    struct crypt_params_luks2 params = {
        .pbkdf = &pbkdf,
        .label = "OHOS-CONSUMER-TEST",
    };
    int fd, r;

    /* 1. 初始化（无设备上下文亦合法） */
    r = crypt_init(&cd, NULL);
    check(r == 0, "crypt_init(NULL device) returns 0");
    check(cd != NULL, "crypt_device handle allocated");

    /* 2. 库内常量符号解析 */
    check(crypt_get_dir() != NULL, "crypt_get_dir() non-NULL");
    crypt_free(cd);
    cd = NULL;

    /* 3. 普通文件上真实写 LUKS2 头 */
    fd = open(img, O_RDWR | O_CREAT | O_TRUNC, 0600);
    check(fd >= 0, "open image file for writing");
    if (fd < 0)
        return 1;
    check(ftruncate(fd, (off_t)IMG_SIZE) == 0, "ftruncate image to 40MiB");
    close(fd);

    r = crypt_init(&cd, img);
    check(r == 0, "crypt_init(image) returns 0");
    r = crypt_format(cd, CRYPT_LUKS2, "aes", "xts-plain64", NULL, NULL, 32, &params);
    if (r != 0)
        fprintf(stderr, "  crypt_format errno=%d (%s)\n", r, strerror(-r));
    check(r == 0, "crypt_format(LUKS2, aes-xts-plain64) returns 0");
    /* 镜像 CLI 消费者流（luksFormat --key-file）：format 只写元数据，keyslot
     * 需显式挂载。不挂 keyslot 的头 segment→digest→keyslots 链为空，
     * crypt_get_volume_key_size() 按上游语义返回 0（首轮实测：0 ≠ 断言值）。
     * 用 format 时传入的卷密钥（cd->volume_key 在内存中）挂 keyslot 0，
     * pbkdf2 1000 次迭代（NO_BENCHMARK）避免 argon2 内存锁/耗时。 */
    r = crypt_set_pbkdf_type(cd, &pbkdf);
    check(r == 0, "crypt_set_pbkdf_type(pbkdf2/1000) returns 0");
    r = crypt_keyslot_add_by_volume_key(cd, CRYPT_ANY_SLOT, NULL, 0, "ohos", 4);
    if (r < 0)
        fprintf(stderr, "  keyslot_add errno=%d (%s)\n", r, strerror(-r));
    check(r >= 0, "crypt_keyslot_add_by_volume_key(slot0) >= 0");
    crypt_free(cd);
    cd = NULL;

    /* 4. 重新加载并核对元数据（JSON 元数据经 libjson-c 解析回读） */
    r = crypt_init(&cd, img);
    check(r == 0, "crypt_init(image) re-open");
    r = crypt_load(cd, CRYPT_LUKS2, NULL);
    if (r != 0)
        fprintf(stderr, "  crypt_load errno=%d (%s)\n", r, strerror(-r));
    check(r == 0, "crypt_load(LUKS2) returns 0");

    check(crypt_get_type(cd) && strcmp(crypt_get_type(cd), "LUKS2") == 0,
          "crypt_get_type() == LUKS2");
    check(crypt_get_cipher(cd) && strcmp(crypt_get_cipher(cd), "aes") == 0,
          "crypt_get_cipher() == aes");
    check(crypt_get_cipher_mode(cd) && strcmp(crypt_get_cipher_mode(cd), "xts-plain64") == 0,
          "crypt_get_cipher_mode() == xts-plain64");
    check(crypt_get_uuid(cd) != NULL && strlen(crypt_get_uuid(cd)) == 36,
          "crypt_get_uuid() returns 36-char UUID");
    /* 挂载 keyslot 后（segment→digest→keyslot 链完整），vk size =
     * format 时传入的 32 字节；该值经 JSON keyslot/digest/segment 三段
     * 关联回读，是元数据链真实解析的强断言。同时打印实际值供日志取证。 */
    fprintf(stderr, "  volume key size = %d bytes\n",
            crypt_get_volume_key_size(cd));
    check(crypt_get_volume_key_size(cd) == 32,
          "crypt_get_volume_key_size() == 32 (keyslot attached)");
    crypt_free(cd);

    printf("---\n%d check(s) run, %d FAILED\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
