/* test.c — pakchois 0.4 test_package（行为测试，无需 PKCS#11 token）
 *
 * 第 1 层（R34 反空壳）：dlopen 被测包 lib/libpakchois.so 并 dlsym 真实导出符号
 *   pakchois_module_load / pakchois_error / pakchois_module_destroy，
 *   证明包内 .so 是真实实现而非空壳。
 * 第 2 层（行为）：经 dlsym 函数指针真实调用库 API（不直接链接、无需 rpath，
 *   运行期只依赖包的绝对路径）：
 *   - pakchois_module_load：MODPATH 编译期烘焙为 "//lib://lib/pkcs11"（OHOS
 *     系统只读分区，测试环境无 provider）→ 加载不存在的 provider 必须返回
 *     CKR_GENERAL_ERROR（pakchois.c: find_pkcs11_module 全路径 dlopen 失败 →
 *     NULL → rv=CKR_GENERAL_ERROR），且 *module 保持原值（不泄漏悬空句柄）。
 *     该负路径完整走通 provider_mutex 加锁、MODPATH 遍历、dlopen 失败与
 *     错误码传播。
 *   - pakchois_error：错误表返回正确非 NULL 字符串（OK / General error /
 *     Vendor 分支；--disable-nls 下 _(x)=x）。
 * 限制（如实记录，不伪造）：成功路径（槽位/会话/对象转发）需运行期真实
 * PKCS#11 token，仓库内无 token provider 配方且 /lib 为只读系统分区无法
 * 注入 → 见 MANIFEST.yml，上游 test 程序因此不可离线运行。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

/* 头文件安装于 include/pakchois/（pkg-config Cflags: -I${includedir}/pakchois） */
#include <pakchois/pakchois.h>

#ifndef TARGET_SO
#define TARGET_SO "libpakchois.so"
#endif

typedef ck_rv_t (*load_fn)(pakchois_module_t **, const char *);
typedef const char *(*error_fn)(ck_rv_t);
typedef void (*destroy_fn)(pakchois_module_t *);

static int fails = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", (msg)); } \
    else { printf("FAIL: %s\n", (msg)); fails++; } \
} while (0)

int main(void)
{
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }
    printf("dlopen %s ok\n", TARGET_SO);

    load_fn p_load = (load_fn) dlsym(h, "pakchois_module_load");
    error_fn p_error = (error_fn) dlsym(h, "pakchois_error");
    destroy_fn p_destroy = (destroy_fn) dlsym(h, "pakchois_module_destroy");

    /* 层 1：R34 反空壳（真实导出符号存在） */
    CHECK(p_load != NULL, "symbol pakchois_module_load present (R34)");
    CHECK(p_error != NULL, "symbol pakchois_error present (R34)");
    CHECK(p_destroy != NULL, "symbol pakchois_module_destroy present (R34)");
    if (!p_load || !p_error) {
        dlclose(h);
        return 1;
    }

    /* 层 2a：负路径行为 —— 测试环境无 provider（MODPATH //lib://lib/pkcs11
     * 为只读系统分区），加载失败必须返回 CKR_GENERAL_ERROR 且不发布句柄 */
    pakchois_module_t *ctx = NULL;
    ck_rv_t rv = p_load(&ctx, "ohos_pakchois_test_missing_provider");
    CHECK(rv == CKR_GENERAL_ERROR,
          "pakchois_module_load(missing provider) == CKR_GENERAL_ERROR "
          "(mutex -> MODPATH scan -> dlopen fail -> error propagation)");
    CHECK(ctx == NULL,
          "*module unchanged on load failure (no dangling handle published)");

    /* 层 2b：错误表（errors.c）—— 非 NULL 且内容正确 */
    const char *s_ok = p_error(CKR_OK);
    CHECK(s_ok != NULL && strcmp(s_ok, "OK") == 0,
          "pakchois_error(CKR_OK) == \"OK\"");
    const char *s_ge = p_error(CKR_GENERAL_ERROR);
    CHECK(s_ge != NULL && strcmp(s_ge, "General error") == 0,
          "pakchois_error(CKR_GENERAL_ERROR) == \"General error\"");
    const char *s_vd = p_error(CKR_VENDOR_DEFINED);
    CHECK(s_vd != NULL && strcmp(s_vd, "Vendor defined error") == 0,
          "pakchois_error(CKR_VENDOR_DEFINED) == \"Vendor defined error\" "
          "(vendor-defined branch)");

    dlclose(h);
    printf("pakchois: %s (%d failure(s))\n",
           fails ? "FAILED" : "ok (symbols + behavior verified)", fails);
    return fails ? 1 : 0;
}
