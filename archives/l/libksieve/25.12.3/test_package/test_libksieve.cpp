/* SPDX-FileCopyrightText: 2026 NebulaAGI
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Consumer smoke test for the libksieve KSieve parser library.
 *
 * It compiles a real Sieve script with the KSieve::Parser and checks that a
 * valid script parses cleanly while a malformed one is rejected. This
 * exercises the actual library API (KSieve::Parser / KSieve::ScriptBuilder).
 */

#include <KSieve/parser.h>
#include <KSieve/scriptbuilder.h>
#include <KSieve/error.h>

#include <QString>

#include <cstdio>
#include <cstring>

namespace
{
class RecordingScriptBuilder : public KSieve::ScriptBuilder
{
public:
    int commands = 0;
    int tests = 0;
    int errors = 0;

    void taggedArgument(const QString & /*tag*/) override {}
    void stringArgument(const QString & /*string*/, bool /*multiLine*/,
                        const QString & /*embeddedHashComment*/) override {}
    void numberArgument(unsigned long /*number*/, char /*quantifier*/) override {}
    void stringListArgumentStart() override {}
    void stringListEntry(const QString & /*string*/, bool /*multiLine*/,
                         const QString & /*embeddedHashComment*/) override {}
    void stringListArgumentEnd() override {}
    void commandStart(const QString & /*identifier*/, int /*lineNumber*/) override
    {
        ++commands;
    }
    void commandEnd(int /*lineNumber*/) override {}
    void testStart(const QString & /*identifier*/) override { ++tests; }
    void testEnd() override {}
    void testListStart() override {}
    void testListEnd() override {}
    void blockStart(int /*lineNumber*/) override {}
    void blockEnd(int /*lineNumber*/) override {}
    void hashComment(const QString & /*comment*/) override {}
    void bracketComment(const QString & /*comment*/) override {}
    void lineFeed() override {}
    void error(const KSieve::Error & /*error*/) override { ++errors; }
    void finished() override {}
};

int fail(const char *message)
{
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}
}

int main(int argc, char **argv)
{
    Q_UNUSED(argc)
    Q_UNUSED(argv)

    const char validScript[] =
        "require [\"fileinto\", \"vacation\"];\n"
        "if header :contains \"subject\" \"vacation\" {\n"
        "    vacation \"On holidays\";\n"
        "}\n";

    RecordingScriptBuilder builder;
    KSieve::Parser parser(validScript, validScript + std::strlen(validScript));
    parser.setScriptBuilder(&builder);
    if (!parser.parse()) {
        const KSieve::Error &err = parser.error();
        std::fprintf(stderr, "FAIL: valid script did not parse: %s\n", err.asString().toUtf8().constData());
        return 1;
    }
    if (builder.errors != 0) {
        return fail("valid script reported parse errors");
    }
    if (builder.commands < 2) {
        return fail("parser did not drive the commands in the script");
    }

    const char invalidScript[] = "require ]this is not('";
    RecordingScriptBuilder badBuilder;
    KSieve::Parser badParser(invalidScript, invalidScript + std::strlen(invalidScript));
    badParser.setScriptBuilder(&badBuilder);
    if (badParser.parse()) {
        return fail("malformed script unexpectedly parsed");
    }

    std::puts("PASS: libksieve KSieve parser consumed and validated a Sieve script");
    return 0;
}
