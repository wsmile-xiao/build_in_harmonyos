#include <c4/log/log.hpp>
#include <c4/log/export.hpp>
#include <iostream>

static void my_pump(const char* s, size_t n) {
    (void)s; (void)n;
}

int main() {
    // 1. test set/get logpump
    c4::logns::set_logpump(my_pump);
    auto fn = c4::logns::get_logpump();
    if (fn != my_pump) {
        std::cerr << "get_logpump mismatch" << std::endl;
        return 1;
    }
    c4::logns::set_logpump(nullptr);
    auto fn2 = c4::logns::get_logpump();
    if (fn2 == my_pump) {
        std::cerr << "reset pump failed" << std::endl;
        return 2;
    }

    // 2. test DumpBuf API
    auto* buf = c4::logns::detail::_dump_buf();
    if (!buf) {
        std::cerr << "dump_buf null" << std::endl;
        return 3;
    }
    buf->reserve(64);
    if (buf->capacity() < 64) {
        std::cerr << "reserve failed" << std::endl;
        return 4;
    }
    buf->resize(10);
    if (buf->size() != 10) {
        std::cerr << "resize failed" << std::endl;
        return 5;
    }
    buf->shrink_to_fit();
    // after shrink, capacity should be at least size
    if (buf->capacity() < buf->size()) {
        std::cerr << "shrink failed" << std::endl;
        return 6;
    }

    // 3. test that log header is usable - check export macro exists
    // Do not actually call log print to avoid side effects, just verify link
    std::cout << "c4log test passed - pump, buf ok" << std::endl;
    return 0;
}
