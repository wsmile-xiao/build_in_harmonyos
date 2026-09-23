#include <boost/regex.hpp>

#include <iostream>
#include <string>

int main() {
    const std::string input = "user@example.com";
    const boost::regex pattern("^([[:alnum:]_.+-]+)@([[:alnum:].-]+)$");
    boost::smatch match;
    if (!boost::regex_match(input, match, pattern) || match.size() != 3) {
        std::cerr << "boost regex test: match failed" << std::endl;
        return 1;
    }
    if (match[1].str() != "user" || match[2].str() != "example.com") {
        std::cerr << "boost regex test: capture groups incorrect" << std::endl;
        return 1;
    }
    const std::string replaced = boost::regex_replace(
        input, pattern, "$1@open-harmony.org", boost::format_all);
    if (replaced != "user@open-harmony.org") {
        std::cerr << "boost regex test: replacement failed" << std::endl;
        return 1;
    }
    std::cout << "boost regex consumer test passed" << std::endl;
    return 0;
}
