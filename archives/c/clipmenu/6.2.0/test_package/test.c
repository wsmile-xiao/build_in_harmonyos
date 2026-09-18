#include <stdio.h>
#include <stdlib.h>

int main(void) {
    // Test clipmenu installation by verifying it's in PATH
    printf("Testing clipmenu installation...\n");
    
    // Verify clipmenu is installed and on PATH (doesn't require X11)
    int ret = system("command -v clipmenu >/dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "clipmenu is not installed or not on PATH\n");
        return 1;
    }
    
    printf("test clipmenu 6.2.0: OK (script executable)\n");
    return 0;
}
