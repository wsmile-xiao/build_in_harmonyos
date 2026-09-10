#include <boost/pfr.hpp>
#include <boost/pfr/io.hpp>

#include <sstream>
#include <string>

struct person {
    int id;
    std::string name;
};

int main() {
    person value{42, "Ada"};

    if (boost::pfr::tuple_size<person>::value != 2) {
        return 1;
    }
    if (boost::pfr::get<0>(value) != 42 || boost::pfr::get<1>(value) != "Ada") {
        return 2;
    }

    int visited = 0;
    boost::pfr::for_each_field(value, [&visited](const auto&) { ++visited; });
    if (visited != 2) {
        return 3;
    }

    std::ostringstream output;
    output << boost::pfr::io(value);
    if (output.str().find("Ada") == std::string::npos) {
        return 4;
    }

    return 0;
}
