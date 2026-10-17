#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include <boost/algorithm/string/replace.hpp>
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string/trim.hpp>
#include <boost/circular_buffer.hpp>
#include <boost/filesystem.hpp>
#include <boost/format.hpp>
#include <boost/math/special_functions/factorials.hpp>
#include <boost/program_options.hpp>
#include <boost/property_tree/ptree.hpp>
#include <boost/system/error_code.hpp>
#include <boost/tokenizer.hpp>

int main() {
    int failures = 0;

    namespace po = boost::program_options;
    po::options_description options("morpheus boost options");
    int steps = 0;
    options.add_options()("steps", po::value<int>(&steps));
    const char* arguments[] = {"morpheus-smoke", "--steps", "190"};
    po::variables_map values;
    po::store(po::parse_command_line(3, arguments, options), values);
    po::notify(values);
    failures += steps != 190;
    failures += boost::str(boost::format("steps=%1%") % steps) != "steps=190";

    namespace fs = boost::filesystem;
    const fs::path root = fs::current_path() / fs::unique_path("boost-morpheus-component-test-%%%%-%%%%");
    const fs::path file = root / "input.txt";
    boost::system::error_code create_ec;
    fs::create_directories(root, create_ec);
    failures += static_cast<bool>(create_ec);
    {
        std::ofstream output(file.string(), std::ios::binary);
        output << "boost-morpheus";
        failures += !output.good();
    }
    boost::system::error_code exists_ec;
    failures += !fs::exists(file, exists_ec) || exists_ec;
    boost::system::error_code size_ec;
    failures += fs::file_size(file, size_ec) != 14 || size_ec;
    boost::system::error_code remove_ec;
    fs::remove_all(root, remove_ec);
    failures += static_cast<bool>(remove_ec);

    std::string csv = " alpha, beta, gamma ";
    boost::algorithm::trim(csv);
    boost::algorithm::replace_all(csv, " ", "");
    std::vector<std::string> split_values;
    boost::algorithm::split(split_values, csv, boost::is_any_of(","));
    failures += split_values.size() != 3 || split_values[1] != "beta";

    boost::circular_buffer<int> window(2);
    window.push_back(1);
    window.push_back(2);
    window.push_back(3);
    failures += window.front() != 2 || window.back() != 3;

    failures += boost::math::factorial<double>(5) != 120.0;

    boost::property_tree::ptree tree;
    tree.put("steps", steps);
    failures += tree.get<int>("steps") != 190;

    boost::tokenizer<boost::escaped_list_separator<char>> tokens(csv);
    failures += std::distance(tokens.begin(), tokens.end()) != 3;

    return failures;
}
