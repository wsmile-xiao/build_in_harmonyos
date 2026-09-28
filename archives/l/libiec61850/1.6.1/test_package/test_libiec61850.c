/*
 * test_libiec61850.c — libiec61850 1.6.1 消费者视角测试（鸿蒙平台特有测试）。
 *
 * 从已安装的包（include/libiec61850/ 头文件 + 静态库 libiec61850.a / libhal.a）
 * 编译链接，真实调用 IEC 61850 / MMS / HAL 公开 API 并逐条断言返回值。
 * 每个 CHECK 计 1 条断言，全部通过时程序返回 0。
 *
 * 与上游 examples 目录的区别：examples 是上游自带示例（上游用例），本文件是
 * 由本适配新增的、面向"库已被正确安装并可被第三方消费"的验证（鸿蒙特有测试）。
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <libiec61850/hal_time.h>
#include <libiec61850/iec61850_dynamic_model.h>
#include <libiec61850/linked_list.h>
#include <libiec61850/mms_value.h>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, name)                                        \
    do {                                                         \
        g_checks += 1;                                           \
        if (cond) {                                              \
            printf("[OK]   %s\n", (name));                       \
        } else {                                                 \
            g_failed += 1;                                       \
            fprintf(stderr, "[FAIL] %s\n", (name));              \
        }                                                        \
        fflush(stdout);                                          \
        fflush(stderr);                                          \
    } while (0)

int main(void)
{
    /* 1. MMS 整数：构造 + 取值回读 */
    MmsValue *iv = MmsValue_newIntegerFromInt32(42);
    CHECK(iv != NULL, "MmsValue_newIntegerFromInt32 返回非空");
    CHECK((iv != NULL) && (MmsValue_toInt32(iv) == 42), "MmsValue_toInt32 回读 == 42");

    /* 2. MMS 布尔 */
    MmsValue *bv = MmsValue_newBoolean(true);
    CHECK((bv != NULL) && (MmsValue_getBoolean(bv) == true), "MmsValue_newBoolean/getBoolean == true");

    /* 3. MMS 浮点 */
    MmsValue *fv = MmsValue_newFloat(3.14159f);
    CHECK((fv != NULL) && (fabsf(MmsValue_toFloat(fv) - 3.14159f) < 1e-5f),
          "MmsValue_newFloat/toFloat 往返误差 < 1e-5");

    /* 4. MMS 可见字符串 */
    MmsValue *sv = MmsValue_newVisibleString("IEC61850");
    CHECK((sv != NULL) && (MmsValue_toString(sv) != NULL) &&
              (strcmp(MmsValue_toString(sv), "IEC61850") == 0),
          "MmsValue_newVisibleString/toString 内容一致");

    /* 5. MMS 数组 */
    MmsValue *av = MmsValue_createEmptyArray(4);
    CHECK((av != NULL) && (MmsValue_getArraySize(av) == 4), "MmsValue_createEmptyArray(4) 长度 == 4");

    /* 6. 链表（iec61850 内部基础容器） */
    LinkedList list = LinkedList_create();
    CHECK(list != NULL, "LinkedList_create 返回非空");
    CHECK(list != NULL && LinkedList_size(list) == 0, "新建链表长度 == 0");
    if (list != NULL) {
        LinkedList_add(list, (void*)1);
        CHECK(LinkedList_size(list) == 1, "add 后链表长度 == 1");
        /* destroyStatic：本用例放入的是字面量指针而非堆内存，
         * LinkedList_destroy() 会对每个 data 调 free()。 */
        LinkedList_destroyStatic(list);
    } else {
        CHECK(0, "add 后链表长度 == 1（链表创建失败，跳过）");
    }

    /* 7. 动态 IED 模型 */
    IedModel *model = IedModel_create("libiec61850_test_ied");
    CHECK(model != NULL, "IedModel_create 返回非空");
    if (model != NULL) {
        IedModel_destroy(model);
    }

    /* 8. HAL 时间（系统调用面） */
    CHECK(Hal_getTimeInMs() > 0, "Hal_getTimeInMs 返回正的时间戳");

    printf("assertions=%d failed=%d\n", g_checks, g_failed);
    return (g_failed == 0) ? 0 : 1;
}
