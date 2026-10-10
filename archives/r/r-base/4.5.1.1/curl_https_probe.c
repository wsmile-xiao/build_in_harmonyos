#include <curl/curl.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    curl_version_info_data *data = curl_version_info(CURLVERSION_NOW);
    const char * const *protocol = data->protocols;

    for (; protocol && *protocol; ++protocol) {
        if (strcmp(*protocol, "https") == 0) {
            puts("CURL_HTTPS_CONSUMER=PASS");
            return 0;
        }
    }
    fputs("CURL_HTTPS_CONSUMER=FAIL\n", stderr);
    return 1;
}
