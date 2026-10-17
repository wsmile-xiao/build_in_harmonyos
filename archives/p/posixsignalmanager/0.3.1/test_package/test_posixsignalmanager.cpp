#include <PosixSignalManager.h>
#include <cassert>
#include <csignal>
#include <cstdio>

int main(void) {
    int result = PosixSignalManager::classifySignal(SIGTERM);
    assert(result == 1);
    result = PosixSignalManager::classifySignal(SIGSEGV);
    assert(result == 3);
    result = PosixSignalManager::classifySignal(SIGINT);
    assert(result == 1);
    printf("test posixsignalmanager 0.3.1: OK (classifySignal verified)\n");
    return 0;
}
