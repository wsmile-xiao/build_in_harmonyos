/*
 * Consumer test for kea-hooks.
 *
 * Links against the packaged libkea-hooks.so and drives the public hooks
 * framework API the way a Kea server or a user hook library does: the hook
 * registry (ServerHooks), the command <-> hook name mapping and the hook
 * library description model (HookLibInfo / extractNames).  A dummy package
 * that shipped no library or a stub one would fail to link or fail these
 * checks.
 */
#include <hooks/hooks.h>
#include <hooks/libinfo.h>
#include <hooks/server_hooks.h>

#include <cc/data.h>

#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

void
check(bool ok, const std::string& what) {
    std::cout << (ok ? "[  OK  ] " : "[ FAIL ] ") << what << "\n";
    if (!ok) {
        ++failures;
    }
}

} // namespace

int
main() {
    // 1) Hook framework ABI version exported by the packaged headers.
    check(KEA_HOOKS_VERSION == 30003, "KEA_HOOKS_VERSION is 30003 (Kea 3.0.3)");

    // 2) ServerHooks registry, implemented in libkea-hooks.so.
    isc::hooks::ServerHooks& hooks = isc::hooks::ServerHooks::getServerHooks();
    const std::string name("kea_hooks_consumer_test");
    const int index = hooks.registerHook(name);
    check(index >= 2, "registerHook() returns an index past context_create/destroy");
    check(hooks.getIndex(name) == index, "getIndex() round-trips the registered hook");
    check(hooks.getName(index) == name, "getName() round-trips the registered hook");
    check(hooks.findIndex("kea_hooks_absent_hook") == -1,
          "findIndex() reports -1 for an unknown hook");
    check(hooks.getCount() > 2, "getCount() counts the registered hooks");

    // 3) command name <-> hook name conversion (static framework logic).
    check(isc::hooks::ServerHooks::commandToHookName("kea-hooks-pkg-test") ==
              "$kea_hooks_pkg_test",
          "commandToHookName() prefixes '$' and maps '-' to '_'");
    check(isc::hooks::ServerHooks::hookToCommandName("$kea_hooks_pkg_test") ==
              "kea-hooks-pkg-test",
          "hookToCommandName() reverses the conversion");

    // 4) Hook library description model used by the configuration parsers.
    isc::hooks::HookLibsCollection libs;
    libs.push_back(isc::hooks::HookLibInfo(
        "/opt/kea/lib/kea/hooks/libdhcp_perfmon.so", isc::data::ConstElementPtr()));
    libs.push_back(isc::hooks::HookLibInfo(
        "/opt/kea/lib/kea/hooks/libdhcp_limits.so", isc::data::ConstElementPtr()));
    const std::vector<std::string> names = isc::hooks::extractNames(libs);
    check(names.size() == 2 &&
              names[0] == "/opt/kea/lib/kea/hooks/libdhcp_perfmon.so",
          "extractNames() returns the configured library paths");

    if (failures != 0) {
        std::cerr << failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "kea-hooks/3.0.3 OK" << std::endl;
    return 0;
}
