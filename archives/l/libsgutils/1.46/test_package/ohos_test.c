/* ohos_test.c — libsgutils (sg3_utils 1.46) 鸿蒙专项测试
 *
 * 验证库在 HarmonyOS PC 平台的可用性要点：
 *   1. 公开头文件 <scsi/sg_lib.h> 在 OHOS 工具链下可编译；
 *   2. 公开 API sg_scsi_normalize_sense()/sg_get_sense_str() 解析手工构造的
 *      SCSI sense 数据并得到预期结果（验证 OHOS 下字节序/结构布局）；
 *   3. 链接动态库 libsgutils2 运行正常。
 * 本用例与上游 testing/ 用例、test_package 消费者用例分别计数。
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <scsi/sg_lib.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS: %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void)
{
    struct sg_scsi_sense_hdr ssh;
    /* 手工构造 sense：key=ILLEGAL_REQUEST(5), asc/ascq=0x24 0x00
     * (INVALID FIELD IN CDB)，SG_LIB_CAT_ILLEGAL_REQ */
    uint8_t sense[18];
    char out[128];
    const char * s;

    memset(sense, 0, sizeof(sense));
    sense[0] = 0x70;          /* current, fixed format */
    sense[2] = 0x05;          /* sense key: ILLEGAL_REQUEST */
    sense[7] = 0x0a;          /* additional sense length */
    sense[12] = 0x24;         /* asc: INVALID FIELD IN CDB */
    sense[13] = 0x00;         /* ascq */
    sense[14] = 0x03;         /* field pointer byte */
    sense[15] = 0x00;         /* field pointer bit 0-7 */

    printf("libsgutils (sg3_utils 1.46) OHOS-specific test\n");

    /* 1. sense 规范化：正确识别 fixed format + key=5 */
    CHECK(1 == sg_scsi_normalize_sense(sense, sizeof(sense), &ssh),
          "sg_scsi_normalize_sense() returns true for fixed format sense");
    CHECK(0x70 == ssh.response_code,
          "response code 0x70 (current, fixed) parsed");
    CHECK(5 == ssh.sense_key,
          "sense key 5 (ILLEGAL_REQUEST) parsed");

    /* 2. 类别归类：ASC/ASCQ 0x24/0x00 应为 SG_LIB_CAT_ILLEGAL_REQ */
    CHECK(SG_LIB_CAT_ILLEGAL_REQ ==
          sg_err_category_sense(sense, sizeof(sense)),
          "sg_err_category_sense() -> ILLEGAL_REQ");

    /* 3. 字符串描述非空 */
    s = NULL;
    if (sg_get_sense_str("", sense, sizeof(sense), false, sizeof(out), out) > 0)
        s = out;
    printf("  sense str = '%s'\n", s ? s : "(null)");
    CHECK(s != NULL && strlen(s) > 0,
          "sg_get_sense_str() returns description text");

    printf(failures ? "OHOS TEST: %d FAILURE(S)\n" : "OHOS TEST: ALL PASS\n",
           failures);
    return failures ? 1 : 0;
}