/*
 * test_package consumer probe — klavaro/3.14 (GUI application, no C API).
 *
 * klavaro installs a GTK3 GUI executable (bin/klavaro) and data files,
 * not a linkable library or installed headers. The consumer-side test in
 * conanfile.py therefore verifies the packaged artifact directly (ELF
 * magic / AArch64 machine / DT_NEEDED closure incl. libgtkdatabox.so.1 +
 * libcurl.so.4 / dynamic-loader resolution probe). This translation unit
 * exists so the test_package still exercises the OHOS cross toolchain
 * (compile + link) the way every consumer build would.
 */
int main(void)
{
    /* toolchain probe only: klavaro has no public C API to call */
    return 0;
}
