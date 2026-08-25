#include <stdio.h>
#include <yara.h>

int main(void) {
    // Initialize YARA library
    yr_initialize();

    // Compile an empty rules set to verify the API works
    YR_RULES* rules = NULL;
    YR_COMPILER* compiler = NULL;
    int result = yr_compiler_create(&compiler);
    if (result != ERROR_SUCCESS) {
        fprintf(stderr, "Failed to create YARA compiler: %d\n", result);
        yr_finalize();
        return 1;
    }

    // Add a simple rule
    const char* rule_text =
        "rule test_rule { condition: true }";
    result = yr_compiler_add_string(compiler, rule_text, NULL);
    if (result != 0) {
        fprintf(stderr, "Failed to add rule string\n");
        yr_compiler_destroy(compiler);
        yr_finalize();
        return 1;
    }

    // Get compiled rules
    result = yr_compiler_get_rules(compiler, &rules);
    if (result != ERROR_SUCCESS) {
        fprintf(stderr, "Failed to get compiled rules: %d\n", result);
        yr_compiler_destroy(compiler);
        yr_finalize();
        return 1;
    }

    printf("YARA version: %s\n", YR_VERSION);
    printf("Rules compiled successfully\n");

    yr_rules_destroy(rules);
    yr_compiler_destroy(compiler);
    yr_finalize();

    return 0;
}
