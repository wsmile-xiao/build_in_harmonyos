// Consumer test for the installed sheenbidi package.
//
// Based on the upstream/Debian smoke test: a mixed Arabic/Latin string whose
// resolved level runs and mirrored parentheses are known, plus pure LTR and
// pure RTL strings.
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <SheenBidi/SheenBidi.h>

static int checks;
static int failures;

static void check(int ok, const char *what)
{
    checks++;
    if (ok) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

static void mixed_case(void)
{
    const char *text = "یہ ایک )car( ہے۔";
    SBCodepointSequence sequence = {SBStringEncodingUTF8, (void *)text, strlen(text)};

    SBAlgorithmRef algorithm = SBAlgorithmCreate(&sequence);
    check(algorithm != NULL, "SBAlgorithmCreate returns an algorithm");
    if (algorithm == NULL) {
        return;
    }

    SBParagraphRef paragraph =
        SBAlgorithmCreateParagraph(algorithm, 0, INT32_MAX, SBLevelDefaultLTR);
    check(paragraph != NULL, "SBAlgorithmCreateParagraph returns a paragraph");
    if (paragraph == NULL) {
        SBAlgorithmRelease(algorithm);
        return;
    }

    check(SBParagraphGetLength(paragraph) == (SBUInteger)strlen(text),
          "paragraph length equals the UTF-8 byte length");

    SBLineRef line = SBParagraphCreateLine(paragraph, 0, SBParagraphGetLength(paragraph));
    SBUInteger runCount = SBLineGetRunCount(line);
    const SBRun *runs = SBLineGetRunsPtr(line);
    check(runCount == 3, "mixed text yields 3 level runs");
    if (runCount == 3) {
        check(runs[0].offset == 16 && runs[0].length == 8 && runs[0].level == 1,
              "run 0 = offset 16, length 8, level 1");
        check(runs[1].offset == 13 && runs[1].length == 3 && runs[1].level == 2,
              "run 1 = offset 13, length 3, level 2");
        check(runs[2].offset == 0 && runs[2].length == 13 && runs[2].level == 1,
              "run 2 = offset 0, length 13, level 1");
    }

    SBMirrorLocatorRef locator = SBMirrorLocatorCreate();
    SBMirrorLocatorLoadLine(locator, line, (void *)text);
    const SBMirrorAgent *agent = SBMirrorLocatorGetAgent(locator);
    int mirrors = 0;
    int found16 = 0;
    int found12 = 0;
    while (SBMirrorLocatorMoveNext(locator)) {
        mirrors++;
        if (agent->index == 16 && agent->codepoint == 40 && agent->mirror == 41) {
            found16 = 1;
        }
        if (agent->index == 12 && agent->codepoint == 41 && agent->mirror == 40) {
            found12 = 1;
        }
    }
    check(mirrors == 2, "mirror locator finds 2 mirrored parentheses");
    check(found16, "mirror at index 16 maps '(' (40) to ')' (41)");
    check(found12, "mirror at index 12 maps ')' (41) to '(' (40)");

    SBMirrorLocatorRelease(locator);
    SBLineRelease(line);
    SBParagraphRelease(paragraph);
    SBAlgorithmRelease(algorithm);
}

static void simple_case(const char *text, SBLevel expectedLevel, const char *what)
{
    SBCodepointSequence sequence = {SBStringEncodingUTF8, (void *)text, strlen(text)};
    SBAlgorithmRef algorithm = SBAlgorithmCreate(&sequence);
    SBParagraphRef paragraph =
        SBAlgorithmCreateParagraph(algorithm, 0, INT32_MAX, SBLevelDefaultLTR);
    SBLineRef line = SBParagraphCreateLine(paragraph, 0, SBParagraphGetLength(paragraph));
    SBUInteger runCount = SBLineGetRunCount(line);
    const SBRun *runs = SBLineGetRunsPtr(line);
    check(runCount == 1 && runs[0].level == expectedLevel, what);
    SBLineRelease(line);
    SBParagraphRelease(paragraph);
    SBAlgorithmRelease(algorithm);
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);

    mixed_case();
    simple_case("hello", 0, "pure LTR text yields a single level-0 run");
    simple_case("\xd7\xa9\xd7\x9c\xd7\x95\xd7\x9d", 1,
                "pure Hebrew text yields a single level-1 run");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures ? 1 : 0;
}
