#include <iostream>
#include "pugixml.hpp"

int main() {
    pugi::xml_document doc;
    const pugi::xml_parse_result parsed =
        doc.load_string("<root><child id='1'>hello</child></root>");
    if (!parsed) {
        std::cerr << parsed.description() << std::endl;
        return 1;
    }

    const pugi::xml_node child = doc.select_node("/root/child").node();
    if (!child || std::string(child.text().get()) != "hello") {
        std::cerr << "unexpected XML child" << std::endl;
        return 2;
    }
    if (std::string(child.attribute("id").value()) != "1") {
        std::cerr << "unexpected XML attribute" << std::endl;
        return 3;
    }

    std::cout << "pugixml " << PUGIXML_VERSION << ": OK" << std::endl;
    return 0;
}
