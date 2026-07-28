#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#include <bitsery/adapter/buffer.h>
#include <bitsery/bitsery.h>
#include <bitsery/traits/string.h>
#include <bitsery/traits/vector.h>

struct Record {
    std::uint32_t id{};
    std::string name;
    std::vector<std::int16_t> samples;
};

template <typename S>
void serialize(S& s, Record& record) {
    s.value4b(record.id);
    s.text1b(record.name, 64);
    s.container2b(record.samples, 16);
}

int main() {
    using Buffer = std::vector<std::uint8_t>;
    using OutputAdapter = bitsery::OutputBufferAdapter<Buffer>;
    using InputAdapter = bitsery::InputBufferAdapter<Buffer>;

    Record source{42U, "openharmony", {1, -2, 3, 5, 8}};
    Buffer buffer;

    const auto written = bitsery::quickSerialization<OutputAdapter>(buffer, source);
    if (written == 0 || buffer.empty()) {
        std::cerr << "bitsery serialization produced no bytes\n";
        return 1;
    }

    Record decoded;
    const auto state = bitsery::quickDeserialization<InputAdapter>({buffer.begin(), written}, decoded);
    if (state.first != bitsery::ReaderError::NoError || !state.second) {
        std::cerr << "bitsery deserialization failed\n";
        return 1;
    }

    if (decoded.id != source.id || decoded.name != source.name || decoded.samples != source.samples) {
        std::cerr << "bitsery round-trip data mismatch\n";
        return 1;
    }

    std::cout << "bitsery round-trip test passed, bytes=" << written << "\n";
    return 0;
}
