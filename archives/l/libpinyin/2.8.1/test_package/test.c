/* 消费者测试 — 以库使用者身份调用 libpinyin 公开 API（pinyin.h）
 * 断言失败即非 0 退出，由 conanfile.py 的 test() 判定。
 * 系统模型数据目录经 SYSTEM_DATADIR 编译定义传入（CMakeLists 用 CMakeDeps 的
 * PACKAGE_FOLDER 变量拼出包内 share/libpinyin/data），未定义时回退 NULL。 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pinyin.h>

#ifndef SYSTEM_DATADIR
#define SYSTEM_DATADIR NULL
#endif

static int failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (cond) {                                                            \
            printf("ok   - %s\n", msg);                                        \
        } else {                                                               \
            printf("FAIL - %s\n", msg);                                        \
            failures++;                                                        \
        }                                                                      \
    } while (0)

int main(void)
{
    /* 1) 上下文初始化：systemdir 指向包内模型数据目录，userdir 传 NULL */
    pinyin_context_t *context = pinyin_init(SYSTEM_DATADIR, NULL);
    CHECK(context != NULL, "pinyin_init(SYSTEM_DATADIR, NULL) 返回非空上下文");
    if (!context) {
        printf("\n%d failures\n", failures);
        return 1;
    }

    /* 2) 分配实例 */
    pinyin_instance_t *instance = pinyin_alloc_instance(context);
    CHECK(instance != NULL, "pinyin_alloc_instance() 返回非空实例");

    if (instance) {
        /* 3) 输入拼音串并解析：返回值为解析出的音节数（"ni hao" = 2） */
        size_t parsed = pinyin_parse_more_full_pinyins(instance, "ni hao");
        CHECK(parsed == 2, "pinyin_parse_more_full_pinyins(\"ni hao\") 解析出 2 个音节");

        /* 4) 从已解析的拼音猜句子（系统模型已随包安装），再取句子内容 */
        CHECK(pinyin_guess_sentence(instance) == TRUE, "pinyin_guess_sentence() 成功");
        char *sentence = NULL;
        pinyin_get_sentence(instance, 0, &sentence);
        CHECK(sentence != NULL, "pinyin_get_sentence() 返回非空指针");
        g_free(sentence);

        /* 5) 重置后重新解析同一输入（幂等） */
        CHECK(pinyin_reset(instance) == TRUE, "pinyin_reset() 成功");
        parsed = pinyin_parse_more_full_pinyins(instance, "ni hao");
        CHECK(parsed == 2, "pinyin_reset() 后重新解析出 2 个音节");

        pinyin_free_instance(instance);
        printf("ok   - pinyin_free_instance() 无崩溃\n");
    }

    /* 6) 上下文释放（上游 API 名为 pinyin_fini） */
    pinyin_fini(context);
    printf("ok   - pinyin_fini() 无崩溃\n");

    printf("\n%d failures\n", failures);
    return failures == 0 ? 0 : 1;
}
