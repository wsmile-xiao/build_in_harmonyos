#include <rest/rest.h>
#include <rest/rest-proxy.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    RestProxy *proxy = rest_proxy_new("https://example.com", FALSE);
    if (proxy == NULL || !REST_IS_PROXY(proxy)) {
        return 1;
    }
    rest_proxy_set_user_agent(proxy, "librest-consumer/1");
    const gchar *agent = rest_proxy_get_user_agent(proxy);
    if (agent == NULL || strcmp(agent, "librest-consumer/1") != 0) {
        g_object_unref(proxy);
        return 2;
    }
    g_object_unref(proxy);
    puts("librest_consumer=PASS");
    return 0;
}
