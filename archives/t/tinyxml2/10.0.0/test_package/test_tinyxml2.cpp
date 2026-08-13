/* test_package/test_tinyxml2.cpp — tinyxml2 10.0.0 L1 smoke test.
 * Parse XML, modify, and re-serialize to verify the public API. */
#include <cstdio>
#include <cstring>
#include "tinyxml2.h"

int main(void) {
    const char *xml =
        "<root><name>tinyxml2</name><version>10.0.0</version></root>";

    tinyxml2::XMLDocument doc;
    if (doc.Parse(xml) != tinyxml2::XML_SUCCESS) {
        fprintf(stderr, "Parse failed\n");
        return 1;
    }

    tinyxml2::XMLElement *root = doc.RootElement();
    if (!root || strcmp(root->Name(), "root") != 0) {
        fprintf(stderr, "Root element mismatch\n");
        return 1;
    }

    tinyxml2::XMLElement *name = root->FirstChildElement("name");
    if (!name || !name->GetText()) {
        fprintf(stderr, "Missing name element\n");
        return 1;
    }

    if (strcmp(name->GetText(), "tinyxml2") != 0) {
        fprintf(stderr, "Name text mismatch: %s\n", name->GetText());
        return 1;
    }

    /* Modify: add a new element */
    tinyxml2::XMLElement *status = doc.NewElement("status");
    if (!status) {
        fprintf(stderr, "NewElement failed\n");
        return 1;
    }
    status->SetText("ok");
    root->InsertEndChild(status);

    /* Serialize back */
    tinyxml2::XMLPrinter printer;
    doc.Print(&printer);

    if (strstr(printer.CStr(), "status") == nullptr) {
        fprintf(stderr, "Serialize missing new element\n");
        return 1;
    }

    printf("tinyxml2 10.0.0: parse/modify/serialize roundtrip OK\n");
    return 0;
}
