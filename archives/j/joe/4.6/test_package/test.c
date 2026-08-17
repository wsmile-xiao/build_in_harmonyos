#include <stdio.h>
#include <stdlib.h>

/* joe is a binary tool (not a library). This test executes the joe binary
 * via system() to verify it is installed and functional. The test_package
 * conanfile.py test() method also runs joe --help via self.run(). */
int main(void) {
    int ret = system("joe --help > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "joe --help failed with exit code %d\n", ret);
        return 1;
    }
    printf("test joe 4.6: OK\n");
    return 0;
}
