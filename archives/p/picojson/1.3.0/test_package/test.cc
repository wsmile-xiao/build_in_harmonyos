#include <picojson.h>
#include <iostream>
#include <string>

int main() {
    // Real consumer of the picojson API: parse, inspect, serialize (R34)
    picojson::value v;
    const std::string json = "{\"name\":\"picojson\",\"year\":2026,\"tags\":[\"json\",\"header-only\",\"c++11\"],\"ok\":true}";
    std::string err = picojson::parse(v, json);
    if (!err.empty()) {
        std::cerr << "parse error: " << err << std::endl;
        return 1;
    }
    picojson::object& o = v.get<picojson::object>();
    if (o["name"].get<std::string>() != "picojson")
        return 2;
    if (o["year"].get<double>() != 2026.0)
        return 3;
    picojson::array& tags = o["tags"].get<picojson::array>();
    if (tags.size() != 3 || tags[0].get<std::string>() != "json")
        return 4;
    if (!o["ok"].get<bool>())
        return 5;
    std::string out = v.serialize();
    if (out.find("\"name\":\"picojson\"") == std::string::npos)
        return 6;
    std::cout << "picojson consumer OK: " << out << std::endl;
    return 0;
}
