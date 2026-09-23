// test_package/test_boost.cpp — boost 1.85.0 L1 smoke test.
// Exercises Boost.Filesystem, Boost.Regex, Boost.ProgramOptions, and
// Boost.Iostreams (gzip compress/decompress).
#include <boost/filesystem.hpp>
#include <boost/regex.hpp>
#include <boost/program_options.hpp>
#include <boost/iostreams/copy.hpp>
#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/filtering_stream.hpp>
#include <iostream>
#include <sstream>
#include <string>

namespace fs = boost::filesystem;
namespace po = boost::program_options;
namespace io = boost::iostreams;

int main(int argc, char *argv[]) {
    // Boost.Filesystem: create temp path, check it
    fs::path p("/tmp/boost_test_dir");
    if (!p.has_filename()) {
        std::cerr << "filesystem: path has no filename" << std::endl;
        return 1;
    }
    std::cout << "filesystem: path filename = " << p.filename() << std::endl;

    // Boost.Regex: match a pattern
    boost::regex re("(\\d+)-(\\d+)");
    boost::smatch what;
    std::string text = "version 1-85-0";
    if (!boost::regex_search(text, what, re)) {
        std::cerr << "regex: no match found" << std::endl;
        return 1;
    }
    std::cout << "regex: matched '" << what[0] << "'" << std::endl;

    // Boost.ProgramOptions: parse a simple option
    po::options_description desc("options");
    desc.add_options()
        ("help", "show help")
        ("name", po::value<std::string>(), "set name");

    po::variables_map vm;
    char arg0[] = "test_boost";
    char arg1[] = "--name=boost185";
    char *fake_argv[] = {arg0, arg1};
    try {
        po::store(po::parse_command_line(2, fake_argv, desc), vm);
    } catch (const std::exception &e) {
        std::cerr << "program_options: parse failed: " << e.what() << std::endl;
        return 1;
    }
    if (vm.count("name") == 0) {
        std::cerr << "program_options: --name not found" << std::endl;
        return 1;
    }
    std::cout << "program_options: --name = " << vm["name"].as<std::string>() << std::endl;

    // Boost.Iostreams: gzip compress then decompress round-trip
    const std::string payload = "boost iostreams gzip round-trip test 0123456789";
    std::stringstream compressed(std::ios::in | std::ios::out | std::ios::binary);
    {
        std::istringstream raw(payload);
        io::filtering_ostream out;
        out.push(io::gzip_compressor());
        out.push(compressed);
        io::copy(raw, out);
    }
    if (compressed.str().empty()) {
        std::cerr << "iostreams: gzip compression produced empty output" << std::endl;
        return 1;
    }
    std::stringstream decompressed(std::ios::in | std::ios::out | std::ios::binary);
    {
        io::filtering_istream in;
        in.push(io::gzip_decompressor());
        in.push(compressed);
        io::copy(in, decompressed);
    }
    if (decompressed.str() != payload) {
        std::cerr << "iostreams: gzip round-trip mismatch (expected '" << payload
                  << "', got '" << decompressed.str() << "')" << std::endl;
        return 1;
    }
    std::cout << "iostreams: gzip round-trip OK (" << payload.size() << " -> "
              << compressed.str().size() << " bytes)" << std::endl;

    std::cout << "boost 1.85.0: filesystem + regex + program_options + iostreams OK" << std::endl;
    return 0;
}
