/* 兜底 stub：官方 CI 部分 worker 的 make 对 .os/.oS 大小写处理异常，可能让
 * libc.a 里的 .os（静态 PIC 对象）误带 -DSHARED、走 SHARED 分支，静态链接时引用
 * 这些 ld.so/libgcc 符号。这里提供弱定义兜底；正常构建（.os 无 SHARED）时这些
 * 符号不会被引用，弱定义不参与链接、不影响正常产物。
 *
 * 注意：这些符号是 ld.so（_dl_secure/_dl_error_catch_tsd/__libc_dl_error_tsd）与
 * libgcc（_Unwind_*）在动态链接运行时提供的；静态 uClibc 程序本不该引用它们。
 */
__attribute__((weak)) int _dl_secure = 0;
__attribute__((weak)) void *__libc_stack_end = 0;

static void **__stub_dl_error_catch_tsd(void) { return 0; }
__attribute__((weak)) void **(*_dl_error_catch_tsd)(void) = __stub_dl_error_catch_tsd;

__attribute__((weak)) void **__libc_dl_error_tsd(void) { return 0; }

__attribute__((weak)) void _Unwind_ForcedUnwind(void *a, void *b, void *c) { (void)a; (void)b; (void)c; }
__attribute__((weak)) void *_Unwind_GetCFA(void *c) { (void)c; return 0; }
