#include <algorithm>
#include <cstdio>
#include <iterator>
#include <string>

#include <boost/iostreams/device/array.hpp>
#include <boost/iostreams/device/mapped_file.hpp>
#include <boost/iostreams/filtering_stream.hpp>

int main() {
    const std::string path = "boost-redex-mapped-file.bin";
    const std::string payload = "Boost.Iostreams Redex payload 1.91.0";
    int failures = 0;

    boost::iostreams::mapped_file_params params;
    params.path = path;
    params.flags = boost::iostreams::mapped_file::mapmode::readwrite;
    params.new_file_size = payload.size();

    boost::iostreams::mapped_file mapped;
    mapped.open(params);
    failures += !mapped.is_open();
    if (!mapped.is_open()) {
        std::remove(path.c_str());
        return failures;
    }
    std::copy(payload.begin(), payload.end(), mapped.data());
    mapped.close();

    boost::iostreams::mapped_file_source source(path);
    failures += !source.is_open();
    if (source.is_open()) {
        boost::iostreams::array_source mapped_bytes(
            source.data(), static_cast<std::streamsize>(source.size()));
        boost::iostreams::filtering_istream input;
        input.push(mapped_bytes);
        const std::string restored{
            std::istreambuf_iterator<char>(input),
            std::istreambuf_iterator<char>()};
        failures += restored.size() != payload.size();
        failures += restored != payload;
        input.reset();
        source.close();
    }

    failures += std::remove(path.c_str()) != 0;
    return failures;
}
