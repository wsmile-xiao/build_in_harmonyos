// test_package consumer test — exercises the real fancyargumentparser API.
// Covers: ArgumentParser construction, named + positional args, parse and
// typed retrieval, mirroring the upstream test suite's usage patterns.
#include <string>
#include <vector>

#include "argparse.h"

int main(int argc, char** argv)
{
    (void)argc;
    (void)argv;

    // 1) Named argument parse (upstream test_namespace pattern)
    {
        argparse::ArgumentParser parser("greet");
        parser.AddArgument(argparse::CreateNamedArgument("n", "name", 1,
            argparse::ArgTypeCast::e_String, true));
        auto obj = parser.ParseArgs(std::vector<std::string>{ "--name", "World" });
        if (!obj.IsArgValid())
            return 1;
        if (obj.GetArg("name").GetAsString() != "World")
            return 2;
    }

    // 2) Positional + typed (int) argument via aggregate spec
    {
        argparse::ArgumentParser parser("count");
        parser.AddArgument(argparse::CreatePositionalArgument({
            .name = "n",
            .nargs = 1,
            .type = argparse::ArgTypeCast::e_int,
            .required = true,
            .help = "a number",
        }));
        auto obj = parser.ParseArgs(std::vector<std::string>{ "42" });
        if (!obj.IsArgValid())
            return 3;
        if (obj.GetArg("n").GetAsInt() != 42)
            return 4;
    }

    // 3) Optional long-form flag presence
    {
        argparse::ArgumentParser parser("flag");
        parser.AddArgument(argparse::CreateNamedArgument("v", "verbose", 0,
            argparse::ArgTypeCast::e_bool, false));
        auto obj = parser.ParseArgs(std::vector<std::string>{ "--verbose" });
        if (!obj.IsArgValid())
            return 5;
        if (!obj.GetArg("verbose").GetArgumentExists())
            return 6;
    }

    return 0;
}