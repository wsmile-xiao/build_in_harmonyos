#include <jack/jack.h>
#include <jack/ringbuffer.h>

#include <cstring>
#include <iostream>

namespace {

bool check(bool condition, const char* message)
{
    if (!condition) {
        std::cerr << "jack smoke check failed: " << message << std::endl;
        return false;
    }
    return true;
}

} // namespace

int main()
{
    const char* version = jack_get_version_string();
    if (!check(version != nullptr, "version string is null")) {
        return 1;
    }
    if (!check(std::strlen(version) > 0, "version string is empty")) {
        return 1;
    }

    const unsigned int client_name_size = jack_client_name_size();
    const unsigned int port_name_size = jack_port_name_size();
    if (!check(client_name_size > 0, "client name size is zero")) {
        return 1;
    }
    if (!check(port_name_size > client_name_size, "port name size is not larger")) {
        return 1;
    }

    jack_ringbuffer_t* ring = jack_ringbuffer_create(64);
    if (!check(ring != nullptr, "ringbuffer allocation failed")) {
        return 1;
    }

    const char payload[] = "ohos-jack-smoke";
    const size_t bytes = std::strlen(payload);
    const size_t written = jack_ringbuffer_write(ring, payload, bytes);
    if (!check(written == bytes, "ringbuffer write length mismatch")) {
        jack_ringbuffer_free(ring);
        return 1;
    }
    const size_t available = jack_ringbuffer_read_space(ring);
    if (!check(available == bytes, "ringbuffer read space mismatch after write")) {
        jack_ringbuffer_free(ring);
        return 1;
    }

    char output[32] = {};
    const size_t read_bytes = jack_ringbuffer_read(ring, output, bytes);
    if (!check(read_bytes == bytes, "ringbuffer read length mismatch")) {
        jack_ringbuffer_free(ring);
        return 1;
    }
    if (!check(std::strcmp(output, payload) == 0, "ringbuffer payload mismatch")) {
        jack_ringbuffer_free(ring);
        return 1;
    }
    if (!check(jack_ringbuffer_read_space(ring) == 0, "ringbuffer not empty after read")) {
        jack_ringbuffer_free(ring);
        return 1;
    }

    jack_ringbuffer_free(ring);
    std::cout << "jack consumer smoke passed: " << version << std::endl;
    return 0;
}
