// test_package consumer — args 6.6.0
// 消费者程序：用内置固定 argv 数组驱动 args.hxx 解析，断言结果后退出
// （不依赖外部传入命令行，避免 conan test() 无参调用的不确定性）
#include <args.hxx>

#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>

int main()
{
    // 模拟命令行：--output /data/out.txt --arch aarch64 --jobs 4 --verbose
    const char *argv[] = {
        "test_package_args",
        "--output", "/data/out.txt",
        "--arch", "aarch64",
        "--jobs", "4",
        "--verbose",
        nullptr
    };
    const int argc = 8;

    args::ArgumentParser parser("args test_package consumer");
    args::ValueFlag<std::string> output(parser, "path", "output path", {"output"});
    args::ValueFlag<std::string> arch(parser, "arch", "target arch", {"arch"}, "aarch64");
    args::ValueFlag<int> jobs(parser, "n", "job count", {"jobs"}, 1);
    args::Flag verbose(parser, "verbose", "verbose", {"verbose"});

    try
    {
        parser.ParseCLI(argc, const_cast<char **>(argv));
    }
    catch (const args::Help &)
    {
        std::cout << parser;
        return 0;
    }
    catch (const args::ParseError &e)
    {
        std::cerr << e.what() << '\n';
        return 2;
    }

    const std::string out = args::get(output);
    const std::string a = args::get(arch);
    const int j = args::get(jobs);
    const bool v = verbose;

    if (out != "/data/out.txt" || a != "aarch64" || j != 4 || !v)
    {
        std::cerr << "args consumer assertion failed\n";
        return 1;
    }
    std::cout << "ARGS_TEST_PACKAGE_PASS arch=" << a << " jobs=" << j << "\n";
    return 0;
}