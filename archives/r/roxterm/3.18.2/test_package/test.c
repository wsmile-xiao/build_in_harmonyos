/*
 * test_package consumer probe — roxterm/3.18.2 (GUI application, no C API).
 *
 * roxterm installs GTK3 GUI executables (bin/roxterm, bin/roxterm-config)
 * and data files, not a linkable library or installed headers. The
 * consumer-side test in conanfile.py therefore verifies the packaged
 * artifact directly (ELF magic / AArch64 machine / DT_NEEDED closure
 * incl. libvte-2.91 / libgtk-3 / libdbus-glib-1 / dynamic-loader
 * resolution probe). This translation unit exists so the test_package
 * still exercises the OHOS toolchain (compile + link) the way every
 * consumer build would.
 */
int main(void)
{
    /* toolchain probe only: roxterm has no public C API to call */
    return 0;
}
