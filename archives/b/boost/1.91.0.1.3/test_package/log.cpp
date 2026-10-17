// Boost.Log / Boost.JSON / Boost.Program_options / Boost.Filesystem
// consumer contract for the boost 1.91.0.1.3 clang-include-graph variant.
//
// Exercises the exact component set clang-include-graph 0.2.0 resolves
// (Boost::graph program_options filesystem log_setup log unit_test_framework
// json). Graph and unit_test_framework are header/interface-only here; the
// compiled contract is proven by a real Boost.Log file-sink runtime round
// trip plus program_options parsing and JSON object access.
#include <boost/filesystem.hpp>
#include <boost/json.hpp>
#include <boost/log/core.hpp>
#include <boost/log/trivial.hpp>
#include <boost/log/utility/setup/file.hpp>
#include <boost/program_options.hpp>

#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>

int main(int argc, char** argv) {
    // Boost.Program_options: parse the real command line (no required keys).
    {
        namespace po = boost::program_options;
        po::options_description desc("allowed");
        desc.add_options()("help,h", "produce help");
        po::variables_map vm;
        po::store(po::parse_command_line(argc, argv, desc), vm);
        po::notify(vm);
    }

    // Boost.JSON: parse and read a value back (header-only backend).
    {
        boost::json::value parsed = boost::json::parse(
            "{\"k\":\"boost-json-contract\"}");
        if (parsed.as_object().at("k").as_string() != "boost-json-contract") {
            return 2;
        }
    }

    // Boost.Log + Boost.Log_setup: real file-sink runtime round trip.
    const std::string logfile = "boost_log_contract.log";
    std::remove(logfile.c_str());
    {
        namespace logging = boost::log;
        logging::add_file_log(logfile);  // from libboost_log_setup
        logging::core::get()->set_filter(
            logging::trivial::severity >= logging::trivial::info);
        BOOST_LOG_TRIVIAL(info) << "boost-log-contract-marker";
        logging::core::get()->flush();
    }
    std::ifstream input(logfile);
    std::string content((std::istreambuf_iterator<char>(input)),
                        std::istreambuf_iterator<char>());
    if (content.find("boost-log-contract-marker") == std::string::npos) {
        return 3;
    }

    // Boost.Filesystem: confirm the sink artifact exists and clean it up.
    {
        boost::filesystem::path sink_path(logfile);
        if (!boost::filesystem::exists(sink_path)) {
            return 4;
        }
        boost::filesystem::remove(sink_path);
    }
    return 0;
}
