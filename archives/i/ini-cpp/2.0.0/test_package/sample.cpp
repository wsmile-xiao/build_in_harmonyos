// ini-cpp consumer smoke test (R34): real API usage of the packaged header.
// Writes a runtime-generated INI file, parses it with inih::INIReader and
// checks sections, keys and typed access.
#include <fstream>
#include <iostream>
#include <set>
#include <string>

#include "ini/ini.h"

using namespace inih;

int main() {
    const std::string path = "smoke_config.ini";
    {
        std::ofstream out{path};
        out << "[section1]\nany=1\nname=hello\n[section2]\nflag=0.5\n";
    }
    INIReader r{path};
    const std::set<std::string> secs = r.Sections();
    if (secs != std::set<std::string>({"section1", "section2"})) {
        std::cout << "FAIL: sections" << std::endl;
        return 1;
    }
    const std::set<std::string> keys = r.Keys("section1");
    if (keys != std::set<std::string>({"any", "name"})) {
        std::cout << "FAIL: keys" << std::endl;
        return 1;
    }
    if (r.Get<std::string>("section1", "any") != "1") {
        std::cout << "FAIL: Get<string>" << std::endl;
        return 1;
    }
    if (r.Get<int>("section1", "any") != 1) {
        std::cout << "FAIL: Get<int>" << std::endl;
        return 1;
    }
    if (r.Get<double>("section2", "flag") != 0.5) {
        std::cout << "FAIL: Get<double>" << std::endl;
        return 1;
    }
    std::cout << "OK: ini-cpp header + inih::INIReader real API works" << std::endl;
    return 0;
}
