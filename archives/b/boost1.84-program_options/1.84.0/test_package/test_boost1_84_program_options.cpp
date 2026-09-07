// test_package/test_boost1_84_program_options.cpp — boost1.84-program_options
// 1.84.0 consumer test (L1, upstream-derived).
//
// Derived from the upstream Boost.ProgramOptions test suite
// (libs/program_options/test/, Boost Software License 1.0). Exercises:
//   - options_description: option registration, lookups and formatting
//     (upstream options_description_test.cpp coverage)
//   - parse_command_line / parse_config_file argv parsing, long/short
//     options, default values and multitoken (upstream parsers_test.cpp /
//     cmdline_test.cpp coverage)
//   - variables_map: store/notify value extraction, count(), value_semantic
//     type checks (upstream variable_map_test.cpp coverage)
//   - positional_options_description (upstream positional_options_test.cpp)
// The upstream minitest.hpp-style assert counting is preserved so the pass
// count is reported like the upstream suite.
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include <unistd.h>

#include <boost/program_options.hpp>

namespace po = boost::program_options;

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond) do { \
    ++g_checks; \
    if (!(cond)) { \
        ++g_failures; \
        std::cerr << "FAIL line " << __LINE__ << ": " #cond << std::endl; \
    } \
} while (0)

int main(int argc, char *argv[]) {
    // ── options_description: registration and lookup ─────────────────────
    po::options_description desc("Allowed options");
    desc.add_options()
        ("help,h", "produce help message")
        ("compression,c", po::value<int>()->default_value(5), "compression level")
        ("include-path,I", po::value<std::vector<std::string> >(), "include path")
        ("name", po::value<std::string>(), "set name")
        ("output,o", po::value<std::string>()->implicit_value("a.out"), "output file");
    CHECK(desc.find_nothrow("help", false) != nullptr);
    CHECK(desc.find_nothrow("compression", false) != nullptr);
    CHECK(desc.find_nothrow("no-such-option", false) == nullptr);
    // Registered options count: help, compression, include-path, name, output
    CHECK(desc.options().size() == 5);

    // Formatting sanity: help text contains the caption and option names
    std::ostringstream help_out;
    help_out << desc;
    const std::string help_text = help_out.str();
    CHECK(help_text.find("Allowed options") != std::string::npos);
    CHECK(help_text.find("--help") != std::string::npos);
    CHECK(help_text.find("--compression") != std::string::npos);

    // ── parse_command_line: argv parsing ─────────────────────────────────
    {
        const char *fake_argv[] = {
            "test_program", "--compression", "9", "--name=boost184",
            "-I", "/usr/include", "--include-path", "/opt/include",
            "--output",
        };
        po::variables_map vm;
        po::store(po::parse_command_line(9, const_cast<char **>(fake_argv), desc), vm);
        po::notify(vm);

        CHECK(vm.count("compression") == 1);
        CHECK(vm["compression"].as<int>() == 9);
        CHECK(vm.count("name") == 1);
        CHECK(vm["name"].as<std::string>() == "boost184");
        CHECK(vm.count("include-path") == 1);
        std::vector<std::string> paths =
            vm["include-path"].as<std::vector<std::string> >();
        CHECK(paths.size() == 2);
        CHECK(paths[0] == "/usr/include");
        CHECK(paths[1] == "/opt/include");
        // implicit value filled in
        CHECK(vm.count("output") == 1);
        CHECK(vm["output"].as<std::string>() == "a.out");
        // options not on the command line
        CHECK(vm.count("help") == 0);
    }

    // ── default value without the option present ─────────────────────────
    {
        const char *fake_argv[] = {"test_program"};
        po::variables_map vm;
        po::store(po::parse_command_line(1, const_cast<char **>(fake_argv), desc), vm);
        po::notify(vm);
        CHECK(vm.count("compression") == 1);
        CHECK(vm["compression"].as<int>() == 5);  // default_value(5)
    }

    // ── unknown option rejection ─────────────────────────────────────────
    {
        const char *fake_argv[] = {"test_program", "--unknown-option"};
        po::variables_map vm;
        bool threw = false;
        try {
            po::store(po::parse_command_line(2, const_cast<char **>(fake_argv), desc), vm);
        } catch (const po::unknown_option &) {
            threw = true;
        }
        CHECK(threw);
    }

    // ── required option missing ──────────────────────────────────────────
    {
        po::options_description req_desc("required");
        req_desc.add_options()
            ("must", po::value<std::string>()->required(), "required option");
        const char *fake_argv[] = {"test_program"};
        po::variables_map vm;
        po::store(po::parse_command_line(1, const_cast<char **>(fake_argv), req_desc), vm);
        bool threw = false;
        try {
            po::notify(vm);
        } catch (const po::required_option &) {
            threw = true;
        }
        CHECK(threw);
        // supplying it clears the error
        const char *fake_argv2[] = {"test_program", "--must=ok"};
        po::variables_map vm2;
        po::store(po::parse_command_line(2, const_cast<char **>(fake_argv2), req_desc), vm2);
        po::notify(vm2);
        CHECK(vm2["must"].as<std::string>() == "ok");
    }

    // ── positional options ───────────────────────────────────────────────
    {
        po::positional_options_description p;
        p.add("input-file", -1);
        po::options_description pd("positional");
        pd.add_options()("input-file", po::value<std::vector<std::string> >(), "input");
        const char *fake_argv[] = {"test_program", "a.cpp", "b.cpp"};
        po::variables_map vm;
        po::store(po::command_line_parser(3, const_cast<char **>(fake_argv))
                      .options(pd)
                      .positional(p)
                      .run(),
                  vm);
        po::notify(vm);
        CHECK(vm.count("input-file") == 1);
        std::vector<std::string> files =
            vm["input-file"].as<std::vector<std::string> >();
        CHECK(files.size() == 2);
        CHECK(files[0] == "a.cpp");
        CHECK(files[1] == "b.cpp");
    }

    // ── parse_config_file (INI-style) ────────────────────────────────────
    {
        // Write a uniquely-named temp config file and parse it with a
        // dedicated description registering the dotted (sectioned) option
        // names, mirroring the upstream parsers_test config_file exercise
        // (m1.v1 etc.). 文件名拼入 PID 避免与 cwd 下可能残留的同名旧文件
        // 冲突（build 目录可能含历史内容导致解析到错乱段落）。
        const std::string cfg_path =
            "po_test_config_" + std::to_string(static_cast<long>(::getpid())) + ".cfg";
        {
            std::ofstream cfg(cfg_path.c_str());
            cfg << "# a comment line\n"
                << "compression=7\n"
                << "[section]\n"
                << "name=config-value\n";
            cfg.flush();
            if (!cfg.good()) {
                std::cerr << "FAIL: cannot write config file " << cfg_path << std::endl;
                ++g_failures;
            }
        }
        po::options_description cfg_desc("config");
        cfg_desc.add_options()
            ("compression", po::value<int>(), "compression level")
            ("section.name", po::value<std::string>(), "sectioned name");
        po::variables_map vm;
        std::ifstream ifs(cfg_path.c_str());
        if (!ifs.good()) {
            std::cerr << "FAIL: cannot read back config file " << cfg_path << std::endl;
            ++g_failures;
        }
        po::store(po::parse_config_file(ifs, cfg_desc), vm);
        po::notify(vm);
        CHECK(vm.count("compression") == 1);
        CHECK(vm["compression"].as<int>() == 7);
        CHECK(vm.count("section.name") == 1);
        CHECK(vm["section.name"].as<std::string>() == "config-value");
        std::remove(cfg_path.c_str());
    }

    std::cout << g_checks << " checks: " << g_failures << " failures" << std::endl;
    return g_failures == 0 ? 0 : 1;
}
