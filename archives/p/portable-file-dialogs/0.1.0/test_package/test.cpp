// test_package/test.cpp — consumer of portable-file-dialogs (header-only).
// Exercises the public API without spawning dialogs (headless OHOS has no
// dialog helpers; spawning would be environment-dependent).
#include <portable-file-dialogs.h>

#include <cstdio>

int main()
{
    // public static API: verbosity toggle + helper rescan (PATH scan only)
    pfd::settings::verbose(false);
    pfd::settings::rescan();

    // API surface: dialog choice enum is a real, usable type
    pfd::choice c = pfd::choice::ok;
    (void)c;

    // API surface: dialog classes are instantiable types (no construction)
    using message_type = pfd::message;
    static_assert(sizeof(message_type) > 0, "pfd::message must be a complete type");

    std::printf("pfd api ok\n");
    return 0;
}
