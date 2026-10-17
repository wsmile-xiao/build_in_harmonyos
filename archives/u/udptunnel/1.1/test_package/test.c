/* Consumer test for udptunnel: verifies the packaged binary is present and
 * honors the K0 CLI contract (--help exits 0). The tunnel data plane cannot
 * be exercised headlessly, so assertions stay on the CLI/contract layer.
 */
#include <stdlib.h>

int main(void) {
    int rc = system("udptunnel --help > /dev/null 2>&1");
    return rc != 0 ? 1 : 0;
}
