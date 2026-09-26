#include <curl/curl.h>
#include <stdio.h>

static size_t discard(void *ptr, size_t size, size_t nmemb, void *userdata)
{
    (void)ptr;
    (void)userdata;
    return size * nmemb;
}

int main(void)
{
    const curl_version_info_data *info = curl_version_info(CURLVERSION_NOW);
    CURL *handle;
    CURLcode rc;

    if (!info || !info->version) {
        fprintf(stderr, "curl_version_info failed\n");
        return 1;
    }
    handle = curl_easy_init();
    if (!handle) {
        fprintf(stderr, "curl_easy_init failed\n");
        return 2;
    }
    curl_easy_setopt(handle, CURLOPT_URL, "file:///dev/null");
    curl_easy_setopt(handle, CURLOPT_WRITEFUNCTION, discard);
    rc = curl_easy_perform(handle);
    curl_easy_cleanup(handle);
    if (rc != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform failed: %s\n", curl_easy_strerror(rc));
        return 3;
    }
    printf("libcurl %s: OK\n", info->version);
    return 0;
}
