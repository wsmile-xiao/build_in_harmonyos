/*
 * test_ohos_config.c — HarmonyOS 平台特有测试
 *
 * 验证 gnustep-make 2.9.2.1 针对 HarmonyOS PC 的适配配置是否在安装产物中
 * 正确生效（这些配置是本次适配的核心，见 PR 补丁 0001/0003/0006）：
 *   1. config.make: OBJCFLAGS 含 -fconstant-string-class=NSConstantString
 *      （鸿蒙 ObjC 常量字符串类，否则 NSString 初始化失败）
 *   2. config.make: OPTFLAG 含 -fPIC -O0
 *      （规避 -O2 下 lld 不生成 __objc_constant_string 段的链接问题）
 *   3. config.make: DEFAULT_OBJC_RUNTIME_ABI = gnustep-2.0（libobjc2 modern ABI）
 *   4. config-noarch.make: default_library_combo = ng-gnu-gnu（modern runtime）
 *   5. target.make: IS_LINUX = yes（linux-ohos 识别为 GNU/Linux）
 *   6. target.make: HAVE_SHARED_LIBS = yes（.so 共享库构建）
 *   7. GNUstep.sh 存在（构建系统入口）
 *
 * 运行环境：conanrun（GNUSTEP_MAKEFILES 由被测包注入）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define BUF_SIZE 65536

static int failures = 0;

/* 读取文件并检查是否包含 needle */
static void check_file_contains(const char *path, const char *needle,
                                const char *desc)
{
    FILE *f;
    char *buf;
    size_t n = 0;
    f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", path);
        failures++;
        return;
    }
    buf = (char *)malloc(BUF_SIZE);
    if (!buf) {
        fprintf(stderr, "FAIL: out of memory reading %s\n", path);
        fclose(f);
        failures++;
        return;
    }
    n = fread(buf, 1, BUF_SIZE - 1, f);
    buf[n] = '\0';
    fclose(f);
    if (strstr(buf, needle) == NULL) {
        fprintf(stderr, "FAIL: %s — '%s' not found in %s\n", desc, needle, path);
        failures++;
    } else {
        printf("PASS: %s ('%s')\n", desc, needle);
    }
    free(buf);
}

int main(void)
{
    const char *mk = getenv("GNUSTEP_MAKEFILES");
    char path[1024];

    if (!mk || !*mk) {
        fprintf(stderr, "FAIL: GNUSTEP_MAKEFILES not set in run environment\n");
        return 1;
    }

    /* 1-3: config.make 的鸿蒙适配配置 */
    snprintf(path, sizeof(path), "%s/config.make", mk);
    check_file_contains(path, "-fconstant-string-class=NSConstantString",
                        "ObjC constant-string class (NSConstantString)");
    check_file_contains(path, "-fPIC -O0",
                        "-O0 (avoid __objc_constant_string link issue)");
    check_file_contains(path, "DEFAULT_OBJC_RUNTIME_ABI = gnustep-2.0",
                        "ObjC modern runtime ABI (gnustep-2.0)");

    /* 4: config-noarch.make 的 ng-gnu-gnu（libobjc2 modern runtime） */
    snprintf(path, sizeof(path), "%s/config-noarch.make", mk);
    check_file_contains(path, "default_library_combo = ng-gnu-gnu",
                        "libobjc2 modern runtime combo (ng-gnu-gnu)");

    /* 5-6: target.make 的 linux-ohos 识别与 .so 支持 */
    snprintf(path, sizeof(path), "%s/target.make", mk);
    check_file_contains(path, "IS_LINUX = yes",
                        "linux-ohos recognized as GNU/Linux");
    check_file_contains(path, "HAVE_SHARED_LIBS = yes",
                        ".so shared library build enabled");

    /* 7: GNUstep.sh 存在 */
    snprintf(path, sizeof(path), "%s/GNUstep.sh", mk);
    if (access(path, R_OK) != 0) {
        fprintf(stderr, "FAIL: missing GNUstep.sh\n");
        failures++;
    } else {
        printf("PASS: GNUstep.sh present\n");
    }

    if (failures > 0) {
        fprintf(stderr, "OHOS config test: %d failure(s)\n", failures);
        return 1;
    }
    printf("OHOS config test: OK (7 assertions)\n");
    return 0;
}
