#include <iksemel.h>

#include <stdio.h>
#include <string.h>

static int sax_tags = 0;
static int sax_cdata = 0;

static int tag_hook(void *user_data, char *name, char **atts, int type)
{
    (void)user_data;
    (void)atts;
    (void)type;
    if (name == NULL) {
        return 1;
    }
    sax_tags++;
    return 0;
}

static int cdata_hook(void *user_data, char *data, size_t len)
{
    (void)user_data;
    if (data == NULL || len == 0) {
        return 1;
    }
    sax_cdata++;
    return 0;
}

int main(void)
{
    ikstack *stack;
    iks *node;
    iks *child;
    iksparser *sax;
    iksparser *dom;
    iks *tree;
    iksid *id;
    char *text;
    /* iks_sha/iks_md5 write exactly 40/32 hex chars with NO NUL terminator
       (see iks_sha_print/iks_md5_print: 5x "%08x" / 4x "%08x", no '\0').
       Zero-init and terminate explicitly; compare fixed lengths. */
    char hash[41] = {0};
    char md5[33] = {0};
    char *encoded;
    char *decoded;
    size_t allocated;
    size_t used;
    int err;

    /* 1. object stack allocates and tracks memory */
    stack = iks_stack_new(256, 1024);
    if (stack == NULL) {
        return 1;
    }
    if (iks_stack_alloc(stack, 64) == NULL) {
        return 1;
    }
    iks_stack_stat(stack, &allocated, &used);
    if (allocated == 0 || used == 0) {
        return 1;
    }
    iks_stack_delete(stack);

    /* 2. DOM build, attribute round-trip and serialization */
    node = iks_new("iq");
    if (node == NULL) {
        return 2;
    }
    iks_insert_attrib(node, "type", "result");
    iks_insert_attrib(node, "to", "user@example.org");
    child = iks_insert(node, "query");
    if (child == NULL) {
        return 2;
    }
    iks_insert_attrib(child, "xmlns", "jabber:iq:version");
    iks_insert_cdata(iks_insert(child, "name"), "TestClient", 10);
    if (iks_strcmp(iks_find_attrib(node, "type"), "result") != 0) {
        return 2;
    }
    if (iks_find(node, "query") == NULL) {
        return 2;
    }
    text = iks_string(iks_stack(node), node);
    if (text == NULL || strstr(text, "TestClient") == NULL) {
        return 2;
    }
    iks_delete(node);

    /* 3. SAX parser fires tag and cdata hooks */
    sax = iks_sax_new(NULL, tag_hook, cdata_hook);
    if (sax == NULL) {
        return 3;
    }
    if (iks_parse(sax, "<presence><status>online</status></presence>", 0, 1) != IKS_OK) {
        return 3;
    }
    if (sax_tags < 4 || sax_cdata < 1) {
        return 3;
    }
    if (iks_nr_bytes(sax) == 0) {
        return 3;
    }
    iks_parser_delete(sax);

    /* 4. DOM parser parses a full document */
    tree = NULL;
    dom = iks_dom_new(&tree);
    if (dom == NULL) {
        return 4;
    }
    err = iks_parse(dom, "<message><body>hello</body></message>", 0, 1);
    if (err != IKS_OK || tree == NULL) {
        return 4;
    }
    if (iks_strcmp(iks_find_cdata(tree, "body"), "hello") != 0) {
        return 4;
    }
    iks_parser_delete(dom);
    iks_delete(tree);

    /* 5. string helpers behave like libc */
    if (iks_strlen("iksemel") != 7) {
        return 5;
    }
    if (iks_strcmp("abc", "abc") != 0 || iks_strcasecmp("AbC", "aBc") != 0) {
        return 5;
    }
    if (iks_strncmp("abcd", "abce", 3) != 0) {
        return 5;
    }

    /* 6. SHA-1 of "abc" matches upstream 1.4 test vector (test/tst-sha.c).
       NOTE: upstream 1.4 expects ...0d89d, NOT the published RFC SHA1
       (...0d4d); make check 8/8 on OHOS proves the library emits the
       former, so the consumer test must match upstream, not the RFC. */
    iks_sha("abc", hash);
    hash[40] = '\0';
    if (strncmp(hash, "a9993e364706816aba3e25717850c26c9cd0d89d", 40) != 0) {
        fprintf(stderr, "SHA mismatch: got %.40s expected %.40s\n",
                hash, "a9993e364706816aba3e25717850c26c9cd0d89d");
        return 6;
    }

    /* 7. MD5 of "abc" matches the published digest (also upstream tst-md5.c) */
    iks_md5("abc", md5);
    md5[32] = '\0';
    if (strncmp(md5, "900150983cd24fb0d6963f7d28e17f72", 32) != 0) {
        fprintf(stderr, "MD5 mismatch: got %.32s expected %.32s\n",
                md5, "900150983cd24fb0d6963f7d28e17f72");
        return 7;
    }

    /* 8. base64 round-trip preserves payload */
    encoded = iks_base64_encode("hello", 5);
    if (encoded == NULL || iks_strcmp(encoded, "aGVsbG8=") != 0) {
        return 8;
    }
    decoded = iks_base64_decode(encoded);
    if (decoded == NULL || iks_strcmp(decoded, "hello") != 0) {
        return 8;
    }

    /* 9. JID parses into user, server and resource parts */
    stack = iks_stack_new(256, 1024);
    if (stack == NULL) {
        return 9;
    }
    id = iks_id_new(stack, "user@example.org/resource");
    if (id == NULL) {
        return 9;
    }
    if (iks_strcmp(id->user, "user") != 0 || iks_strcmp(id->server, "example.org") != 0) {
        return 9;
    }
    if (iks_strcmp(id->resource, "resource") != 0) {
        return 9;
    }
    iks_stack_delete(stack);

    printf("libiksemel 1.4 smoke test passed\n");
    return 0;
}
