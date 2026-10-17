/* Consumer test for the packaged libecoli API.
 *
 * Covers core grammar parsing + string-vector helpers without the optional
 * editline/yaml features (both disabled in this recipe):
 *  - node creation and description
 *  - shell-like lexing + sequence parsing ("hello <name>")
 *  - match / no-match paths, pnode lookup and value extraction
 *  - strvec helpers linked from the same library
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ecoli.h>

static int checks;
static int failures;

#define CHECK(condition, message)                                        \
    do {                                                                 \
        checks++;                                                        \
        if (condition) {                                                 \
            printf("ok %02d - %s\n", checks, message);                   \
        } else {                                                         \
            failures++;                                                  \
            printf("not ok %02d - %s\n", checks, message);               \
        }                                                                \
    } while (0)

int main(void)
{
    struct ec_node *word = NULL;
    struct ec_node *root = NULL;
    struct ec_pnode *p = NULL;
    struct ec_strvec *vec = NULL;
    const struct ec_pnode *found = NULL;
    const char *val = NULL;
    char *desc = NULL;

    ec_init();

    word = ec_node_str(EC_NO_ID, "hello");
    CHECK(word != NULL, "ec_node_str creates a node");
    if (word == NULL) {
        ec_exit();
        return 1;
    }

    desc = ec_node_desc(word);
    CHECK(desc != NULL && strcmp(desc, "hello") == 0,
          "node description is hello");
    free(desc);
    ec_node_free(word);

    vec = ec_strvec();
    CHECK(vec != NULL, "ec_strvec creates a vector");
    if (vec == NULL) {
        ec_exit();
        return 1;
    }
    CHECK(ec_strvec_add(vec, "ecoli") == 0 && ec_strvec_len(vec) == 1,
          "strvec add/len works");
    CHECK(ec_strvec_val(vec, 0) != NULL &&
          strcmp(ec_strvec_val(vec, 0), "ecoli") == 0,
          "strvec val returns ecoli");
    ec_strvec_free(vec);

    /* Grammar: "hello <name>", with shell lexing. */
    root = ec_node_sh_lex(
        EC_NO_ID,
        EC_NODE_SEQ(EC_NO_ID,
                    ec_node_str(EC_NO_ID, "hello"),
                    ec_node_any("NAME", NULL)));
    CHECK(root != NULL, "grammar nodes compose");
    if (root == NULL) {
        ec_exit();
        return 1;
    }

    p = ec_parse(root, "hello ecoli");
    CHECK(p != NULL && ec_pnode_matches(p), "parse matches hello ecoli");
    CHECK(p != NULL && ec_pnode_len(p) == 1, "parse length is 1");
    if (p != NULL && ec_pnode_matches(p)) {
        found = ec_pnode_find(p, "NAME");
        CHECK(found != NULL, "pnode NAME is found");
        if (found != NULL) {
            val = ec_strvec_val(ec_pnode_get_strvec(found), 0);
            CHECK(val != NULL && strcmp(val, "ecoli") == 0,
                  "NAME value is ecoli");
        } else {
            CHECK(0, "NAME value is ecoli");
        }
    } else {
        CHECK(0, "pnode NAME is found");
        CHECK(0, "NAME value is ecoli");
    }
    ec_pnode_free(p);
    p = NULL;

    p = ec_parse(root, "hello");
    CHECK(p != NULL && !ec_pnode_matches(p),
          "incomplete input does not match");
    ec_pnode_free(p);
    p = NULL;

    ec_node_free(root);
    ec_exit();

    if (failures == 0)
        printf("PASS: libecoli consumer test (%d checks)\n", checks);
    else
        printf("FAIL: libecoli consumer test (%d/%d checks passed)\n",
               checks - failures, checks);

    return failures == 0 ? 0 : 1;
}
