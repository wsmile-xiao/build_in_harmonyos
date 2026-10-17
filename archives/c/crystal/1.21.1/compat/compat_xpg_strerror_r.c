/*
 * OHOS/musl 兼容垫片（供 crystal 1.21.1 编译器自举链接使用）。
 *
 * 背景：官方 linux-aarch64 bootstrap 是 **gnu 目标**构建的，其 stdlib 绑定
 * （src/lib_c/aarch64-linux-gnu 下的声明）会引用若干 glibc 专属符号；而 OHOS 的
 * sysroot/musl 只提供 POSIX 版实现或干脆不提供，导致链接失败。
 *
 * 本文件为等价补齐（不是绕过）：符号语义与 glibc 侧一致，仅为名称/存在性差异。
 */

/* ── 1) glibc 的 XSI 版 strerror_r 符号名 ────────────────────────────
 * crystal: src/lib_c/aarch64-linux-gnu/c/string.cr:8
 *     fun strerror_r = __xpg_strerror_r(Int, Char*, SizeT) : Int
 * musl 只提供 POSIX 版 strerror_r（签名同为 (int, char*, size_t) -> int）。
 *   ld.lld: error: undefined symbol: __xpg_strerror_r
 */
#include <string.h>
#include <stddef.h>

int __xpg_strerror_r(int errnum, char *buf, size_t buflen) {
    return strerror_r(errnum, buf, buflen);
}

/* ── 2) pthread_setcancelstate ───────────────────────────────────────
 * crystal: src/crystal/system/unix/process.cr:262,267
 *     LibC.pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, out cancel_state)
 * 实测 OHOS SDK 26 sysroot 的 pthread.h **不声明**该函数、libc 无该符号
 * （编译期 "call to undeclared function" + 链接期 undefined symbol）。
 * 仓内既有同族条目：DRAFT-aml-1.0.0-ohos-pthread-setcancelstate-meson-feature-detect
 *   → 结论：设备运行期 libc 以 **弱符号** 导出（nm 见 `W pthread_setcancelstate`），
 *     「编译期 sysroot 缺」≠「运行期不存在」。worker 线程禁用取消属防御性行为，
 *     缺失时可安全跳过。
 * 故此处提供返回 0（成功）的空实现：语义为「不支持线程取消」，
 * 与弱符号兜底行为一致，不影响正确性。
 *
 * ⚠️ 必须声明为 **weak**：本文件作为显式输入对象（compat.o）总是被链接，
 * 若用强符号，一旦运行期 libc 确实导出了真实实现（设备 libc 以弱符号导出，
 * 未来版本可能改为强符号），链接器会因重复定义报错，或由本空实现**遮蔽**
 * 掉真实实现 → 线程取消语义被静默破坏。weak 的定义让真实实现优先。
 */
#include <pthread.h>

__attribute__((weak))
int pthread_setcancelstate(int state, int *oldstate) {
    (void)state;
    if (oldstate != NULL) {
        *oldstate = PTHREAD_CANCEL_ENABLE;
    }
    return 0;
}

__attribute__((weak))
int pthread_setcanceltype(int type, int *oldtype) {
    (void)type;
    if (oldtype != NULL) {
        *oldtype = PTHREAD_CANCEL_DEFERRED;
    }
    return 0;
}

/* ── 关于 OpenSSL 的 sk_* 符号（重要，勿再加回）────────────────────────
 * 早期版本的本垫片曾为 sk_value / sk_num / sk_free / sk_pop_free 提供转发，
 * 那是在 **OpenSSL 版本探测失败**（PKG_CONFIG_PATH 未设 → 版本被判定为
 * "0.0.0" → crystal 走 lib_crypto.cr:336 的 1.1 裸名分支）时的权宜之计。
 *
 * 一旦在构建环境正确导出 PKG_CONFIG_PATH，crystal 会探测到真实版本
 * （实测 3.5.8）并改走 :331 的 `= OPENSSL_sk_*` 别名分支，**不再需要裸名**。
 * 此时若仍保留转发函数，反而有害：本文件作为显式输入对象（compat.o）总是被
 * 链接，其内部对 OPENSSL_sk_* 的未解析引用若排在 -lcrypto 之后处理，就会报
 *   ld.lld: error: undefined symbol: OPENSSL_sk_num / OPENSSL_sk_pop_free / ...
 *
 * 结论：**用 PKG_CONFIG_PATH 解决版本探测，不要用符号转发绕过**。
 */
