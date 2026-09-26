/*
 * ohos_pic_probe.c — 鸿蒙适配验证探针（被编成共享库）
 *
 * 本配方用 `./configure --static` + `CFLAGS=-fPIC` 产出 PIC 静态库 libz.a。
 * 该探针把 libz.a 的吸收结果编成 .so，由 test_ohos.c 在鸿蒙运行期 dlopen：
 * 若 libz.a 不是 PIC，`clang -shared` 会在链接期报重定位错误（R_AARCH64），
 * 这正是本适配要解决的鸿蒙问题；链接 + 加载成功即证明适配结论成立。
 */
#include <stdio.h>

#include "zlib.h"

int ohos_pic_probe(char *out, unsigned int len) {
    return snprintf(out, (size_t)len, "%s", zlibVersion());
}
