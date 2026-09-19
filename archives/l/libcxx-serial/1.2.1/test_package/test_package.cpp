// Consumer smoke test for libcxx-serial 1.2.1 (upstream wjwwood/serial).
//
// Exercises the compiled library end to end without serial hardware:
// serial::list_ports() drives the sysfs tty enumeration
// (src/impl/list_ports/list_ports_linux.cc) through the public API, and the
// bytesize/parity/stopbits/flowcontrol enums validate the API surface that
// consumers compile against.
#include <cstdio>
#include <string>
#include <vector>

#include <serial/serial.h>

int main() {
    std::vector<serial::PortInfo> ports;
    try {
        ports = serial::list_ports();
    } catch (const std::exception &e) {
        std::printf("list_ports() threw: %s\n", e.what());
        return 1;
    }
    std::printf("libcxx-serial consumer test: %zu serial port(s) enumerated\n",
                ports.size());
    for (size_t i = 0; i < ports.size(); ++i) {
        std::printf("  port[%zu]: port=%s description=%s hardware_id=%s\n", i,
                    ports[i].port.c_str(), ports[i].description.c_str(),
                    ports[i].hardware_id.c_str());
    }

    if (serial::fivebits != static_cast<serial::bytesize_t>(5) ||
        serial::eightbits != static_cast<serial::bytesize_t>(8) ||
        serial::parity_none != serial::parity_t(0) ||
        serial::stopbits_one != serial::stopbits_t(1) ||
        serial::flowcontrol_none != serial::flowcontrol_t(0)) {
        std::printf("API enum values unexpected\n");
        return 1;
    }
    std::printf("API enums OK\n");
    return 0;
}
