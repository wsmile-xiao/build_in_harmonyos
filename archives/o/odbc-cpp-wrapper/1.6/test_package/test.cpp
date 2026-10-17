#include <odbc/Environment.h>
#include <odbc/Types.h>
#include <odbc/Forwards.h>
#include <stdio.h>

int main(void) {
    // Create an ODBC environment - this calls SQLAllocHandle via libiodbc
    odbc::EnvironmentRef env = odbc::Environment::create();
    if (env.isNull()) {
        fprintf(stderr, "Failed to create ODBC environment\n");
        return 1;
    }
    printf("test odbc-cpp-wrapper 1.6: OK\n");
    return 0;
}
