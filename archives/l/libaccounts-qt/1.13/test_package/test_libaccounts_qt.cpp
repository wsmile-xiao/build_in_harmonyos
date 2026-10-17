#include <Accounts/manager.h>
#include <Accounts/account.h>
#include <Accounts/service.h>

int main(void) {
    // Instantiate the Accounts::Manager - tests that the library
    // links correctly and the Qt meta-object system works
    Accounts::Manager manager;

    // Verify we can access the API
    Accounts::AccountIdList list = manager.accountList();

    // If we get here without crashing, the library works
    return 0;
}
