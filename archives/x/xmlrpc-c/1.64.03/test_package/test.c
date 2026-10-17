#include <xmlrpc-c/base.h>
#include <xmlrpc-c/server.h>
#include <stdio.h>

int main(void) {
    xmlrpc_env env;
    xmlrpc_env_init(&env);

    /* Create a registry — core server-side object */
    xmlrpc_registry *registry = xmlrpc_registry_new(&env);
    if (env.fault_occurred) {
        fprintf(stderr, "xmlrpc-c: failed to create registry: %s\n",
                env.fault_string);
        xmlrpc_env_clean(&env);
        return 1;
    }

    printf("xmlrpc-c: registry created OK\n");

    xmlrpc_registry_free(registry);
    xmlrpc_env_clean(&env);
    return 0;
}
