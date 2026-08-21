#include <vamp-hostsdk/vamp-hostsdk.h>

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

// Real consumption of the installed Vamp host SDK:
// list the plugins visible on VAMP_PATH (may be empty on a fresh system)
// and report the SDK key composition API working end to end.
int main() {
    Vamp::HostExt::PluginLoader *loader =
        Vamp::HostExt::PluginLoader::getInstance();
    if (!loader) {
        std::cerr << "FAIL: PluginLoader::getInstance() returned null" << std::endl;
        return 1;
    }
    std::vector<Vamp::HostExt::PluginLoader::PluginKey> keys =
        loader->listPlugins();
    std::string composed =
        loader->composePluginKey("vamp-smoke", "smoke");
    // Upstream Impl::composePluginKey returns "<lowercased-basename>:<identifier>"
    // (see src/vamp-hostsdk/PluginLoader.cpp Impl::composePluginKey).
    if (composed != "vamp-smoke:smoke") {
        std::cerr << "FAIL: composePluginKey returned " << composed << std::endl;
        return 1;
    }
    std::cout << "vamp-plugin-sdk OK: loader alive, " << keys.size()
              << " plugin(s) on VAMP_PATH, composePluginKey=" << composed
              << std::endl;
    return 0;
}
