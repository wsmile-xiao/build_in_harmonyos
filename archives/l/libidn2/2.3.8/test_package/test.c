#include <stdint.h>
#include <stddef.h>
#include <idn2.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* 真实 API + 可手算断言（仓纪律 R34 反空壳）：
 *   ① idn2_check_version    —— 运行时版本可取且 >= 编译头版本
 *   ② idn2_to_ascii_8z      —— IDNA2008 编码："中国.example" → "xn--fiqs8s.example"
 *      （xn--fiqs8s 是 U+4E2D U+56FD 的 punycode，可用任何在线/离线 punycode 工具复算）
 *   ③ idn2_to_unicode_8z8z  —— 反向解码还原出原 UTF-8 域名
 *   ④ idn2_strerror         —— 错误码有可读文案
 * 头文件为 <idn2.h>（上游 tarball include/ 实名，非 <libidn2.h>）。
 * dlopen 探针保留（soname 完整性），但判绿依赖上面的功能断言。
 * 出错统一走 cleanup：ace/uni 未分配时为 NULL，idn2_free(NULL) 是空操作。 */

#ifndef TARGET_SO
#define TARGET_SO "libidn2.so"
#endif

int main(void) {
    int ret = 1;
    char *ace = NULL;
    char *uni = NULL;
    void *h = NULL;

    /* ① 版本 */
    const char *ver = idn2_check_version(NULL);
    if (!ver || !*ver) { fprintf(stderr, "idn2_check_version 返回空\n"); goto cleanup; }
    if (!idn2_check_version(IDN2_VERSION)) {
        fprintf(stderr, "运行库版本 %s 低于编译头版本 %s\n", ver, IDN2_VERSION);
        goto cleanup;
    }
    printf("libidn2 version: %s\n", ver);

    /* ② UTF-8 → ASCII (punycode)，非过渡模式 */
    int rc = idn2_to_ascii_8z("\xe4\xb8\xad\xe5\x9b\xbd.example", &ace,
                              IDN2_NONTRANSITIONAL);
    if (rc != IDN2_OK) {
        fprintf(stderr, "idn2_to_ascii_8z rc=%d (%s)\n", rc, idn2_strerror(rc));
        goto cleanup;
    }
    if (strcmp(ace, "xn--fiqs8s.example") != 0) {
        fprintf(stderr, "punycode 结果不符: got %s want xn--fiqs8s.example\n", ace);
        goto cleanup;
    }
    printf("to_ascii: %s\n", ace);

    /* ③ ASCII → UTF-8 还原 */
    rc = idn2_to_unicode_8z8z(ace, &uni, 0);
    if (rc != IDN2_OK) {
        fprintf(stderr, "idn2_to_unicode_8z8z rc=%d (%s)\n", rc, idn2_strerror(rc));
        goto cleanup;
    }
    if (strcmp(uni, "\xe4\xb8\xad\xe5\x9b\xbd.example") != 0) {
        fprintf(stderr, "解码还原不符\n");
        goto cleanup;
    }
    printf("to_unicode roundtrip ok\n");

    /* ④ 错误路径有可读文案 */
    const char *msg = idn2_strerror(IDN2_PUNYCODE_BAD_INPUT);
    if (!msg || !*msg) { fprintf(stderr, "idn2_strerror 返回空\n"); goto cleanup; }

    /* soname 完整性探针（不判绿，只验加载面） */
    h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); goto cleanup; }
    if (!dlsym(h, "idn2_to_ascii_8z")) {
        fprintf(stderr, "dlsym idn2_to_ascii_8z 缺失（疑签名/导出问题）\n");
        goto cleanup;
    }

    printf("libidn2 test_package: ALL PASS\n");
    ret = 0;

cleanup:
    idn2_free(ace);
    idn2_free(uni);
    if (h) dlclose(h);
    return ret;
}
