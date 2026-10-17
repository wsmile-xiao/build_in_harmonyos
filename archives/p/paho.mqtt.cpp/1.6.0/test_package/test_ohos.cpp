#include <sys/utsname.h>

#include <exception>
#include <iostream>
#include <string>

#include <mqtt/async_client.h>

int main() {
    struct utsname system_info {};
    if (uname(&system_info) != 0) {
        std::cerr << "uname failed on OHOS\n";
        return 1;
    }
    if (std::string(system_info.sysname) != "HarmonyOS") {
        std::cerr << "unexpected OHOS system name: " << system_info.sysname << '\n';
        return 1;
    }

    try {
        mqtt::async_client client("tcp://127.0.0.1:1883", "paho-ohos-consumer");
        if (client.get_server_uri() != "tcp://127.0.0.1:1883") {
            std::cerr << "unexpected Paho server URI on OHOS\n";
            return 1;
        }
        if (client.get_client_id() != "paho-ohos-consumer") {
            std::cerr << "unexpected Paho client id on OHOS\n";
            return 1;
        }
    }
    catch (const std::exception& error) {
        std::cerr << "Paho async_client construction failed on OHOS: "
                  << error.what() << '\n';
        return 1;
    }

    std::cout << "paho.mqtt.cpp OHOS platform test: OK\n";
    return 0;
}
