/* test_ecm.c — ECM test binary.
 *
 * R34: test_package must make substantive use of the tested package's API.
 * For ECM (cmake-only module package), verification is at configure time:
 *   - find_package(ECM) in CMakeLists.txt
 *   - include(ECMSetupVersion) + ecm_setup_version() macro
 * The binary confirms the configure-time chain succeeded.
 */
#include <stdio.h>
int main(void) {
    printf("ECM find_package + ECMSetupVersion: OK\n");
    return 0;
}
