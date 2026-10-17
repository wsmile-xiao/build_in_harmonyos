#include <shmdata/type.hpp>

#include <iostream>
#include <string>

int main() {
    shmdata::Type type("application/x-shmdata-test,channels=(int)2");
    if (type.name() != "application/x-shmdata-test")
        return 1;
    if (type.str().find("channels") == std::string::npos)
        return 2;
    if (!type.get_parsing_errors().empty())
        return 3;
    std::cout << "shmdata installed-consumer type parser: PASS\n";
    return 0;
}
