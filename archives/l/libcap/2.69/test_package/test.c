#include <sys/capability.h>
#include <stdio.h>

int main(void) {
    /* Test cap_from_text / cap_to_text / cap_free — userspace API, no kernel needed */
    cap_t caps = cap_from_text("cap_net_raw+ep");
    if (caps == NULL) {
        fprintf(stderr, "cap_from_text failed\n");
        return 1;
    }
    char *text = cap_to_text(caps, NULL);
    if (text == NULL) {
        fprintf(stderr, "cap_to_text failed\n");
        cap_free(caps);
        return 1;
    }
    printf("capabilities: %s\n", text);
    cap_free(text);
    cap_free(caps);
    printf("libcap test: OK\n");
    return 0;
}
