#define SPIRIT_PO_NO_EXCEPTIONS
#define SPIRIT_PO_DEBUG

#include <spirit_po/spirit_po.hpp>

#include <string>

int main() {
    const std::string po =
        "msgid \"\"\n"
        "msgstr \"\"\n"
        "\"Language: zh_CN\\n\"\n"
        "\"Plural-Forms: nplurals=2; plural=(n != 1);\\n\"\n"
        "\"Content-Type: text/plain; charset=UTF-8\\n\"\n"
        "\n"
        "msgctxt \"menu\"\n"
        "msgid \"File\"\n"
        "msgstr \"文件\"\n"
        "\n"
        "msgid \"apple\"\n"
        "msgid_plural \"apples\"\n"
        "msgstr[0] \"苹果\"\n"
        "msgstr[1] \"苹果们\"\n";

    const auto catalog = spirit_po::catalog<>::from_range(po);
    if (!catalog) {
        return 1;
    }
    if (catalog.size() != 2) {
        return 2;
    }
    if (std::string(catalog.gettext("File")) != "File") {
        return 3;
    }
    if (std::string(catalog.pgettext("menu", "File")) != "文件") {
        return 4;
    }
    if (std::string(catalog.ngettext("apple", "apples", 1)) != "苹果") {
        return 5;
    }
    if (std::string(catalog.ngettext("apple", "apples", 2)) != "苹果们") {
        return 6;
    }
    if (std::string(catalog.gettext("missing")) != "missing") {
        return 7;
    }
    return 0;
}
