/* test_package/test_libcurl.c — libcurl 8.5.0 L1 smoke test.
 * Initialize curl, get version info, verify basic API works. */
#include <stdio.h>
#include <string.h>
#include <curl/curl.h>

int main(void) {
    CURLcode ginit_rc = curl_global_init(CURL_GLOBAL_ALL);
    if (ginit_rc != CURLE_OK) {
        fprintf(stderr, "curl_global_init failed: %s\n", curl_easy_strerror(ginit_rc));
        return 1;
    }

    CURL *handle = curl_easy_init();
    if (!handle) {
        fprintf(stderr, "curl_easy_init failed\n");
        curl_global_cleanup();
        return 1;
    }

    char *curl_ver = curl_version();
    if (!curl_ver || strlen(curl_ver) == 0) {
        fprintf(stderr, "curl_version returned empty\n");
        curl_easy_cleanup(handle);
        curl_global_cleanup();
        return 1;
    }

    /* Set a URL to verify setopt works */
    CURLcode rc = curl_easy_setopt(handle, CURLOPT_URL, "https://example.com");
    if (rc != CURLE_OK) {
        fprintf(stderr, "curl_easy_setopt URL failed: %s\n", curl_easy_strerror(rc));
        curl_easy_cleanup(handle);
        curl_global_cleanup();
        return 1;
    }

    printf("libcurl 8.5.0: init/setopt OK, version: %s\n", curl_ver);

    curl_easy_cleanup(handle);
    curl_global_cleanup();
    return 0;
}
