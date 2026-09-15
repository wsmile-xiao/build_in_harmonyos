/*
 * test_netcdf_fortran_abi.c — netcdf-fortran 交付面契约测试（Conan test_package）
 *
 * 这是一个 C 侧消费者，验证的是**库产物对消费者可用的契约**，与同目录的 Fortran
 * 消费者（test_netcdf_fortran.f90，跑真实读写链路 27 项）互补：
 *
 *   1. 按 SONAME 以 RTLD_NOW 加载 libnetcdff.so —— 这会立即解析该库的全部
 *      重定位；只要库存在未解析符号就加载失败。这正是「用 C 编译器顶替 Fortran
 *      链接规则」时的实测症状（消费者报 _FortranATrim / _QMnetcdfPnf90_create
 *      等符号找不到，RC=127）。
 *   2. 逐个 dlsym 该库必须向消费者提供的 ABI 入口：Fortran 侧 F2003 模块过程
 *      （_QMnetcdfP<nf90_*>）与 Fortran 运行时（_FortranA*）。
 *      这些名字取自真实 Fortran 消费者链接后的未定义符号表，不是猜的。
 *
 * 任一断言失败即返回非 0，使 conan create 的 test_package 阶段真实失败。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 库的 SONAME：上游 CMakeLists 设 SOVERSION 7（NC4F_SO_VERSION），
 * 与 Fortran 消费者 DT_NEEDED 里记录的一致。 */
#define NETCDFF_SONAME "libnetcdff.so.7"

/* 该库必须导出的 ABI 入口。
 * 前 5 个是 F2003 模块过程（Fortran 消费者实际链接的名字），
 * 后 3 个是 Flang Fortran 运行时中字符/IO 相关例程。 */
static const char *const REQUIRED_SYMBOLS[] = {
    "_QMnetcdfPnf90_create",
    "_QMnetcdfPnf90_open",
    "_QMnetcdfPnf90_close",
    "_QMnetcdfPnf90_inquire",
    "_QMnetcdfPnf90_put_var_2d_eightbytereal",
    "_FortranATrim",
    "_FortranAioBeginExternalFormattedOutput",
    "_FortranAIndex1",
};
#define REQUIRED_SYMBOL_COUNT \
    (sizeof(REQUIRED_SYMBOLS) / sizeof(REQUIRED_SYMBOLS[0]))

int main(void)
{
    int checks = 0;
    int failures = 0;
    void *handle = NULL;
    size_t i;

    /* ① RTLD_NOW：加载期解析全部重定位，未解析符号即失败。 */
    handle = dlopen(NETCDFF_SONAME, RTLD_NOW | RTLD_LOCAL);
    checks++;
    if (handle == NULL) {
        failures++;
        printf("  [FAIL] dlopen(\"%s\", RTLD_NOW): %s\n", NETCDFF_SONAME,
               dlerror());
    } else {
        printf("  [ok]   dlopen(\"%s\", RTLD_NOW) 全部重定位可解析\n",
               NETCDFF_SONAME);
    }

    /* ② 逐个 ABI 入口必须可解析。 */
    if (handle != NULL) {
        for (i = 0; i < REQUIRED_SYMBOL_COUNT; i++) {
            void *sym = dlsym(handle, REQUIRED_SYMBOLS[i]);
            checks++;
            if (sym == NULL) {
                failures++;
                printf("  [FAIL] dlsym \"%s\" 未找到\n", REQUIRED_SYMBOLS[i]);
            } else {
                printf("  [ok]   dlsym \"%s\"\n", REQUIRED_SYMBOLS[i]);
            }
        }
    }

    /* ③ 加载到的那份库必须真的来自**被测包**：调用方（test_package/conanfile.py 的
     *    test()）通过环境变量 NETCDFF_PACKAGE_LIBDIR 传入被测包的 lib 目录绝对路径，
     *    这里断言 dladdr 给出的实际加载路径落在该目录下。
     *    只比 basename 不够——LD_LIBRARY_PATH 更靠前处若存在另一个同名副本，
     *    basename 相同而来源不同。该变量属交付面契约，未设置即判失败
     *    （不允许"跳过检查也算通过"）。 */
    if (handle != NULL) {
        void *sym = dlsym(handle, REQUIRED_SYMBOLS[0]);
        const char *expected = getenv("NETCDFF_PACKAGE_LIBDIR");
        const char *loaded = NULL;
        Dl_info info;
        memset(&info, 0, sizeof(info));
        checks++;
        if (sym != NULL && dladdr(sym, &info) != 0 && info.dli_fname != NULL) {
            loaded = info.dli_fname;
        }
        if (expected == NULL || expected[0] == '\0') {
            failures++;
            printf("  [FAIL] 未设置 NETCDFF_PACKAGE_LIBDIR，无法断言库来自被测包\n");
        } else if (loaded == NULL) {
            failures++;
            printf("  [FAIL] 无法确定实际加载路径\n");
        } else {
            size_t n = strlen(expected);
            while (n > 1 && expected[n - 1] == '/') {
                n--; /* 容忍尾部斜杠 */
            }
            if (loaded[0] == '/' && strncmp(loaded, expected, n) == 0
                && loaded[n] == '/') {
                printf("  [ok]   实际加载来自被测包: %s\n", loaded);
            } else {
                failures++;
                printf("  [FAIL] 实际加载的不是被测包: %s（期望前缀 %s/）\n",
                       loaded, expected);
            }
        }
        dlclose(handle);
    }

    printf("RESULT: netcdf-fortran ABI contract checks %d/%d passed\n",
           checks - failures, checks);
    if (failures != 0) {
        printf("FAILURES: %d\n", failures);
        return 1;
    }
    printf("PASS: netcdf-fortran 交付面契约全通过\n");
    return 0;
}
