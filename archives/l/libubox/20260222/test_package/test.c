#include <stdio.h>
#include <string.h>
#include <libubox/blob.h>
#include <libubox/blobmsg.h>

int main(void)
{
    struct blob_buf buf = {0};
    struct blob_attr *attr;
    unsigned int rem;
    int ret = 0;
    int found_name = 0;
    int found_year = 0;

    /* blobmsg_buf_init 返回 int：0=成功（blob_buf_init 成功返回 0，失败 -ENOMEM） */
    if (blobmsg_buf_init(&buf) != 0)
        return 1;

    /* blobmsg_add_string/blobmsg_add_u32 return int (blobmsg_add_field):
     * 0 = success, non-zero = failure */
    if (blobmsg_add_string(&buf, "name", "libubox") != 0) {
        blob_buf_free(&buf);
        return 1;
    }
    if (blobmsg_add_u32(&buf, "year", 2026) != 0) {
        blob_buf_free(&buf);
        return 1;
    }

    /* 遍历 blobmsg 子属性应使用 blobmsg_for_each_attr（内部用 blobmsg_data
     * 跳过 blobmsg 头偏移），而非 blob_for_each_attr */
    blobmsg_for_each_attr(attr, buf.head, rem) {
        if (strcmp(blobmsg_name(attr), "name") == 0) {
            found_name = 1;
            if (strcmp(blobmsg_get_string(attr), "libubox") != 0)
                ret = 1;
        } else if (strcmp(blobmsg_name(attr), "year") == 0) {
            found_year = 1;
            if (blobmsg_get_u32(attr) != 2026)
                ret = 1;
        }
    }

    if (!found_name || !found_year)
        ret = 1;

    blob_buf_free(&buf);
    printf("test libubox blobmsg API: %s\n", ret ? "FAIL" : "OK");
    return ret;
}
