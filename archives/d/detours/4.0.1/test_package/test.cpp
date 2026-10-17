#include <windows.h>
#include <detours.h>
#include <stdio.h>

int main() {
    BOOL isHelper = DetourIsHelperProcess();
    printf("DetourIsHelperProcess() = %d\n", (int)isHelper);
    if (isHelper != FALSE) {
        printf("FAIL: DetourIsHelperProcess() expected FALSE, got %d\n", (int)isHelper);
        return 1;
    }
    printf("Detours library linked successfully.\n");
    return 0;
}
