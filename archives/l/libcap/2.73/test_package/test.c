#include <sys/capability.h>
#include <sys/psx_syscall.h>
#include <stdio.h>

int main(void) {
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

    if (psx_set_sensitivity(PSX_IGNORE) != 0) {
        fprintf(stderr, "psx_set_sensitivity failed\n");
        cap_free(text);
        cap_free(caps);
        return 1;
    }

    if (cap_get_bound(CAP_CHOWN) < 0) {
        perror("cap_get_bound failed");
        cap_free(text);
        cap_free(caps);
        return 1;
    }

    cap_t process_caps = cap_get_proc();
    if (process_caps == NULL) {
        perror("cap_get_proc failed");
        cap_free(text);
        cap_free(caps);
        return 1;
    }

    printf("capabilities: %s\n", text);
    cap_free(process_caps);
    cap_free(text);
    cap_free(caps);
    return 0;
}
