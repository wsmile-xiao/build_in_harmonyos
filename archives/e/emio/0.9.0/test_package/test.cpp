// test_package consumer test for emio 0.9.0 (header-only C++20).
// Exercises the real high-level and low-level public API:
// emio::format / emio::static_buffer / emio::format_to / emio::writer / emio::reader.
#include <string>

#include <emio/emio.hpp>

int main() {
    // High-level: format to std::string.
    const std::string str = emio::format("The answer is {}.", 42);
    if (str != "The answer is 42.") {
        return 1;
    }

    // Without heap: static_buffer + format_to.
    emio::static_buffer<128> buf{};
    emio::format_to(buf, "The answer is {:#x}.", 42).value();
    if (buf.view() != "The answer is 0x2a.") {
        return 2;
    }

    // Low-level writer.
    emio::writer wrt{buf};
    wrt.write_str(" In decimal: ").value();
    wrt.write_int(42).value();
    wrt.write_char('.').value();
    if (buf.view() != "The answer is 0x2a. In decimal: 42.") {
        return 3;
    }

    // Low-level reader.
    emio::reader rdr{"17c"};
    auto number = rdr.parse_int<uint32_t>();
    auto suffix = rdr.read_char();
    if (!number || !suffix || *number != 17 || *suffix != 'c') {
        return 4;
    }

    // scan high-level.
    int answer{};
    if (!emio::scan(str, "The answer is {}.", answer) || answer != 42) {
        return 5;
    }

    return 0;
}