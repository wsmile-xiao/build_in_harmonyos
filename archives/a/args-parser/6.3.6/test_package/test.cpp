#include <iostream>
#include <args-parser/all.hpp>

using namespace Args;

int main(int argc, char **argv)
{
    try {
        CmdLine cmd(argc, argv);
        Arg help(String("help"), true);
        cmd.addArg(&help);
        Arg port('p', String("port"), true);
        cmd.addArg(&port);
        cmd.parse();
        if (help.isDefined() && help.value() == String("on")) {
            std::cout << "args-parser test: help defined" << std::endl;
        } else {
            std::cout << "args-parser test: parse ok" << std::endl;
        }
    } catch (const std::exception &e) {
        std::cerr << "args-parser test: unexpected exception: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}