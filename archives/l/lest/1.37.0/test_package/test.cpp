#include <lest/lest.hpp>
#include <string>

const lest::test specification[] = {
    CASE("string length") {
        EXPECT(std::string("harmony").size() == 7);
    },
    CASE("integer arithmetic") {
        EXPECT(2 + 3 == 5);
    },
};

int main() {
    return lest::run(specification);
}
