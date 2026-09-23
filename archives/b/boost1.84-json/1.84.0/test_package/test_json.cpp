#include <boost/json.hpp>

#include <iostream>

int main() {
    namespace json = boost::json;
    json::value value = json::parse(R"({"name":"OpenHarmony","count":2,"ok":true})");
    if (!value.is_object()) return 1;
    auto& object = value.as_object();
    if (object.at("name").as_string() != "OpenHarmony") return 1;
    if (object.at("count").as_int64() != 2) return 1;
    if (!object.at("ok").as_bool()) return 1;
    object.at("count") = 3;
    auto const encoded = json::serialize(value);
    if (encoded.find("\"count\":3") == std::string::npos) return 1;
    std::cout << "boost json consumer test passed" << std::endl;
    return 0;
}
