#include <opendht/infohash.h>

#include <iostream>
#include <string>

int main() {
    const dht::InfoHash h = dht::InfoHash::get("opendht-ohos");
    const std::string s = h.toString();
    if (s.size() != 40) {
        std::cerr << "bad hash size " << s.size() << "\n";
        return 1;
    }
    if (!static_cast<bool>(h)) {
        std::cerr << "zero hash\n";
        return 2;
    }
    std::cout << "opendht version=3.7.1 hash=" << s << " ok\n";
    return 0;
}
