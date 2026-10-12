#include "http_fixture.h"
#include <onion/url.h>
#include <onion/response.h>

static onion_connection_status hello(void *unused, onion_request *req, onion_response *res) {
    (void)unused; (void)req;
    onion_response_set_length(res,8);
    return onion_response_write0(res, "hi-ohpcd") < 0 ? OCS_INTERNAL_ERROR : OCS_PROCESSED;
}
int main(void) {
    fixture f; int rc=1; alarm(20);
    if(fixture_init(&f)) return 1;
    if(onion_url_add(onion_root_url(f.server), "hello", hello)) goto done;
    if(fixture_start(&f)) goto done;
    char response[4096];
    if(fixture_get(&f,"/hello",response,sizeof(response))) goto done;
    if(!strstr(response,"HTTP/1.1 200") || !strstr(response,"\r\n\r\nhi-ohpcd")) goto done;
    rc=0;
done:
    if(fixture_end(&f)) rc=1;
    if(!rc) puts("CONSUMER_TEST_PASS=1/1");
    else fputs("FAIL: real onion loopback HTTP roundtrip\n",stderr);
    return rc;
}
