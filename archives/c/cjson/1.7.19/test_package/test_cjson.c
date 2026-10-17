#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cjson/cJSON.h"

int main(void)
{
    const char *json_str = "{\"name\":\"cjson\",\"version\":\"1.7.19\"}";
    cJSON *json = cJSON_Parse(json_str);
    if (!json) {
        fprintf(stderr, "cJSON_Parse failed\n");
        return 1;
    }

    cJSON *name = cJSON_GetObjectItem(json, "name");
    if (!name || !cJSON_IsString(name)) {
        fprintf(stderr, "Failed to get 'name'\n");
        cJSON_Delete(json);
        return 1;
    }

    if (strcmp(name->valuestring, "cjson") != 0) {
        fprintf(stderr, "Unexpected value for 'name': expected 'cjson', got '%s'\n",
                name->valuestring);
        cJSON_Delete(json);
        return 1;
    }

    printf("cJSON test PASSED: parsed '%s' successfully, name='%s'\n",
           json_str, name->valuestring);
    cJSON_Delete(json);
    return 0;
}