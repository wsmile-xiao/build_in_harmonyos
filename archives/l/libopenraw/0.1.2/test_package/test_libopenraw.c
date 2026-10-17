/*
 * libopenraw test_package — 验证库能正常链接并调用核心 API
 */
#include <stdio.h>
#include <string.h>
#include <libopenraw/libopenraw.h>

int main(void)
{
    /* 1. 获取库支持的文件扩展名列表 */
    const char **exts = or_get_file_extensions();
    if (exts == NULL) {
        fprintf(stderr, "FAIL: or_get_file_extensions() returned NULL\n");
        return 1;
    }
    printf("OK: or_get_file_extensions() returned non-NULL\n");

    /* 打印前几个扩展名 */
    int count = 0;
    for (int i = 0; exts[i] != NULL && i < 10; i++) {
        printf("  ext[%d] = %s\n", i, exts[i]);
        count++;
    }
    if (count == 0) {
        fprintf(stderr, "FAIL: no file extensions reported\n");
        return 1;
    }
    printf("OK: library reports %d+ file extensions\n", count);

    /* 2. 创建一个不存在文件的 rawfile 对象，验证生命周期 API 正常 */
    ORRawFileRef rf = or_rawfile_new("/nonexistent/file.cr2", OR_RAWFILE_TYPE_UNKNOWN);
    if (rf == NULL) {
        /* or_rawfile_new 对不存在文件返回 NULL 是合理行为 */
        printf("OK: or_rawfile_new() returned NULL for missing file\n");
    } else {
        /* 对象创建成功，验证 release 不崩溃 */
        or_error err = or_rawfile_release(rf);
        printf("OK: or_rawfile_release() returned error code %d\n", err);
    }

    printf("ALL TESTS PASSED\n");
    return 0;
}
