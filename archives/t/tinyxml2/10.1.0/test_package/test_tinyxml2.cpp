#include <tinyxml2.h>

#include <cstdio>
#include <cstring>
#include <string>

namespace {

int failures = 0;

#define CHECK(condition, message)                                            \
    do {                                                                     \
        if (condition) {                                                     \
            std::printf("[ok] %s\n", message);                              \
        } else {                                                             \
            std::fprintf(stderr, "[FAIL] %s (%s:%d)\n", message, __FILE__,  \
                         __LINE__);                                          \
            ++failures;                                                      \
        }                                                                    \
    } while (false)

const char* kXml =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    "<robot name=\"harmony-pc\" dof=\"7\">"
    "<link name=\"base\" mass=\"1.25\"/>"
    "<link name=\"tip\" mass=\"0.5\"/>"
    "<note>a &amp; b &lt; c</note>"
    "<blob><![CDATA[raw <not> parsed]]></blob>"
    "</robot>";

}  // namespace

int main() {
    using namespace tinyxml2;

    XMLDocument document;
    CHECK(document.Parse(kXml) == XML_SUCCESS, "parse valid UTF-8 XML");

    XMLElement* root = document.RootElement();
    CHECK(root != nullptr && std::strcmp(root->Name(), "robot") == 0,
          "read root element");
    CHECK(root != nullptr && root->Attribute("name") != nullptr &&
              std::strcmp(root->Attribute("name"), "harmony-pc") == 0,
          "read string attribute");

    int dof = -1;
    CHECK(root != nullptr &&
              root->QueryIntAttribute("dof", &dof) == XML_SUCCESS && dof == 7,
          "read typed integer attribute");

    int link_count = 0;
    double mass_sum = 0.0;
    if (root != nullptr) {
        for (XMLElement* link = root->FirstChildElement("link"); link != nullptr;
             link = link->NextSiblingElement("link")) {
            ++link_count;
            double mass = 0.0;
            if (link->QueryDoubleAttribute("mass", &mass) == XML_SUCCESS) {
                mass_sum += mass;
            }
        }
    }
    CHECK(link_count == 2, "iterate sibling elements");
    CHECK(mass_sum > 1.7499 && mass_sum < 1.7501,
          "read typed floating-point attributes");

    XMLElement* note = root == nullptr ? nullptr : root->FirstChildElement("note");
    CHECK(note != nullptr && note->GetText() != nullptr &&
              std::string(note->GetText()) == "a & b < c",
          "decode XML entities");
    XMLElement* blob = root == nullptr ? nullptr : root->FirstChildElement("blob");
    CHECK(blob != nullptr && blob->GetText() != nullptr &&
              std::string(blob->GetText()) == "raw <not> parsed",
          "preserve CDATA text");

    XMLDocument output;
    XMLElement* config = output.NewElement("config");
    config->SetAttribute("revision", 42);
    config->SetAttribute("token", "x&y");
    XMLElement* child = output.NewElement("child");
    child->SetText("hello <HarmonyOS>");
    config->InsertEndChild(child);
    output.InsertFirstChild(config);

    XMLPrinter printer;
    output.Print(&printer);
    const std::string serialized = printer.CStr();
    CHECK(serialized.find("&amp;") != std::string::npos,
          "escape entities during serialization");

    XMLDocument round_trip;
    CHECK(round_trip.Parse(serialized.c_str()) == XML_SUCCESS,
          "parse serialized output");
    XMLElement* round_root = round_trip.RootElement();
    int revision = 0;
    CHECK(round_root != nullptr &&
              round_root->QueryIntAttribute("revision", &revision) == XML_SUCCESS &&
              revision == 42,
          "preserve integer attribute through round-trip");
    CHECK(round_root != nullptr && round_root->Attribute("token") != nullptr &&
              std::string(round_root->Attribute("token")) == "x&y",
          "preserve escaped string attribute through round-trip");
    XMLElement* round_child =
        round_root == nullptr ? nullptr : round_root->FirstChildElement("child");
    CHECK(round_child != nullptr && round_child->GetText() != nullptr &&
              std::string(round_child->GetText()) == "hello <HarmonyOS>",
          "preserve escaped text through round-trip");

    XMLDocument malformed;
    CHECK(malformed.Parse("<a><b></a>") != XML_SUCCESS,
          "reject malformed XML");
    CHECK(malformed.ErrorStr() != nullptr &&
              std::strlen(malformed.ErrorStr()) > 0,
          "report malformed XML error text");

    if (failures != 0) {
        std::fprintf(stderr, "tinyxml2 10.1.0: %d assertion(s) failed\n", failures);
        return 1;
    }
    std::printf("tinyxml2 10.1.0: all 15 consumer assertions passed\n");
    return 0;
}
