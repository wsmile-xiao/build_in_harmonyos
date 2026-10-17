// test_package/test.cpp — xalan 1.12 Conan L1 test.
//
// Exercises the real Xalan-C++ XSLT API end to end: initialize Xerces +
// Xalan, write a small XML document and XSL stylesheet to the working
// directory, run XalanTransformer::transform() to an output file, then
// read the output back and assert on its content (non-empty, contains
// both item texts and the greeting wrapper). This is a genuine API +
// file-transform smoke test of the XSLT engine, not a stub.
//
// Lifetime discipline: XalanTransformer::terminate() must run AFTER the
// transformer object is destroyed, and XMLPlatformUtils::Terminate()
// after that; both must also run when transform fails. A scoped block
// plus early-return-free flow guarantees the order.
#include <xalanc/XalanTransformer/XalanTransformer.hpp>
#include <xercesc/util/PlatformUtils.hpp>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

static int g_total = 0;
static int g_passed = 0;

static void check(bool ok, const char* what) {
    ++g_total;
    if (ok) {
        ++g_passed;
    } else {
        std::fprintf(stderr, "xalan: FAILED assertion — %s\n", what);
    }
}

static bool writeFile(const char* path, const char* content) {
    std::ofstream out(path, std::ios::binary);
    if (!out) {
        return false;
    }
    out << content;
    out.close();
    return static_cast<bool>(out);
}

static std::string readFile(const char* path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        return std::string();
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

int main() {
    static const char* kXml =
        "<?xml version=\"1.0\"?>"
        "<doc><name first=\"Hello\" last=\"World\"/>"
        "<name first=\"Foo\" last=\"Bar\"/></doc>";
    static const char* kXsl =
        "<?xml version=\"1.0\"?>"
        "<xsl:stylesheet version=\"1.0\" "
        "xmlns:xsl=\"http://www.w3.org/1999/XSL/Transform\">"
        "<xsl:output method=\"xml\" indent=\"yes\"/>"
        "<xsl:template match=\"/\">"
        "<greeting>"
        "<xsl:for-each select=\"doc/name\">"
        "<item><xsl:value-of select=\"@first\"/> "
        "<xsl:value-of select=\"@last\"/></item>"
        "</xsl:for-each>"
        "</greeting>"
        "</xsl:template>"
        "</xsl:stylesheet>";

    if (!writeFile("xalan_test_in.xml", kXml)) {
        std::fprintf(stderr, "xalan: cannot write input xml\n");
        return 1;
    }
    if (!writeFile("xalan_test.xsl", kXsl)) {
        std::fprintf(stderr, "xalan: cannot write stylesheet\n");
        return 1;
    }

    int transformResult = -1;
    std::string lastError;
    {
        try {
            xercesc::XMLPlatformUtils::Initialize();
        } catch (...) {
            std::fprintf(stderr, "xalan: XMLPlatformUtils::Initialize threw\n");
            return 1;
        }
        xalanc::XalanTransformer::initialize();
        {
            xalanc::XalanTransformer transformer;
            transformResult = transformer.transform(
                "xalan_test_in.xml", "xalan_test.xsl", "xalan_test_out.xml");
            if (transformResult != 0) {
                lastError = transformer.getLastError();
            }
        }
        xalanc::XalanTransformer::terminate();
        xercesc::XMLPlatformUtils::Terminate();
    }

    check(transformResult == 0, "transform returns 0");
    if (!lastError.empty()) {
        std::fprintf(stderr, "xalan: transform error: %s\n", lastError.c_str());
    }

    const std::string out = readFile("xalan_test_out.xml");
    check(!out.empty(), "output file is non-empty");
    check(out.find("Hello") != std::string::npos,
          "output contains first item text \"Hello\"");
    check(out.find("World") != std::string::npos,
          "output contains first item text \"World\"");
    check(out.find("Foo") != std::string::npos,
          "output contains second item text \"Foo\"");
    check(out.find("greeting") != std::string::npos,
          "output contains greeting wrapper element");

    if (g_passed == g_total) {
        std::printf("test xalan 1.12: OK (%d/%d assertions)\n", g_passed, g_total);
        return 0;
    }
    std::fprintf(stderr, "test xalan 1.12: FAILED (%d/%d assertions)\n",
                 g_passed, g_total);
    return 1;
}
