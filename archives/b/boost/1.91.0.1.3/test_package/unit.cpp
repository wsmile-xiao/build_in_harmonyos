#include <string>

#include <boost/filesystem/path.hpp>
#include <boost/program_options.hpp>
#include <boost/regex.hpp>

int main() {
    int failures = 0;

    const boost::regex expression("boost-[0-9]+");
    failures += !boost::regex_match(std::string("boost-190"), expression);

    const boost::filesystem::path path("alpha/../boost.txt");
    failures += path.lexically_normal().filename() != "boost.txt";

    namespace po = boost::program_options;
    po::options_description options("options");
    int value = 0;
    options.add_options()("value", po::value<int>(&value));
    const char* arguments[] = {"boost-test", "--value", "191"};
    po::variables_map values;
    po::store(po::parse_command_line(3, arguments, options), values);
    po::notify(values);
    failures += value != 191;

    return failures;
}
