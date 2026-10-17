// test_package/test.cpp — xerces 3.3.0 Conan L1 test.
//
// Exercises the real Xerces-C++ DOM parsing API end to end: initialize the
// platform, feed an in-memory XML document through XercesDOMParser via a
// MemBufInputSource, then walk the resulting DOM tree and assert on its
// structure (root tag, element count, text content). This is a genuine API
// smoke test of the parsing/transcoding core, not a string-printing stub.
//
// Each assertion prints exactly one deterministic result line:
//   "CHECK PASS: <what>"  or  "CHECK FAIL: <what>"
// test_package/conanfile.py counts those lines as the single evidence source
// for HMBS_TEST_PACKAGE_RESULT (6 assertions total).
//
// Xerces-C++ lifetime discipline (two requirements):
//  1. XMLPlatformUtils::Terminate() must run AFTER every Xerces object is
//     destroyed — destroying a parser/DOM tree after Terminate() touches freed
//     platform state and segfaults on HarmonyOS (musl/libc++) during exit.
//  2. Terminate() must also run if parse()/transcode() throws — otherwise the
//     platform is left initialized.
// Both hold via an RAII guard (PlatformTerminator below) declared *before* any
// other Xerces object in a scope: it is destroyed last, so every Xerces object
// is gone before Terminate(), and its destructor runs even during unwinding.
#include <xercesc/util/PlatformUtils.hpp>
#include <xercesc/util/XMLString.hpp>
#include <xercesc/parsers/XercesDOMParser.hpp>
#include <xercesc/framework/MemBufInputSource.hpp>
#include <xercesc/dom/DOM.hpp>

#include <cstdio>
#include <cstring>
#include <string>

using namespace xercesc;

static int g_total = 0;
static int g_passed = 0;

static void check(bool ok, const char* what) {
    ++g_total;
    if (ok) {
        ++g_passed;
        std::printf("CHECK PASS: %s\n", what);
    } else {
        std::fprintf(stderr, "CHECK FAIL: %s\n", what);
    }
}

// RAII guard: calls XMLPlatformUtils::Terminate() on destruction. Declare it
// before any other Xerces object in a scope so it destructs last — after those
// objects — guaranteeing Terminate() runs once they are gone, including when an
// exception propagates out of the scope. Destroyed as a no-op only if
// Initialize() failed (the guard is never constructed on that early-return
// path).
struct PlatformTerminator {
    ~PlatformTerminator() { XMLPlatformUtils::Terminate(); }
};

int main() {
    try {
        XMLPlatformUtils::Initialize();
    } catch (const XMLException&) {
        std::fprintf(stderr, "CHECK FAIL: XMLPlatformUtils::Initialize threw\n");
        return 1;
    }

    {
        PlatformTerminator term;  // RAII: destructs last -> Terminate() always runs

        // Compact, well-formed XML with two child elements carrying text + attrs.
        static const char* kXml =
            "<root>"
            "<child id=\"1\">hello</child>"
            "<child id=\"2\">world</child>"
            "</root>";

        XercesDOMParser parser;
        parser.setValidationScheme(XercesDOMParser::Val_Never);
        parser.setDoNamespaces(true);

        MemBufInputSource src(
            reinterpret_cast<const XMLByte*>(kXml),
            static_cast<XMLSize_t>(std::strlen(kXml)),
            "membuf",
            false);

        parser.parse(src);
        check(parser.getErrorCount() == 0, "parse produces no errors");

        DOMDocument* doc = parser.getDocument();
        check(doc != nullptr, "parser returns a DOMDocument");

        DOMElement* root = doc ? doc->getDocumentElement() : nullptr;
        check(root != nullptr, "document has a root element");

        bool rootNameOk = false;
        if (root) {
            char* rootName = XMLString::transcode(root->getTagName());
            rootNameOk = rootName && std::strcmp(rootName, "root") == 0;
            XMLString::release(&rootName);
        }
        check(rootNameOk, "root tag is \"root\"");

        // Count element children and capture the first child's text content.
        XMLSize_t elemCount = 0;
        std::string firstText;
        if (root) {
            DOMNodeList* children = root->getChildNodes();
            if (children) {
                for (XMLSize_t i = 0; i < children->getLength(); ++i) {
                    DOMNode* n = children->item(i);
                    if (n->getNodeType() == DOMNode::ELEMENT_NODE) {
                        ++elemCount;
                        if (elemCount == 1) {
                            char* txt = XMLString::transcode(n->getTextContent());
                            if (txt) firstText = txt;
                            XMLString::release(&txt);
                        }
                    }
                }
            }
        }
        check(elemCount == 2, "root has exactly 2 child elements");
        check(firstText == "hello", "first child text content is \"hello\"");
    }  // parser/src destroyed, then `term` -> Terminate()

    if (g_passed == g_total && g_total == 6) {
        std::printf("test xerces 3.3.0: OK (%d/%d assertions)\n", g_passed, g_total);
        return 0;
    }
    std::fprintf(stderr, "test xerces 3.3.0: FAILED (%d/%d assertions)\n", g_passed, g_total);
    return 1;
}
