// test_package/src/test_boost.cpp — boost-1.85 1.85.0-b2-nodocs L1 smoke test.
// Exercises all 9 b2-built components: atomic, chrono, filesystem,
// iostreams (gzip round-trip via zlib), program_options, random, regex,
// system, thread.
#include <boost/atomic.hpp>
#include <boost/chrono.hpp>
#include <boost/filesystem.hpp>
#include <boost/iostreams/copy.hpp>
#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/filtering_stream.hpp>
#include <boost/program_options.hpp>
#include <boost/random.hpp>
#include <boost/regex.hpp>
#include <boost/system/error_code.hpp>
#include <boost/thread.hpp>
#include <iostream>
#include <sstream>
#include <string>

namespace fs = boost::filesystem;
namespace po = boost::program_options;
namespace io = boost::iostreams;

int main() {
    // Boost.System: generic error category
    boost::system::error_code ec = boost::system::errc::make_error_code(
        boost::system::errc::permission_denied);
    if (ec.value() == 0 || ec.message().empty()) {
        std::cerr << "system: bad error_code" << std::endl;
        return 1;
    }
    std::cout << "system: error_code value=" << ec.value()
              << " message=" << ec.message() << std::endl;

    // Boost.Atomic
    boost::atomic<int> x(0);
    x.store(42, boost::memory_order_release);
    int v = x.load(boost::memory_order_acquire);
    if (v != 42) { std::cerr << "atomic: load mismatch" << std::endl; return 1; }
    std::cout << "atomic: value = " << v << std::endl;

    // Boost.Chrono
    boost::chrono::milliseconds dur(100);
    if (dur.count() != 100) { std::cerr << "chrono: mismatch" << std::endl; return 1; }
    std::cout << "chrono: " << dur.count() << "ms" << std::endl;

    // Boost.Filesystem
    fs::path p("/tmp/boost_b2_nodocs_test");
    if (!p.has_filename()) { std::cerr << "filesystem: no filename" << std::endl; return 1; }
    std::cout << "filesystem: path filename = " << p.filename() << std::endl;

    // Boost.Regex
    boost::regex re("(\\d+)-(\\d+)");
    boost::smatch what;
    std::string text = "version 1-85-0";
    if (!boost::regex_search(text, what, re)) {
        std::cerr << "regex: no match" << std::endl;
        return 1;
    }
    std::cout << "regex: matched '" << what[0] << "'" << std::endl;

    // Boost.ProgramOptions
    po::options_description desc("options");
    desc.add_options()
        ("help", "show help")
        ("name", po::value<std::string>(), "set name");
    po::variables_map vm;
    char arg0[] = "test_boost";
    char arg1[] = "--name=b2nodocs";
    char *fake_argv[] = {arg0, arg1};
    try {
        po::store(po::parse_command_line(2, fake_argv, desc), vm);
    } catch (const std::exception &e) {
        std::cerr << "program_options: parse failed: " << e.what() << std::endl;
        return 1;
    }
    if (vm.count("name") == 0) { std::cerr << "program_options: --name missing" << std::endl; return 1; }
    std::cout << "program_options: --name = " << vm["name"].as<std::string>() << std::endl;

    // Boost.Random
    boost::random::mt19937 rng(42);
    boost::random::uniform_int_distribution<> dist(1, 100);
    int rv = dist(rng);
    if (rv < 1 || rv > 100) { std::cerr << "random: out of range" << std::endl; return 1; }
    std::cout << "random: uniform_int = " << rv << std::endl;

    // Boost.Thread
    int shared = 0;
    boost::thread t([&shared] { shared = 7; });
    t.join();
    if (shared != 7) { std::cerr << "thread: shared not updated" << std::endl; return 1; }
    std::cout << "thread: shared = " << shared << std::endl;

    // Boost.Iostreams: gzip compress then decompress round-trip (zlib-backed)
    const std::string payload = "b2-nodocs iostreams gzip round-trip 0123456789";
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
        std::cerr << "iostreams: gzip round-trip mismatch" << std::endl;
        return 1;
    }
    std::cout << "iostreams: gzip round-trip OK (" << payload.size() << " -> "
              << compressed.str().size() << " bytes)" << std::endl;

    std::cout << "boost-1.85 1.85.0-b2-nodocs: all 9 b2-built components OK" << std::endl;
    return 0;
}
