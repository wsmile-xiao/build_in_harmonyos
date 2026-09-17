/* R34 consumer test for libytnef 2.1.2.
 *
 * Parses the bundled TNEF sample (one-file.tnef) through the installed public
 * API and asserts the decoded message, so the exit code reflects real library
 * behaviour rather than a successful link.
 */
#include <stdio.h>
#include <string.h>

#include <ytnef.h>

static const char *find_sample(int argc, char **argv)
{
    static const char *fallbacks[] = {
        "one-file.tnef",
        "../test_package/one-file.tnef",
        "../../test_package/one-file.tnef",
    };
    static char from_argv[4096];

    if (argc > 1) {
        FILE *probe = fopen(argv[1], "rb");
        if (probe) {
            fclose(probe);
            strncpy(from_argv, argv[1], sizeof(from_argv) - 1);
            from_argv[sizeof(from_argv) - 1] = '\0';
            return from_argv;
        }
    }
    for (unsigned i = 0; i < sizeof(fallbacks) / sizeof(fallbacks[0]); i++) {
        FILE *probe = fopen(fallbacks[i], "rb");
        if (probe) {
            fclose(probe);
            return fallbacks[i];
        }
    }
    return NULL;
}

int main(int argc, char **argv)
{
    const char *sample = find_sample(argc, argv);
    if (sample == NULL) {
        fprintf(stderr, "FAIL: could not locate the one-file.tnef sample\n");
        return 10;
    }

    TNEFStruct tnef;
    TNEFInitialize(&tnef);
    tnef.Debug = 0;
    tnef.attachmentSize = 50;

    if (TNEFParseFile((char *) sample, &tnef) < 0) {
        fprintf(stderr, "FAIL: TNEFParseFile() failed for %s\n", sample);
        TNEFFree(&tnef);
        return 1;
    }

    /* stream version */
    if (strncmp(tnef.version, "TNEF", 4) != 0) {
        fprintf(stderr, "FAIL: unexpected stream version '%s'\n", tnef.version);
        TNEFFree(&tnef);
        return 2;
    }

    /* decoded message subject */
    if (tnef.subject.size <= 0 || tnef.subject.data == NULL ||
        strcmp((const char *) tnef.subject.data, "one-file") != 0) {
        fprintf(stderr, "FAIL: unexpected subject (size=%d)\n", tnef.subject.size);
        TNEFFree(&tnef);
        return 3;
    }

    /* decoded message class and internet message id */
    if (strncmp(tnef.messageClass, "IPM.Microsoft Mail.Note", 23) != 0) {
        fprintf(stderr, "FAIL: unexpected message class '%s'\n", tnef.messageClass);
        TNEFFree(&tnef);
        return 4;
    }
    if (strcmp(tnef.messageID, "20017FCFD081D311A7A50008C71BCA8D") != 0) {
        fprintf(stderr, "FAIL: unexpected message id '%s'\n", tnef.messageID);
        TNEFFree(&tnef);
        return 5;
    }

    /* attachments carried by the stream */
    int attachments = 0;
    long attachment_bytes = 0;
    for (Attachment *item = tnef.starting_attach.next; item != NULL; item = item->next) {
        attachments++;
        attachment_bytes += item->FileData.size;
    }
    if (attachments < 1) {
        fprintf(stderr, "FAIL: expected at least one attachment, got %d\n", attachments);
        TNEFFree(&tnef);
        return 6;
    }
    if (attachment_bytes <= 0) {
        fprintf(stderr, "FAIL: attachment payloads are empty\n");
        TNEFFree(&tnef);
        return 7;
    }

    /* mapi properties decoded for the message */
    if (tnef.MapiProperties.count <= 0) {
        fprintf(stderr, "FAIL: no MAPI properties decoded\n");
        TNEFFree(&tnef);
        return 8;
    }

    printf("libytnef test_package passed: subject=\"%s\" attachments=%d bytes=%ld "
           "mapi_properties=%lu\n",
           (const char *) tnef.subject.data, attachments, attachment_bytes,
           (unsigned long) tnef.MapiProperties.count);

    TNEFFree(&tnef);
    return 0;
}
