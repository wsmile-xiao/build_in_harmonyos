/* test.c — libsgutils (sg3_utils 1.46) 消费者用例（Conan test_package / L1）
 *
 * 仅通过库已安装/导出的公开头文件（include/sg_lib.h）与公开 API 使用该三方库，
 * 验证第三方使用者能否编译、链接、调用并正常运行：调用 sg_lib_version()
 * 获取版本串、sg_get_category_sense_str() 解析 SCSI 错误类别、hex2str()
 * 转换字节序列为十六进制串，并核对可观察结果。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <scsi/sg_lib.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS: %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void)
{
    const char * ver = sg_lib_version();
    char buf[64];
    const uint8_t bytes[4] = { 0x12, 0x34, 0xab, 0xcd };
    int n;

    printf("libsgutils (sg3_utils) consumer test\n");
    printf("  sg_lib_version() = '%s'\n", ver ? ver : "(null)");
    CHECK(ver != NULL && strlen(ver) > 0, "sg_lib_version() returns non-empty string");

    /* 类别字符串解析：SG_LIB_CAT_ILLEGAL_REQ (5) 须返回非空描述文本 */
    const char * cat = sg_get_category_sense_str(SG_LIB_CAT_ILLEGAL_REQ,
                                                 sizeof(buf), buf, 0);
    printf("  sg_get_category_sense_str(ILLEGAL_REQ) = '%s'\n", cat ? cat : "(null)");
    CHECK(cat != NULL && strlen(cat) > 0,
          "sg_get_category_sense_str() returns text for ILLEGAL_REQ");

    /* hex2str：0x12 0x34 0xab 0xcd → "12 34 ab cd" */
    n = hex2str(bytes, sizeof(bytes), "", 0, sizeof(buf), buf);
    printf("  hex2str({12 34 ab cd}) = '%s' (n=%d)\n", buf, n);
    CHECK(n > 0 && strstr(buf, "12") != NULL && strstr(buf, "34") != NULL &&
          strstr(buf, "ab") != NULL && strstr(buf, "cd") != NULL,
          "hex2str() renders all 4 bytes");

    printf(failures ? "CONSUMER TEST: %d FAILURE(S)\n" : "CONSUMER TEST: ALL PASS\n",
           failures);
    return failures ? 1 : 0;
}