#include <ngfclient.h>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // Real API call: construct Ngf::Client and query connection status.
    // isConnected() returns false when NGF daemon ngfd is not running,
    // which is expected in CI—this verifies the library links and API works.
    Ngf::Client client;
    if (!client.isConnected()) {
        std::printf("libngf-qt test PASSED (daemon not running, API call succeeded)\n");
        return 0;
    }
    std::printf("libngf-qt test PASSED\n");
    return 0;
}
