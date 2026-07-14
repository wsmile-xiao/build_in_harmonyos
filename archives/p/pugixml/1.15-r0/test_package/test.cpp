#include <iostream>
#include "pugixml.hpp"

int main() {
    pugi::xml_document doc;
    pugi::xml_parse_result result = doc.load_string("<root><child>hello</child></root>");

    if (!result) {
        std::cerr << "XML parse error: " << result.description() << std::endl;
        return 1;
    }

    pugi::xml_node root = doc.child("root");
    pugi::xml_node child = root.child("child");

    if (!child) {
        std::cerr << "Failed to find child node" << std::endl;
        return 1;
    }

    std::string text = child.text().get();
    if (text != "hello") {
        std::cerr << "Unexpected text: " << text << std::endl;
        return 1;
    }

    std::cout << "pugixml " << PUGIXML_VERSION << ": OK" << std::endl;
    return 0;
}