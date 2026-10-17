#include <docopt/docopt.h>

#include <iostream>
#include <string>
#include <vector>

int docopt_secondary_consumer_check(void);

int main() {
    static const char usage[] = R"(Usage:
  copier copy <source> <destination> [--force] [--count=<n>]

Options:
  -f --force       Overwrite destination.
  --count=<n>      Number of copies [default: 1].
)";

    const std::vector<std::string> argv = {
        "copy", "input.txt", "output.txt", "--force", "--count=3"
    };
    const docopt::Options options = docopt::docopt_parse(usage, argv, false);

    if (!options.at("copy").asBool()) {
        std::cerr << "copy command was not parsed" << std::endl;
        return 1;
    }
    if (options.at("<source>").asString() != "input.txt") {
        std::cerr << "source argument mismatch" << std::endl;
        return 2;
    }
    if (options.at("<destination>").asString() != "output.txt") {
        std::cerr << "destination argument mismatch" << std::endl;
        return 3;
    }
    if (!options.at("--force").asBool()) {
        std::cerr << "force option was not parsed" << std::endl;
        return 4;
    }
    if (options.at("--count").asString() != "3") {
        std::cerr << "count option mismatch" << std::endl;
        return 5;
    }
    if (docopt_secondary_consumer_check() != 0) {
        std::cerr << "secondary consumer check failed" << std::endl;
        return 6;
    }

    std::cout << "docopt.cpp parsed command, positional arguments, flag, and value" << std::endl;
    return 0;
}
