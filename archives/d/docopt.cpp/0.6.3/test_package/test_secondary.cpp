#include <docopt/docopt.h>

#include <string>
#include <vector>

int docopt_secondary_consumer_check(void) {
    static const char usage[] = "Usage:\n  tool [--verbose]\n";
    const std::vector<std::string> argv = {"--verbose"};
    const docopt::Options options = docopt::docopt_parse(usage, argv, false);
    return options.at("--verbose").asBool() ? 0 : 1;
}
