// Consumer test for clue 1.0.0 — exercises the packaged header through its
// real string-logging API (same mode the upstream lest suite uses).
//
// Each CHECK is an independent, individually-falsifiable assertion; the
// harness itself uses clue::is_true() so every line depends on the header.
// Exit code: 0 all checks passed, 1 at least one failed.

#define clue_LOG_TO_STRING
#include "clue.hpp"

#include <iostream>
#include <string>

// The short-name LOG_* macros expand to an unqualified the_log() reference
// (upstream's own lest tests compile with `using namespace clue;` as well),
// so pull clue's names into scope.
using namespace clue;

static int g_checks = 0;
static int g_failed = 0;

#define CHECK( cond ) \
    do { ++g_checks; if (!(cond)) { ++g_failed; \
        std::cout << "FAIL line " << __LINE__ << ": " << #cond << std::endl; \
    } } while (clue::is_true(false))

int main()
{
    // 1-2: version macros exposed by the packaged header
    CHECK( 1 == clue_MAJOR && 0 == clue_MINOR && 0 == clue_PATCH );
    CHECK( std::string(clue_VERSION) == "1.0.0" );

    // 3-4: severity text table
    CHECK( std::string("Warning") == clue::to_severity_text( clue_LOG_SEV_WARNING ) );
    CHECK( std::string("Info")    == clue::to_severity_text( clue_LOG_SEV_INFO    ) );

    // 5: module text helper prepends a colon
    CHECK( std::string(": Gearbox") == clue::to_module_text( "Gearbox" ) );

    // 6-7: text_or() picks fallback for empty text only
    CHECK( std::string("x") == clue::text_or( "x", "y" ) );
    CHECK( std::string("y") == clue::text_or( "",  "y" ) );

    // 8: severities accumulation list
    CHECK( std::string("Emergency, Alert.") == clue::to_severities_text( clue_LOG_SEV_ALERT ) );

    // 9: default string logger starts empty
    clue::the_log().clear();
    CHECK( clue::the_log().severity() == clue_LOG_SEV_NONE );

    // 10-11: LOG_INFO records both severity and streamed text
    // (short-name macros are plain macros — never call them as clue::LOG_INFO)
    LOG_INFO( "hello " << 42 );
    CHECK( clue::the_log().severity() == clue_LOG_SEV_INFO );
    CHECK( clue::the_log().text() == std::string("hello 42") );

    // 12: clear() resets the logger
    clue::the_log().clear();
    CHECK( clue::the_log().severity() == clue_LOG_SEV_NONE && clue::the_log().text().empty() );

    // 13-14: a second, different severity is recorded correctly
    LOG_ERROR( "v=" << 7 );
    CHECK( clue::the_log().severity() == clue_LOG_SEV_ERROR );
    CHECK( clue::the_log().text() == std::string("v=7") );

    std::cout << "clue consumer checks: " << (g_checks - g_failed)
              << "/" << g_checks << " passed" << std::endl;
    return g_failed == 0 ? 0 : 1;
}
