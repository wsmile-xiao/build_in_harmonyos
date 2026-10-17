#include <iostream>

#include "tinyxml.h"

int main() {
    TiXmlDocument document;
    document.Parse("<?xml version=\"1.0\"?><root><item id=\"7\">value &amp; more</item></root>");
    if (document.Error()) {
        std::cerr << "parse failed: " << document.ErrorDesc() << '\n';
        return 1;
    }

    const TiXmlElement* root = document.FirstChildElement("root");
    const TiXmlElement* item = root ? root->FirstChildElement("item") : nullptr;
    int id = 0;
    if (!item || item->QueryIntAttribute("id", &id) != TIXML_SUCCESS || id != 7 ||
        !item->GetText() || std::string(item->GetText()) != "value & more") {
        std::cerr << "unexpected parsed document\n";
        return 2;
    }

    TiXmlPrinter printer;
    document.Accept(&printer);
    if (std::string(printer.CStr()).find("<item id=\"7\">") == std::string::npos) {
        std::cerr << "serialization failed\n";
        return 3;
    }

    std::cout << "tinyxml consumer PASS\n";
    return 0;
}
