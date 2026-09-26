/* jimtcl 0.83 test_package — consumer view: embed the packaged libjim.
 *
 * Links jimtcl::jimtcl (libjim.a + conan zlib) exactly like a downstream
 * project would, creates an interpreter and evaluates real scripts.
 * Every assertion counts towards the "鸿蒙特有测试" row of the PR body.
 */
#include <stdio.h>
#include <string.h>

#include <jim.h>

static int checks = 0;
static int failed = 0;

static void expect(Jim_Interp *interp, const char *script, const char *want,
                   const char *desc)
{
    const char *got;

    checks++;
    if (Jim_Eval(interp, script) != JIM_OK) {
        failed++;
        Jim_MakeErrorMessage(interp);
        printf("FAIL[%d] %s: eval error: %s\n", checks, desc,
               Jim_GetString(Jim_GetResult(interp), NULL));
        return;
    }
    got = Jim_GetString(Jim_GetResult(interp), NULL);
    if (strcmp(got, want) != 0) {
        failed++;
        printf("FAIL[%d] %s: got \"%s\" want \"%s\"\n", checks, desc, got, want);
        return;
    }
    printf("PASS[%d] %s\n", checks, desc);
}

int main(void)
{
    Jim_Interp *interp = Jim_CreateInterp();

    if (interp == NULL) {
        fprintf(stderr, "cannot create Jim interpreter\n");
        return 1;
    }
    Jim_RegisterCoreCommands(interp);
    Jim_InitStaticExtensions(interp);

    expect(interp, "info patchlevel", "0.83", "packaged version is 0.83");
    expect(interp, "expr {6*7}", "42", "expr arithmetic");
    expect(interp, "llength {a b c}", "3", "list operations");
    expect(interp, "dict size {a 1 b 2}", "2", "dict operations");
    expect(interp, "string length HarmonyOS", "9", "string operations");
    expect(interp, "regexp {^ohos$} ohos", "1", "regexp extension");
    expect(interp, "zlib inflate [zlib deflate {hello jimtcl}]",
           "hello jimtcl", "zlib extension roundtrip (conan zlib linked)");

    Jim_FreeInterp(interp);
    printf("test_jimtcl: %d/%d assertions passed\n", checks - failed, checks);
    return failed ? 1 : 0;
}
