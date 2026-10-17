#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <afflib/afflib.h>

/* 消费者冒烟测试：实际调用 libafflib 的公开 C API。
 * 1. af_version() 获取库版本号（验证链接与符号解析）
 * 2. af_open()/af_close() 创建并关闭一个临时 AFF 文件（验证核心 I/O 路径）
 * 临时目录优先取 $TMPDIR，回退 /tmp，并确保目录存在。
 */
int main(void) {
    const char *version = af_version();
    if (version == NULL || version[0] == '\0') {
        fprintf(stderr, "FAIL: af_version() 返回空\n");
        return 1;
    }
    printf("af_version() = %s\n", version);

    const char *tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        tmpdir = "/tmp";
    }
    char tmpfile[1024];
    snprintf(tmpfile, sizeof(tmpfile), "%s/test_afflib_smoke.aff", tmpdir);

    /* 确保临时目录存在（$TMPDIR 可能指向未创建的目录） */
    struct stat st;
    if (stat(tmpdir, &st) != 0 || !S_ISDIR(st.st_mode)) {
        if (mkdir(tmpdir, 0755) != 0) {
            fprintf(stderr, "FAIL: 无法创建临时目录 %s\n", tmpdir);
            return 1;
        }
    }
    remove(tmpfile);

    AFFILE *af = af_open(tmpfile, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (af == NULL) {
        fprintf(stderr, "FAIL: af_open(%s) 返回 NULL\n", tmpfile);
        return 1;
    }
    if (af_close(af) != 0) {
        fprintf(stderr, "FAIL: af_close() 失败\n");
        return 1;
    }
    remove(tmpfile);

    printf("PASS: afflib 3.7.22 API 冒烟测试通过 (af_version/af_open/af_close)\n");
    return 0;
}
