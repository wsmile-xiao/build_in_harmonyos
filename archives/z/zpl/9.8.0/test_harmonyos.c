/* test_harmonyos.c — HarmonyOS 专项测试（真实可执行，非空壳）。
 *
 * 验证 zpl 9.8.0 在 OHOS (aarch64) 上的平台适配结论：
 *   1. 平台宏：ZPL_SYSTEM_LINUX / ZPL_CPU_ARM / ZPL_ARCH_64_BIT 正确识别；
 *   2. 对齐分配器：zpl_alloc_align(align=4) 在 aarch64 上可用
 *      （回归验证归档补丁 0001 第 3 项：posix_memalign 对 align=4 返回
 *      EINVAL 的问题，x86 Linux 用 aligned_alloc 而 ARM 分支误用 posix_memalign）；
 *   3. 文件 API：zpl_file_open 写/读往返（TMPDIR 下可写路径，回归验证
 *      补丁第 2 项 stdio.h 缺失导致 FILE 未声明）；
 *   4. 运行时行为：base64 往返 + json5 解析（注意 zpl_json_parse 在
 *      handle_comments=true 时会原地改写源串，必须传可写缓冲区）真实
 *      运行并输出可观察结果。 */
#define ZPL_IMPLEMENTATION
#include <zpl.h>

int main(void)
{
    int failures = 0;

    /* 1. 平台宏识别（OHOS aarch64） */
#if defined(ZPL_SYSTEM_LINUX) && defined(ZPL_CPU_ARM) && defined(ZPL_ARCH_64_BIT)
    zpl_printf("[ohos] platform macros OK (LINUX+ARM+64BIT)\n");
#else
    zpl_printf("[ohos] FAIL: platform macros wrong (LINUX=%d ARM=%d 64BIT=%d)\n",
               (int)defined(ZPL_SYSTEM_LINUX), (int)defined(ZPL_CPU_ARM),
               (int)defined(ZPL_ARCH_64_BIT));
    failures++;
#endif

    /* 2. 对齐分配器：align=4（base64_decode 路径） */
    {
        void *p = zpl_alloc_align(zpl_heap(), 12, 4);
        if (!p) {
            zpl_printf("[ohos] FAIL: zpl_alloc_align(4) returned NULL\n");
            failures++;
        } else {
            zpl_printf("[ohos] aligned alloc align=4 OK\n");
            zpl_free(zpl_heap(), p);
        }
    }

    /* 3. 文件 API：TMPDIR 下写/读往返 */
    {
        char path[1024];
        char const *tmpdir = zpl_get_env("TMPDIR");
        if (!tmpdir || !*tmpdir) tmpdir = "/storage/Users/currentUser/tmp";
        zpl_snprintf(path, sizeof(path), "%s/zpl_ohos_test_%lld.txt", tmpdir,
                     (long long)zpl_time_now());
        char const *payload = "zpl OHOS file I/O round-trip";
        zpl_file f = {0};
        if (zpl_file_open_mode(&f, ZPL_FILE_MODE_WRITE, path) != ZPL_FILE_ERROR_NONE) {
            zpl_printf("[ohos] FAIL: file open (write) %s\n", path);
            failures++;
        } else {
            zpl_file_write(&f, payload, zpl_strlen(payload));
            zpl_file_close(&f);
            zpl_file r = {0};
            zpl_file_contents fc = {0};
            if (zpl_file_read_contents(zpl_heap(), true, path).data == NULL) {
                zpl_printf("[ohos] FAIL: file read-back %s\n", path);
                failures++;
            } else {
                fc = zpl_file_read_contents(zpl_heap(), true, path);
                if (zpl_strncmp(fc.data, payload, zpl_strlen(payload)) == 0) {
                    zpl_printf("[ohos] file write/read round-trip OK (%s)\n", path);
                } else {
                    zpl_printf("[ohos] FAIL: file content mismatch\n");
                    failures++;
                }
                zpl_file_free_contents(&fc);
            }
            zpl_file_close(&r);
        }
    }

    /* 4. base64 往返（可观察结果） */
    {
        char const *plain = "OHOS zpl round-trip 测试";
        zpl_u8 *enc = zpl_base64_encode(zpl_heap(), plain, zpl_strlen(plain));
        zpl_u8 *dec = enc ? zpl_base64_decode(zpl_heap(), enc, zpl_strlen(enc)) : NULL;
        if (!enc || !dec || zpl_strcmp(plain, dec) != 0) {
            zpl_printf("[ohos] FAIL: base64 round-trip\n");
            failures++;
        } else {
            zpl_printf("[ohos] base64 round-trip OK: %s\n", dec);
        }
    }

    /* 5. json5 解析（可观察结果；源串须为可写缓冲区） */
    {
        char doc[] = "{ \"name\": \"zpl\", \"version\": 9 }";
        zpl_json_object root = {0};
        u8 err = 0;
        zpl_json_parse(&root, zpl_strlen(doc), doc, zpl_heap_allocator(), true, &err);
        if (err != 0) {
            zpl_printf("[ohos] FAIL: json5 parse err=%d\n", (int)err);
            failures++;
        } else {
            zpl_json_object *name = zpl_json_find(&root, "name", false);
            zpl_json_object *ver = zpl_json_find(&root, "version", false);
            if (name && ver && name->string && ver->integer == 9) {
                zpl_printf("[ohos] json5 parse OK: name=%s version=%lld\n",
                           name->string, (long long)ver->integer);
            } else {
                zpl_printf("[ohos] FAIL: json5 field lookup\n");
                failures++;
            }
            zpl_json_free(&root);
        }
    }

    if (failures) {
        zpl_printf("[ohos] test_harmonyos: %d failure(s)\n", failures);
        return 1;
    }
    zpl_printf("[ohos] test_harmonyos: ALL OK\n");
    return 0;
}
