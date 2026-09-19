/* 鸿蒙特有测试（消费者视角）：只用 libmongocrypt 的公开 C API，在 OHOS 上真跑一次
 * FLE1 local datakey 封装。该路径会走 OpenSSL 后端的 AES-256-CBC + HMAC-SHA-512，
 * 因此同时验证了包本身、制品仓 openssl/3.5.6 的链接、以及 OHOS 上的运行时。
 */
#include <mongocrypt.h>

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static int checks;
static int failures;

#define CHECK(cond, what)                     \
    do {                                      \
        checks++;                             \
        if (cond) {                           \
            printf("ok %d - %s\n", checks, what); \
        } else {                              \
            failures++;                       \
            printf("not ok %d - %s\n", checks, what); \
        }                                     \
    } while (0)

static void dump_status(mongocrypt_t *crypt, mongocrypt_ctx_t *ctx) {
    mongocrypt_status_t *st = mongocrypt_status_new();
    uint32_t len = 0;
    const char *msg;

    if (ctx != NULL) {
        mongocrypt_ctx_status(ctx, st);
    } else {
        mongocrypt_status(crypt, st);
    }
    msg = mongocrypt_status_message(st, &len);
    printf("# status: %.*s\n", (int) len, msg ? msg : "(none)");
    mongocrypt_status_destroy(st);
}

static void test_version(void) {
    uint32_t len = 0;
    const char *v = mongocrypt_version(&len);

    CHECK(v != NULL && v[0] != '\0', "mongocrypt_version 返回非空");
    CHECK(len == (uint32_t) strlen(v), "版本长度与 strlen 一致");
    CHECK(strncmp(v, "1.20.1", 6) == 0, "版本号是 1.20.1");
}

static void test_native_crypto_backend(void) {
    CHECK(mongocrypt_is_crypto_available(), "原生 OpenSSL 后端已编入（非 crypto hooks 模式）");
}

static void test_status_on_fresh_instance(void) {
    mongocrypt_t *crypt = mongocrypt_new();
    mongocrypt_status_t *st = mongocrypt_status_new();
    const char *msg;
    uint32_t len = 0;

    CHECK(crypt != NULL, "mongocrypt_new 成功");
    CHECK(mongocrypt_status(crypt, st), "mongocrypt_status 写入调用方结构");
    CHECK(mongocrypt_status_type(st) == MONGOCRYPT_STATUS_OK, "新建实例状态为 OK");
    /* OK 状态下消息本就是空串，只要求可安全读取（指针有效、长度自洽）。 */
    msg = mongocrypt_status_message(st, &len);
    printf("# status message ptr=%p len=%u\n", (void *) msg, len);
    CHECK(msg == NULL || len == (uint32_t) strlen(msg), "状态消息指针与长度自洽");
    mongocrypt_status_destroy(st);
    mongocrypt_destroy(crypt);
}

static void test_binary_view(void) {
    uint8_t raw[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    mongocrypt_binary_t *view = mongocrypt_binary_new_from_data(raw, sizeof(raw));
    mongocrypt_binary_t *empty = mongocrypt_binary_new();

    CHECK(mongocrypt_binary_len(view) == 8, "binary 视图长度保持");
    CHECK(memcmp(mongocrypt_binary_data(view), raw, sizeof(raw)) == 0, "binary 视图内容保持");
    CHECK(mongocrypt_binary_len(empty) == 0 && mongocrypt_binary_data(empty) == NULL, "空 binary 长度 0");
    mongocrypt_binary_destroy(view);
    mongocrypt_binary_destroy(empty);
}

static void test_local_datakey_encrypt(void) {
    uint8_t key[96];
    int i;
    mongocrypt_t *crypt = mongocrypt_new();
    mongocrypt_binary_t *keybin;
    mongocrypt_ctx_t *ctx;
    mongocrypt_ctx_state_t state;
    mongocrypt_binary_t *out = mongocrypt_binary_new();
    bool inited;
    uint32_t out_len;
    const uint8_t *doc;

    for (i = 0; i < 96; i++) {
        key[i] = (uint8_t) i;
    }
    keybin = mongocrypt_binary_new_from_data(key, sizeof(key));
    CHECK(mongocrypt_setopt_kms_provider_local(crypt, keybin), "接受 96 字节 local KMS master key");
    mongocrypt_binary_destroy(keybin);
    inited = mongocrypt_init(crypt);
    if (!inited) {
        dump_status(crypt, NULL);
    }
    CHECK(inited, "mongocrypt_init 成功");
    if (!inited) {
        mongocrypt_binary_destroy(out);
        mongocrypt_destroy(crypt);
        return;
    }

    ctx = mongocrypt_ctx_new(crypt);
    CHECK(ctx != NULL, "mongocrypt_ctx_new 成功");
    CHECK(mongocrypt_ctx_setopt_masterkey_local(ctx), "ctx 选 local master key");
    CHECK(mongocrypt_ctx_datakey_init(ctx), "datakey_init 启动");

    state = mongocrypt_ctx_state(ctx);
    CHECK(state == MONGOCRYPT_CTX_READY, "local KMS 建密钥不依赖网络，直接进 READY");
    if (state != MONGOCRYPT_CTX_READY) {
        dump_status(crypt, ctx);
    }

    if (state == MONGOCRYPT_CTX_READY) {
        CHECK(mongocrypt_ctx_finalize(ctx, out), "ctx_finalize 产出加密后的 datakey 文档");
        out_len = mongocrypt_binary_len(out);
        doc = mongocrypt_binary_data(out);
        CHECK(out_len > 100, "产出的文档含密文而非空壳");
        if (out_len >= 4) {
            uint32_t declared = (uint32_t) doc[0] | ((uint32_t) doc[1] << 8) | ((uint32_t) doc[2] << 16) |
                                ((uint32_t) doc[3] << 24);
            CHECK(declared == out_len, "产物首 4 字节小端长度 == 文档长度（合法 BSON）");
        } else {
            CHECK(0, "产物太短，无法按 BSON 校验");
        }
    }

    mongocrypt_binary_destroy(out);
    mongocrypt_ctx_destroy(ctx);
    mongocrypt_destroy(crypt);
}

static void test_rejects_bad_master_key(void) {
    uint8_t short_key[8] = {0};
    mongocrypt_t *crypt = mongocrypt_new();
    mongocrypt_binary_t *keybin = mongocrypt_binary_new_from_data(short_key, sizeof(short_key));

    CHECK(!mongocrypt_setopt_kms_provider_local(crypt, keybin), "拒绝非 96 字节的 local key");
    mongocrypt_binary_destroy(keybin);
    dump_status(crypt, NULL);
    mongocrypt_destroy(crypt);
}

static void test_datakey_without_masterkey(void) {
    uint8_t key[96];
    int i;
    mongocrypt_t *crypt = mongocrypt_new();
    mongocrypt_binary_t *keybin;
    mongocrypt_ctx_t *ctx;
    bool started;

    for (i = 0; i < 96; i++) {
        key[i] = (uint8_t) (200 - i);
    }
    keybin = mongocrypt_binary_new_from_data(key, sizeof(key));
    (void) mongocrypt_setopt_kms_provider_local(crypt, keybin);
    mongocrypt_binary_destroy(keybin);
    CHECK(mongocrypt_init(crypt), "init 成功（用于负向用例）");
    ctx = mongocrypt_ctx_new(crypt);
    started = mongocrypt_ctx_datakey_init(ctx);
    CHECK(!started || mongocrypt_ctx_state(ctx) == MONGOCRYPT_CTX_ERROR, "未设 master key 时不会进就绪态");
    mongocrypt_ctx_destroy(ctx);
    mongocrypt_destroy(crypt);
}

int main(void) {
    printf("# libmongocrypt OHOS consumer tests\n");
    test_version();
    test_native_crypto_backend();
    test_status_on_fresh_instance();
    test_binary_view();
    test_local_datakey_encrypt();
    test_rejects_bad_master_key();
    test_datakey_without_masterkey();
    printf("# %d checks, %d failures\n", checks, failures);
    printf("%s\n", failures == 0 ? "PASS" : "FAIL");
    return failures == 0 ? 0 : 1;
}
