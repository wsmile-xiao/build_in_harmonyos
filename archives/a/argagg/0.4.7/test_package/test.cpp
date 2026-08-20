// test_package/test.cpp — R34: substantive test that uses argagg API
// Parses a set of command-line arguments and verifies the parser results.
#include <argagg/argagg.hpp>
#include <iostream>
#include <string>

int main() {
    argagg::parser argparser{{
        {"help", {"-h", "--help"}, "show help", 0},
        {"version", {"-V", "--version"}, "print version", 0},
        {"output", {"-o", "--output"}, "output file", 1},
    }};

    // Simulated command-line: test_argagg --output result.txt --version input.dat
    const char* test_argv[] = {
        "test_argagg", "--output", "result.txt", "--version", "input.dat"};
    int test_argc = 5;

    argagg::parser_results args =
        argparser.parse(test_argc, const_cast<char**>(test_argv));

    // Verify "output" option was found with the right argument
    if (!args.has_option("output")) {
        std::cerr << "FAIL: output option not found" << std::endl;
        return 1;
    }
    std::string output_file = args["output"].as<std::string>();
    if (output_file != "result.txt") {
        std::cerr << "FAIL: output file is '" << output_file
                  << "', expected 'result.txt'" << std::endl;
        return 1;
    }

    // Verify "version" flag was found
    if (!args.has_option("version")) {
        std::cerr << "FAIL: version option not found" << std::endl;
        return 1;
    }

    // Verify "help" flag was NOT found
    if (args.has_option("help")) {
        std::cerr << "FAIL: help option should not be found" << std::endl;
        return 1;
    }

    // Verify positional arguments
    if (args.count() != 1) {
        std::cerr << "FAIL: expected 1 positional arg, got " << args.count()
                  << std::endl;
        return 1;
    }
    std::string pos_arg = args.as<std::string>(0);
    if (pos_arg != "input.dat") {
        std::cerr << "FAIL: positional arg is '" << pos_arg
                  << "', expected 'input.dat'" << std::endl;
        return 1;
    }

    std::cout << "argagg test passed: all assertions OK" << std::endl;
    return 0;
}
