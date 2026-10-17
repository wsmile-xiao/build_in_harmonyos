#include <boost/atomic.hpp>
#include <boost/archive/text_oarchive.hpp>
#include <boost/chrono.hpp>
#include <boost/beast/core/static_string.hpp>
#include <boost/filesystem.hpp>
#include <boost/format.hpp>
#include <boost/program_options.hpp>
#include <boost/regex.hpp>
#include <boost/serialization/string.hpp>
#include <boost/timer/timer.hpp>
#include <boost/thread.hpp>
#include <boost/system/error_code.hpp>

#include <sstream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    namespace po = boost::program_options;

    po::options_description options("options");
    options.add_options()
        ("name", po::value<std::string>()->required(), "name to validate")
        ("count", po::value<int>()->default_value(1), "thread increment count");

    po::variables_map vm;
    po::store(po::parse_command_line(argc, argv, options), vm);
    po::notify(vm);

    const std::string name = vm["name"].as<std::string>();
    const int count = vm["count"].as<int>();

    boost::timer::cpu_timer timer;

    if (!boost::regex_match(name, boost::regex("[A-Za-z0-9_]+"))) {
        throw std::runtime_error("regex validation failed");
    }
    const boost::filesystem::path composed = boost::filesystem::path("boost") / name;
    if (composed.generic_string() != "boost/" + name) {
        throw std::runtime_error("filesystem path composition failed");
    }
    const std::string formatted = (boost::format("%1%:%2%") % name % count).str();
    if (formatted != name + ":" + std::to_string(count)) {
        throw std::runtime_error("format interpolation failed");
    }
    boost::beast::static_string<8> beast_name;
    beast_name = name;
    if (beast_name != name) {
        throw std::runtime_error("beast static_string assignment failed");
    }
    const boost::system::error_code ok;
    if (ok) {
        throw std::runtime_error("default system error code is not clear");
    }

    std::ostringstream buffer;
    boost::archive::text_oarchive archive(buffer);
    archive << name;
    archive << count;
    if (buffer.str().empty()) {
        throw std::runtime_error("serialization produced no output");
    }

    boost::atomic<int> value(0);
    const boost::chrono::steady_clock::time_point start =
        boost::chrono::steady_clock::now();

    boost::thread worker([&value, count]() {
        for (int i = 0; i < count; ++i) {
            ++value;
        }
    });
    worker.join();

    const boost::chrono::steady_clock::time_point finish =
        boost::chrono::steady_clock::now();
    const boost::chrono::steady_clock::duration elapsed = finish - start;

    if (value.load() != count) {
        throw std::runtime_error("thread did not update value");
    }
    if (elapsed < boost::chrono::steady_clock::duration::zero()) {
        throw std::runtime_error("chrono steady clock moved backwards");
    }
    if (timer.elapsed().wall < 0) {
        throw std::runtime_error("timer wall clock moved backwards");
    }

    return 0;
}
