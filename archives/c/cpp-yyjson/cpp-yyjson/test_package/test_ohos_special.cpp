// HarmonyOS-specific device test. uname() verifies the real OS and architecture;
// JSON reflection and read/write operations then exercise the package on that device.
#include <cpp_yyjson.hpp>

#include <sys/utsname.h>

#include <iostream>
#include <string>

struct DeviceConfig
{
    int api_level;
    bool enabled;
    std::string device;
};
VISITABLE_STRUCT(DeviceConfig, api_level, enabled, device);

int main()
{
    struct utsname system_info
    {
    };
    if (uname(&system_info) != 0)
    {
        std::cerr << "HarmonyOS test: uname() failed\n";
        return 1;
    }
    if (std::string(system_info.sysname) != "HarmonyOS"
        || std::string(system_info.machine) != "aarch64")
    {
        std::cerr << "HarmonyOS test: expected HarmonyOS/aarch64, got " << system_info.sysname << '/'
                  << system_info.machine << '\n';
        return 1;
    }

    using namespace yyjson;
    const auto encoded = writer::value(DeviceConfig{6, true, "HarmonyOS PC"}).write();
    const auto decoded = cast<DeviceConfig>(read(encoded));
    if (decoded.api_level != 6 || !decoded.enabled || decoded.device != "HarmonyOS PC")
    {
        std::cerr << "HarmonyOS test: reflected JSON round-trip returned wrong values\n";
        return 1;
    }

    auto parsed = read(R"({"features":["aarch64","ohos"],"memory_mb":8192})");
    const auto parsed_object = parsed.as_object();
    if (!parsed_object || (*parsed_object)["memory_mb"].as_uint().value_or(0) != 8192)
    {
        std::cerr << "HarmonyOS test: JSON reader failed on device payload\n";
        return 1;
    }

    std::cout << "HarmonyOS test passed on " << system_info.sysname << '/' << system_info.machine
              << ": reflected serialization and parsing executed\n";
    return 0;
}
