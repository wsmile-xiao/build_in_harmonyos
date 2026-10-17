/* libiptcdata 1.0.5 真实功能断言（test_package 消费者测试）.
 *
 * 链接的是打包后的 libiptcdata.so / libiptcdata.a（不包含源码目录），
 * 通过 iptc_data_new / iptc_dataset_new 构造真实 IPTC dataset，写入
 * 字符串值后序列化为字节流（iptc_data_save），再从字节流反序列化
 * （iptc_data_new_from_data）并校验读回的值与写入一致。
 *
 * 覆盖：
 *   1. 对象生命周期：iptc_data_new / iptc_data_free / iptc_dataset_new
 *   2. 写入：iptc_dataset_set_tag + iptc_dataset_set_data（带 IPTC_VALIDATE）
 *   3. 集合：iptc_data_add_dataset
 *   4. 按记录+标签取回：iptc_data_get_dataset
 *   5. 序列化/反序列化往返：iptc_data_save -> iptc_data_new_from_data
 *   6. 读回值校验：iptc_dataset_get_data + iptc_dataset_get_as_str
 *
 * 失败后立即 return 1，绝不继续用无效数据。
 */
#include <libiptcdata/iptc-data.h>
#include <libiptcdata/iptc-dataset.h>

#include <stdio.h>
#include <string.h>

#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("FAIL " __VA_ARGS__); printf("\n"); return 1; } } while (0)

int main(void)
{
    /* ── ① 构造一个空的 IPTC 数据集合并加一个 dataset ── */
    IptcData *data = iptc_data_new();
    CHECK(data != NULL, "iptc_data_new 返回 NULL");
    CHECK(data->count == 0, "新 data count=%u（期望 0）", data->count);
    printf("① iptc_data_new OK: count=%u\n", data->count);

    IptcDataSet *ds = iptc_dataset_new();
    CHECK(ds != NULL, "iptc_dataset_new 返回 NULL");

    /* Object Name (标签标题) — IPTC_RECORD_APP_2 / IPTC_TAG_OBJECT_NAME */
    iptc_dataset_set_tag(ds, IPTC_RECORD_APP_2, IPTC_TAG_OBJECT_NAME);

    static const char caption[] = "OpenHarmony IPTC round-trip";
    int rc = iptc_dataset_set_data(ds, (const unsigned char *)caption,
                                   (unsigned int)strlen(caption), IPTC_VALIDATE);
    /* set_data 返回 -1=错误 / 0=校验失败 / N=已拷贝字节数（成功） */
    CHECK(rc > 0, "iptc_dataset_set_data 返回 %d（期望 >0）", rc);
    CHECK((unsigned int)rc == (unsigned int)strlen(caption),
          "set_data 拷贝 %d 字节（期望 %zu）", rc, strlen(caption));
    printf("② 写入 OK: record=%d tag=%d 拷贝 %d 字节 value=\"%s\"\n",
           IPTC_RECORD_APP_2, IPTC_TAG_OBJECT_NAME, rc, caption);

    rc = iptc_data_add_dataset(data, ds);
    CHECK(rc == 0, "iptc_data_add_dataset 返回 %d（期望 0）", rc);
    CHECK(data->count == 1, "add 后 count=%u（期望 1）", data->count);
    printf("③ iptc_data_add_dataset OK: count=%u\n", data->count);

    /* ── ④ 按记录+标签取回刚写入的 dataset ── */
    IptcDataSet *got = iptc_data_get_dataset(data, IPTC_RECORD_APP_2,
                                             IPTC_TAG_OBJECT_NAME);
    CHECK(got != NULL, "iptc_data_get_dataset 返回 NULL");
    char strbuf[128];
    const char *s = iptc_dataset_get_as_str(got, strbuf, sizeof strbuf);
    CHECK(s != NULL, "iptc_dataset_get_as_str 返回 NULL");
    CHECK(strcmp(s, caption) == 0,
          "get_as_str=\"%s\"（期望 \"%s\"）", s, caption);
    printf("④ iptc_data_get_dataset + get_as_str OK: \"%s\"\n", s);

    /* ── ⑤ 序列化为字节流（iptc_data_save）── */
    unsigned char *buf = NULL;
    unsigned int size = 0;
    rc = iptc_data_save(data, &buf, &size);
    CHECK(rc == 0, "iptc_data_save 返回 %d（期望 0）", rc);
    CHECK(buf != NULL && size > 0, "save 产出空缓冲 size=%u", size);
    printf("⑤ iptc_data_save OK: size=%u 字节\n", size);

    /* ── ⑥ 从字节流反序列化并校验往返值一致 ── */
    IptcData *data2 = iptc_data_new_from_data(buf, size);
    CHECK(data2 != NULL, "iptc_data_new_from_data 返回 NULL");
    CHECK(data2->count == 1, "反序列化 count=%u（期望 1）", data2->count);

    IptcDataSet *got2 = iptc_data_get_dataset(data2, IPTC_RECORD_APP_2,
                                              IPTC_TAG_OBJECT_NAME);
    CHECK(got2 != NULL, "反序列化后 get_dataset 返回 NULL");
    char strbuf2[128];
    const char *s2 = iptc_dataset_get_as_str(got2, strbuf2, sizeof strbuf2);
    CHECK(s2 != NULL, "反序列化 get_as_str 返回 NULL");
    CHECK(strcmp(s2, caption) == 0,
          "往返值=\"%s\"（期望 \"%s\"）", s2, caption);
    printf("⑥ 往返校验 OK: 反序列化值=\"%s\"\n", s2);

    /* ── ⑦ 直接 get_data 取原始字节并校验长度/内容 ── */
    /* get_data 在缓冲有富余时附加 NUL 终止符，返回值 = 数据长度 + 1 */
    unsigned char rawbuf[128];
    int gotlen = iptc_dataset_get_data(got2, rawbuf, sizeof rawbuf);
    CHECK(gotlen >= 0, "get_data 返回 %d（期望 >=0）", gotlen);
    CHECK((unsigned int)gotlen == (unsigned int)strlen(caption) + 1,
          "get_data 长度=%d（期望 %zu，含 NUL）", gotlen, strlen(caption) + 1);
    /* 仅比较数据部分（不含 NUL） */
    CHECK(memcmp(rawbuf, caption, strlen(caption)) == 0,
          "get_data 内容不匹配");
    CHECK(rawbuf[strlen(caption)] == '\0', "get_data 未 NUL 终止");
    printf("⑦ iptc_dataset_get_data OK: len=%d（%d 数据 + NUL）内容一致\n",
           gotlen, gotlen - 1);

    iptc_data_free_buf(data, buf);
    iptc_data_free(data2);
    /* ds 已被 iptc_data_add_dataset 接管，不要重复释放；data 释放其 datasets */
    iptc_data_free(data);

    printf("libiptcdata 1.0.5: 全部断言通过\n");
    return 0;
}
