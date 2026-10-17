#include <iostream>
#include <sstream>
#include <string>

#include <cppcmd/CommandInterpreter.hpp>
#include <cppcmd/Expression.hpp>

using namespace cppcmd;

// Consumer test: uses only the public headers and the public API of cppcmd.
// Registers a command, feeds input, and verifies observable output.
int main() {
    std::stringstream inputStream, outputStream;
    CommandInterpreter interpreter(inputStream, outputStream);

    interpreter.registerCommand("add", [](const auto& args, auto& os) {
        int result = 0;
        for (const auto& value : args) result += as<int>(value);
        os << result << std::endl;
    });

    inputStream << "add 1 2 3\n";
    interpreter.run();

    std::string line;
    std::getline(outputStream, line);
    if (line != "6") {
        std::cerr << "FAIL: expected '6', got '" << line << "'" << std::endl;
        return 1;
    }

    // Exercise Expression parsing through the public API as well
    Expression<std::string, std::vector<std::string>> exp{"cmd arg1 arg2"};
    if (!exp || exp.command() != "cmd" || exp.args().size() != 2) {
        std::cerr << "FAIL: expression parse mismatch" << std::endl;
        return 1;
    }

    std::cout << "test cppcmd 0.1.0: OK (add -> " << line << ", expression parsed)"
              << std::endl;
    return 0;
}