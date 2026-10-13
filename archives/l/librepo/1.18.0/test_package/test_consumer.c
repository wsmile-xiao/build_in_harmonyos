/* test_consumer.c — librepo 1.18.0 consumer-side functional test.
 *
 * Parses a local metalink3 XML fixture (same format as upstream
 * tests/test_data/metalinks/metalink_good_01, truncated to two mirrors)
 * with the packaged librepo and asserts the parsed metadata, then checks
 * the packaged version macros.  Pure local execution, no network.
 */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <glib.h>

#include <librepo/metalink.h>
#include <librepo/version.h>

static int fails = 0;
static int checks = 0;

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        checks++;                                                          \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL: %s\n", msg);                            \
            fails++;                                                       \
        } else {                                                           \
            printf("ok: %s\n", msg);                                       \
        }                                                                  \
    } while (0)

int main(int argc, char **argv)
{
    const char *fixture;
    int fd;
    gboolean ret;
    LrMetalink *ml = NULL;
    LrMetalinkUrl *url0 = NULL;
    LrMetalinkHash *hash0 = NULL;
    GError *err = NULL;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <metalink_fixture.xml>\n", argv[0]);
        return 2;
    }
    fixture = argv[1];

    CHECK(LR_VERSION_CHECK(LR_VERSION_MAJOR, LR_VERSION_MINOR, LR_VERSION_PATCH),
          "LR_VERSION_CHECK on the packaged version");
    CHECK(!LR_VERSION_CHECK(LR_VERSION_MAJOR + 1, 0, 0),
          "LR_VERSION_CHECK rejects a newer version");

    fd = open(fixture, O_RDONLY);
    CHECK(fd >= 0, "open metalink fixture");

    ml = lr_metalink_init();
    CHECK(ml != NULL, "lr_metalink_init");

    ret = lr_metalink_parse_file(ml, fd, "repomd.xml", NULL, NULL, &err);
    close(fd);
    CHECK(ret, "lr_metalink_parse_file succeeds");
    CHECK(err == NULL, "no parse error");
    if (!ret) {
        fprintf(stderr, "parse error: %s\n",
                (err && err->message) ? err->message : "(null)");
        g_clear_error(&err);
        return 1;
    }

    CHECK(ml->filename != NULL && strcmp(ml->filename, "repomd.xml") == 0,
          "parsed filename");
    CHECK(ml->timestamp == 1337942396, "parsed timestamp");
    CHECK(ml->size == 4309, "parsed size");
    CHECK(g_slist_length(ml->hashes) == 2, "two hashes parsed");
    CHECK(g_slist_length(ml->urls) == 2, "two mirror urls parsed");

    hash0 = g_slist_nth_data(ml->hashes, 0);
    CHECK(hash0 != NULL && hash0->type != NULL
              && strcmp(hash0->type, "md5") == 0,
          "first hash type is md5");
    CHECK(hash0 != NULL && hash0->value != NULL
              && strcmp(hash0->value, "20b6d77930574ae541108e8e7987ad3f") == 0,
          "first hash value");

    url0 = g_slist_nth_data(ml->urls, 0);
    CHECK(url0 != NULL && url0->protocol != NULL
              && strcmp(url0->protocol, "http") == 0,
          "first mirror protocol");
    CHECK(url0 != NULL && url0->location != NULL
              && strcmp(url0->location, "US") == 0,
          "first mirror location");
    CHECK(url0 != NULL && url0->preference == 99, "first mirror preference");
    CHECK(url0 != NULL && url0->url != NULL
              && strcmp(url0->url,
                        "http://mirror.example.com/fedora/linux/releases/17/"
                        "Everything/x86_64/os/repodata/repomd.xml") == 0,
          "first mirror url");

    lr_metalink_free(ml);

    if (fails) {
        fprintf(stderr, "%d/%d checks failed\n", fails, checks);
        return 1;
    }
    printf("ALL %d CHECKS PASSED\n", checks);
    return 0;
}
