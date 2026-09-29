// test_libkode.cpp — consumer test for the packaged libkode API.
// Exercises all three static libraries shipped by the package:
//   kode       (class.h/code.h/file.h  — KODE:: namespace, C++ code generation)
//   xmlschema  (element.h/xmlelement.h — XSD:: namespace, schema model)
//   xmlcommon  (qname.h                — QName, XML/SOAP helpers)
// Performs a fixed set of 8 checks (count is audited below and drives
// HMBS_TEST_PACKAGE_RESULT discovered=8).

#include "class.h"
#include "code.h"
#include "file.h"

#include "element.h"
#include "xmlelement.h"

#include "qname.h"

#include <QString>
#include <cstdio>

using namespace KODE;
using namespace XSD;

static int g_ok = 0;
static int g_fail = 0;

static void check(bool cond, const char *label)
{
    if (cond) {
        ++g_ok;
        std::printf("OK: %s\n", label);
    } else {
        ++g_fail;
        std::printf("FAIL: %s\n", label);
    }
}

int main()
{
    // ---- kode library (code_generation) ----
    Class c("MyClass", "MyNS");
    check(c.name() == QString("MyClass"), "KODE::Class name");
    check(c.nameSpace() == QString("MyNS"), "KODE::Class namespace");

    Code body;
    body.addLine("int x = 1;");
    check(!body.isEmpty() && body.text().contains("int x = 1;"),
          "KODE::Code addLine/text");

    File file;
    file.setFilename("sample");
    file.setNameSpace("MyNS");
    file.insertClass(c);
    check(file.hasClass("MyClass"), "KODE::File insertClass/hasClass");
    check(file.nameSpace() == QString("MyNS"), "KODE::File namespace");

    // ---- xmlschema library (schema) ----
    Element e("ns1");
    e.setName("elem");
    e.setMinOccurs(3);
    check(e.name() == QString("elem") && e.minOccurs() == 3,
          "XSD::Element name/minOccurs");

    XmlElement xe("ns1");
    xe.setName("node");
    check(xe.name() == QString("node"), "XSD::XmlElement name");

    // ---- xmlcommon library (common) ----
    QName qn("ns", "local");
    check(qn.nameSpace() == QString("ns") && qn.localName() == QString("local"),
          "QName namespace/local");

    std::printf("RESULT: %d ok, %d fail\n", g_ok, g_fail);
    return g_fail == 0 ? 0 : 1;
}
