#include <cstring>
#include <iostream>
#include <memory>
#include "production_source.h"

static void require(bool value, const char *label) {
    if (!value) throw std::runtime_error(label);
}

int main(int argc, char **argv) try {
    if (argc != 3) return 2;
    // Calls the exact packaged official implementation, not a test rewrite.
    // The renamed device-creating main is never called and no fd is opened.
    std::vector<YAML::Node> configs{YAML::LoadFile(argv[1])};
    std::unique_ptr<libevdev, decltype(&libevdev_free)> device(
        evdev_create_from_yaml(configs), &libevdev_free);
    require(device.get() != nullptr, "libevdev allocation failed");
    const char *name = libevdev_get_name(device.get());
    require(name && std::strcmp(name, argv[2]) == 0, "actual NAME differs");
    const char *id = libevdev_get_uniq(device.get());
    require(id && std::strcmp(id, "private-config-proof") == 0, "actual ID differs");
    require(libevdev_get_id_vendor(device.get()) == 22136, "actual vendor differs");
    require(libevdev_get_id_product(device.get()) == 4660, "actual product differs");
    require(libevdev_get_id_bustype(device.get()) == BUS_USB, "actual bus differs");
    require(libevdev_get_id_version(device.get()) == 69, "actual version differs");
    require(libevdev_has_event_code(device.get(), EV_KEY, KEY_A), "KEY_A absent");
    require(libevdev_has_event_code(device.get(), EV_KEY, KEY_ESC), "KEY_ESC absent");
    require(!libevdev_has_event_code(device.get(), EV_KEY, KEY_Z), "undeclared KEY_Z enabled");
    require(libevdev_has_event_code(device.get(), EV_REL, REL_X), "REL_X absent");
    require(libevdev_has_event_code(device.get(), EV_REL, REL_Y), "REL_Y absent");
    const input_absinfo *axis = libevdev_get_abs_info(device.get(), ABS_X);
    require(axis && axis->value == 11 && axis->minimum == 0 &&
            axis->maximum == 65535 && axis->resolution == 15,
            "actual ABS_X metadata differs");
    std::cout << "CONFIG_PARSER_PASS=1/1; actual production YAML/libevdev state; no device creation\n";
    return 0;
} catch (const std::exception &e) {
    std::cerr << "CONFIG_PARSER_FAIL: " << e.what() << '\n';
    return 1;
}
