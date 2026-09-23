// test_package/test_pan.cxx — pan 0.165 consumer-side link & smoke test.
//
// pan is an application (no installed headers/libraries of its own), so
// the link-level proof targets its two REQUIRED library dependencies the
// way pan itself uses them (pan CMakeLists: PkgConfig::GMIME +
// PkgConfig::GTK3):
//   - gmime-3.0: g_mime_init()/g_mime_shutdown() (called by pan main()),
//     gmime_major/minor/micro_version constants to print the linked
//     GMime version (gmime-3.0 has no g_mime_version_string()).
//   - gtk+-3.0: gtk_get_major/minor/micro_version (header-only constants
//     still exercise the pkg-config include path resolution); NO gtk_init()
//     since the runner is headless.
// The real end-to-end proof is the packaged pan binary itself
// (pan --version / --help), driven from test_package/conanfile.py.

#include <cstdio>
#include <cstdlib>

#include <gmime/gmime.h>
#include <gtk/gtk.h>

int main(void)
{
    // gmime init/shutdown exactly like pan/gui/pan.cc main() does.
    g_mime_init();

    std::printf("gmime version: %u.%u.%u\n",
                gmime_major_version, gmime_minor_version, gmime_micro_version);
    if (gmime_major_version != 3)
    {
        std::fprintf(stderr, "FAIL: expected GMime major 3\n");
        return 1;
    }

    std::printf("gtk version: %d.%d.%d\n",
                gtk_get_major_version(), gtk_get_minor_version(),
                gtk_get_micro_version());
    if (gtk_get_major_version() != 3)
    {
        std::fprintf(stderr, "FAIL: expected GTK major 3\n");
        return 1;
    }

    g_mime_shutdown();
    std::printf("test_pan: gmime+gtk link OK\n");
    return 0;
}
