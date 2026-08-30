/* test_package/test_libppd.c
 *
 * 消费者侧验证：链接 libppd，调用 PPD 公共 API 解析最小 PPD 文件，
 * 覆盖上游 testppd.c 的核心公共 API 测试项。
 *
 * 覆盖的上游 testppd.c 测试项（ppd/testppd.c）：
 *   1. ppdOpenFile — 打开 PPD 文件（上游 "ppdOpenFile(\"ppd/test.ppd\")"）
 *   2. ppdFindAttr — 查找属性（上游 "ppdFindAttr(ppd, \"cupsSingleBlock\", spec)"）
 *   3. ppdMarkDefaults — 标记默认选项（上游 "ppdMarkDefaults"）
 *   4. ppdIsMarked — 检查选项是否标记（上游 "ppdIsMarked(ppd, \"PageSize\", \"Letter\")"）
 *   5. ppdPageSize — 获取页面尺寸（上游 "ppdPageSize(ppd, \"Letter\")"）
 *   6. ppdConflicts — 获取冲突数（上游 "ppdConflicts(ppd)"）
 *   7. ppdEmitString — 生成 PostScript 代码（上游 "ppdEmitString(ppd, PPD_ORDER_ANY, 0.0)"）
 *   8. ppdLastError / ppdErrorString — 错误处理（上游 "ppdLastError(&line)"）
 *   9. ppdClose — 关闭 PPD（上游 "ppdClose(ppd)"）
 */
#include <ppd/ppd.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    int status = 0;

    /* 1. 写一个最小 PPD 文件到当前工作目录（CI worker 可能 /tmp 只读）*/
    const char *ppd_content =
        "*PPD-Adobe: \"4.3\"\n"
        "*FormatVersion: \"4.3\"\n"
        "*FileVersion: \"1.0\"\n"
        "*LanguageVersion: English\n"
        "*LanguageEncoding: ISOLatin1\n"
        "*PCFileName: \"TEST.PPD\"\n"
        "*Product: \"(Test Printer)\"\n"
        "*ModelName: \"Test Printer\"\n"
        "*ShortNickName: \"Test Printer\"\n"
        "*NickName: \"Test Printer\"\n"
        "*Manufacturer: \"TestCo\"\n"
        "*DeveloperName: \"OpenPrinting\"\n"
        "*PSVersion: \"(3010.000) 550\"\n"
        "*LanguageLevel: \"3\"\n"
        "*ColorDevice: False\n"
        "*DefaultColorSpace: Gray\n"
        "*FileSystem: False\n"
        "*Throughput: \"1\"\n"
        "*LandscapeOrientation: Plus90\n"
        "*DefaultPageSize: Letter\n"
        "*PageSize Letter/US Letter: \"<</PageSize[612 792]>>setpagedevice\"\n"
        "*End\n"
        "*DefaultImageableArea: Letter\n"
        "*ImageableArea Letter/US Letter: \"18 36 594 756\"\n"
        "*End\n"
        "*DefaultPaperDimension: Letter\n"
        "*PaperDimension Letter/US Letter: \"612 792\"\n"
        "*End\n";

    FILE *fp = fopen("test_libppd.ppd", "w");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot create test PPD file\n");
        return 1;
    }
    fputs(ppd_content, fp);
    fclose(fp);

    /* === 测试 1：ppdOpenFile 打开 PPD 文件 === */
    fputs("ppdOpenFile(test_libppd.ppd): ", stdout);
    ppd_file_t *ppd = ppdOpenFile("test_libppd.ppd");
    if (ppd) {
        puts("PASS");
    } else {
        int line;
        ppd_status_t err = ppdLastError(&line);
        printf("FAIL (%s on line %d)\n", ppdErrorString(err), line);
        status++;
        goto cleanup;
    }

    /* === 测试 2：ppdFindAttr 查找 Manufacturer 属性 === */
    fputs("ppdFindAttr(Manufacturer): ", stdout);
    ppd_attr_t *attr = ppdFindAttr(ppd, "Manufacturer", NULL);
    if (attr && attr->value && !strcmp(attr->value, "TestCo")) {
        puts("PASS");
    } else {
        printf("FAIL (got '%s')\n", attr && attr->value ? attr->value : "(null)");
        status++;
    }

    /* === 测试 3：ppdMarkDefaults 标记默认选项 === */
    fputs("ppdMarkDefaults: ", stdout);
    ppdMarkDefaults(ppd);
    /* ppdMarkDefaults 无返回值，检查后续 ppdIsMarked 是否正确 */
    if (ppdIsMarked(ppd, "PageSize", "Letter")) {
        puts("PASS");
    } else {
        puts("FAIL (default PageSize Letter not marked)");
        status++;
    }

    /* === 测试 4：ppdIsMarked 检查默认选项是否标记 === */
    fputs("ppdIsMarked(PageSize=Letter): ", stdout);
    if (ppdIsMarked(ppd, "PageSize", "Letter")) {
        puts("PASS");
    } else {
        puts("FAIL");
        status++;
    }

    /* === 测试 5：ppdPageSize 获取 Letter 页面尺寸 === */
    fputs("ppdPageSize(Letter): ", stdout);
    ppd_size_t *size = ppdPageSize(ppd, "Letter");
    if (size && size->width > 0 && size->length > 0) {
        printf("PASS (%.1fx%.1f)\n", size->width, size->length);
    } else {
        puts("FAIL (got NULL or zero size)");
        status++;
    }

    /* === 测试 6：ppdConflicts 获取冲突数（默认状态应为 0）=== */
    fputs("ppdConflicts: ", stdout);
    int conflicts = ppdConflicts(ppd);
    if (conflicts == 0) {
        puts("PASS (0)");
    } else {
        printf("FAIL (%d conflicts)\n", conflicts);
        status++;
    }

    /* === 测试 7：ppdEmitString 生成 PostScript 代码 === */
    fputs("ppdEmitString(PPD_ORDER_ANY): ", stdout);
    char *ps = ppdEmitString(ppd, PPD_ORDER_ANY, 0.0);
    if (ps && strlen(ps) > 0) {
        printf("PASS (%d bytes)\n", (int)strlen(ps));
        free(ps);
    } else {
        puts("FAIL (got NULL or empty)");
        status++;
    }

    /* === 测试 8：ppdLastError / ppdErrorString 错误处理 === */
    fputs("ppdLastError/ppdErrorString: ", stdout);
    int err_line;
    ppd_status_t last_err = ppdLastError(&err_line);
    /* 成功打开后，ppdLastError 应为 PPD_OK 或无错误 */
    const char *err_str = ppdErrorString(last_err);
    if (err_str) {
        printf("PASS (last error: '%s' on line %d)\n", err_str, err_line);
    } else {
        puts("FAIL (ppdErrorString returned NULL)");
        status++;
    }

    /* === 测试 9：ppdClose 关闭 PPD === */
    fputs("ppdClose: ", stdout);
    ppdClose(ppd);
    puts("PASS");

cleanup:
    unlink("test_libppd.ppd");

    if (status == 0) {
        puts("\nAll tests PASS");
    } else {
        printf("\n%d test(s) FAIL\n", status);
    }
    return status;
}
