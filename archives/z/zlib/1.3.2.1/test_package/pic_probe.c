/*
 * test_package/pic_probe.c — 鸿蒙特有验证（E539/E541）。
 *
 * 被测包是系统同名库（OHOS SDK sysroot 自带 libz.so），必须静态编译（R26）；
 * 但静态 libz.a 必须由 -fPIC 对象构成，否则下游把它链进共享库 / Python 扩展时，
 * aarch64 上会报 R_AARCH64_ADR_PREL_PG_HI21 relocation（非 PIC 实测失败见
 * logs/pic-probe-nopic-fail.log）。
 *
 * 本探针把被测包的 libz.a 用 `clang -shared -fPIC` 链成共享库：
 *   - 链接失败 → 静态库非 PIC（R_AARCH64 relocation）→ 测试失败；
 *   - 链接成功 → 再校验 .so 无 TEXTREL、且 NEEDED 仅 libc（不引入运行期 libz.so）。
 * 本文件被编译进共享库，函数由下游 DSO 消费者视角导出。
 */
#include <zlib.h>
#include <string.h>

/* compress(in) → uncompress 回 out（调用方提供缓冲）。 */
int zpic_probe_roundtrip(const unsigned char *in, unsigned long in_len,
                         unsigned char *out, unsigned long *out_len) {
    uLongf cap = compressBound(in_len);
    unsigned char tmp[1024];
    if (cap > sizeof(tmp)) return Z_BUF_ERROR;
    uLongf comp_len = cap;
    int rc = compress(tmp, &comp_len, in, in_len);
    if (rc != Z_OK) return rc;
    uLongf back = *out_len;
    rc = uncompress(out, &back, tmp, comp_len);
    *out_len = back;
    return rc;
}

const char *zpic_probe_version(void) { return zlibVersion(); }
