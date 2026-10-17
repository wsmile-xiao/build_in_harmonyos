/*
 * Consumer test for ytnef/2.1.2 (R34: must exercise the packaged artifact).
 *
 * Runs against the real installed libytnef and the bundled TNEF fixture
 * `one-file.tnef`, so it fails if the library is not actually usable from a
 * consumer:
 *   1. the TNEF stream signature helper accepts/rejects the right value
 *   2. TNEFParseFile() decodes the fixture end to end (real code paths,
 *      including the attachment handler)
 *   3. the attachment list is populated and carries the expected file name
 *   4. TNEFInitialize()/TNEFFree() round trip without leaking the structure
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ytnef.h>

static int failures = 0;

static void check(int ok, const char *msg)
{
    if (ok) {
        printf("ok   - %s\n", msg);
    } else {
        printf("FAIL - %s\n", msg);
        failures++;
    }
}

int main(void)
{
    const char *fixture = "one-file.tnef";
    TNEFStruct tnef;
    Attachment *att;
    int attachments = 0;
    int named_authors = 0;
    FILE *fh;
    DWORD signature = 0;
    int parsed;

    /* ── 1. stream signature helper ────────────────────────────────── */
    fh = fopen(fixture, "rb");
    check(fh != NULL, "fixture one-file.tnef is readable");
    if (fh == NULL) {
        return 1;
    }
    if (fread(&signature, 1, sizeof(signature), fh) != sizeof(signature)) {
        fclose(fh);
        printf("FAIL - fixture shorter than the TNEF signature\n");
        return 1;
    }
    fclose(fh);

    check(TNEFCheckForSignature(signature) == 0,
          "TNEFCheckForSignature() accepts the fixture signature");
    check(TNEFCheckForSignature((DWORD)0x00000000) != 0,
          "TNEFCheckForSignature() rejects a bogus signature");

    /* ── 2./3. full parse through the public API ───────────────────── */
    TNEFInitialize(&tnef);
    parsed = TNEFParseFile((char *)fixture, &tnef);
    check(parsed == 0, "TNEFParseFile() decodes the fixture for real");

    for (att = tnef.starting_attach.next; att != NULL; att = att->next) {
        attachments++;
        if (att->Title.size > 0 && att->Title.data != NULL &&
            strcmp((char *)att->Title.data, "AUTHORS") == 0) {
            named_authors = 1;
        }
    }
    check(attachments >= 1, "attachment list is populated by the parser");
    check(named_authors == 1,
          "the decoded attachment is the expected 'AUTHORS' file");
    check(strcmp((char *)tnef.messageClass, "IPM.Microsoft Mail.Note") == 0,
          "message class decoded as IPM.Microsoft Mail.Note");

    TNEFFree(&tnef);

    /* ── 4. lifecycle on a pristine structure ──────────────────────── */
    TNEFInitialize(&tnef);
    check(tnef.starting_attach.next == NULL,
          "TNEFInitialize() leaves an empty attachment list");
    TNEFFree(&tnef);

    if (failures == 0) {
        printf("PASS: ytnef/2.1.2 consumer test (%d assertions)\n", 8);
        return 0;
    }
    printf("FAILED: %d assertion(s) failed\n", failures);
    return 1;
}
