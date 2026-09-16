#include <cstdio>
#include <string>
#include "tinyxml.h"
#include "kodi/util/XMLUtils.h"

static int failures = 0;

#define CHECK(cond, msg)                                    \
    do {                                                    \
        if (!(cond)) {                                      \
            printf("FAIL: %s\n", msg);                      \
            failures++;                                     \
        }                                                   \
    } while (0)

int main(void) {
    TiXmlDocument doc;

    // ---- Set* family: build a settings document ----
    TiXmlElement root("settings");
    doc.InsertEndChild(root);

    XMLUtils::SetInt(&root, "id", 42);
    XMLUtils::SetString(&root, "name", "kodiplatform");
    XMLUtils::SetBoolean(&root, "enabled", true);
    XMLUtils::SetFloat(&root, "ratio", 1.5f);
    XMLUtils::SetHex(&root, "color", 0xdeadbeef);
    XMLUtils::SetPath(&root, "path", "/tmp/kodi");

    // ---- Get* family: read the values back ----
    int iv = 0;
    CHECK(XMLUtils::GetInt(&root, "id", iv), "GetInt should succeed");
    CHECK(iv == 42, "GetInt round-trip value");

    std::string sv;
    CHECK(XMLUtils::GetString(&root, "name", sv), "GetString should succeed");
    CHECK(sv == "kodiplatform", "GetString round-trip value");

    bool bv = false;
    CHECK(XMLUtils::GetBoolean(&root, "enabled", bv), "GetBoolean should succeed");
    CHECK(bv, "GetBoolean round-trip value");

    float fv = 0.0f;
    CHECK(XMLUtils::GetFloat(&root, "ratio", fv), "GetFloat should succeed");
    CHECK(fv > 1.49f && fv < 1.51f, "GetFloat round-trip value");

    uint32_t hexv = 0;
    CHECK(XMLUtils::GetHex(&root, "color", hexv), "GetHex should succeed");
    CHECK(hexv == 0xdeadbeef, "GetHex round-trip value");

    std::string pv;
    CHECK(XMLUtils::GetPath(&root, "path", pv), "GetPath should succeed");
    CHECK(pv == "/tmp/kodi", "GetPath round-trip value");

    // ---- Range-checked getters ----
    int clamped = 0;
    CHECK(XMLUtils::GetInt(&root, "id", clamped, 0, 10), "GetInt(min,max) should succeed");
    CHECK(clamped == 10, "GetInt clamp-to-max");

    // ---- Structural helpers ----
    CHECK(XMLUtils::HasChild(&root, "id"), "HasChild should find existing tag");
    CHECK(!XMLUtils::HasChild(&root, "missing"), "HasChild should reject absent tag");

    std::string encoding;
    // Empty document has no declaration -> GetEncoding must fail gracefully
    TiXmlDocument emptyDoc;
    CHECK(!XMLUtils::GetEncoding(&emptyDoc, encoding), "GetEncoding on empty doc should fail");

    CHECK(XMLUtils::HasUTF8Declaration("<?xml version=\"1.0\" encoding=\"utf-8\"?><a/>"),
          "HasUTF8Declaration should detect utf-8 declaration");
    CHECK(!XMLUtils::HasUTF8Declaration("<?xml version=\"1.0\" encoding=\"iso-8859-1\"?><a/>"),
          "HasUTF8Declaration should reject non-utf8 declaration");

    // ---- Serialization keeps the DOM usable ----
    std::string name2;
    CHECK(XMLUtils::GetString(&root, "name", name2) && name2 == "kodiplatform",
          "DOM stays consistent after all operations");

    if (failures == 0) {
        printf("test kodi-platform 20250416: all %d checks OK\n", 18);
        return 0;
    }
    printf("test kodi-platform 20250416: %d failures\n", failures);
    return 1;
}
