#include <stdio.h>
#include <string.h>
#include "cmor.h"

int main(void) {
    /* cmor_setup 第 2 参数 netcdf 是 netCDF 文件模式，合法值仅
     * CMOR_PRESERVE_4/CMOR_APPEND_4/CMOR_REPLACE_4/CMOR_PRESERVE_3/...；
     * 传 1 会被 cmor 判为非法并记录内部错误（cmor_nerrors+1）。这里用
     * 合法常量 CMOR_REPLACE，并在 setup/close 后断言内部错误计数为 0，
     * 确保「全绿」口径与运行日志一致。 */
    int netcdf = CMOR_REPLACE;
    int verbosity = CMOR_QUIET;
    int mode = CMOR_NORMAL;
    int create_subdirs = 0;
    int err;

    /* 1. 头文件版本宏断言 */
    if (CMOR_VERSION_MAJOR != 3 || CMOR_VERSION_MINOR != 15 || CMOR_VERSION_PATCH != 2) {
        printf("FAIL: version macro mismatch (%d.%d.%d)\n",
               CMOR_VERSION_MAJOR, CMOR_VERSION_MINOR, CMOR_VERSION_PATCH);
        return 1;
    }

    /* 2. 公共 C API：cmor_setup + cmor_close */
    err = cmor_setup(NULL, &netcdf, &verbosity, &mode, NULL, &create_subdirs);
    if (err != 0) {
        printf("FAIL: cmor_setup returned %d\n", err);
        return 1;
    }
    if (cmor_nerrors != 0) {
        printf("FAIL: cmor_setup recorded %d internal error(s)\n", cmor_nerrors);
        return 1;
    }
    err = cmor_close();
    if (err != 0) {
        printf("FAIL: cmor_close returned %d\n", err);
        return 1;
    }
    if (cmor_nerrors != 0) {
        printf("FAIL: cmor_close recorded %d internal error(s)\n", cmor_nerrors);
        return 1;
    }

    printf("cmor 3.15.2 basic C API: OK\n");
    return 0;
}
