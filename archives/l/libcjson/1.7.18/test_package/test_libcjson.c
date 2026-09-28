#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cjson/cJSON.h"

int main(void)
{
    /* Exercise the real cJSON API: parse, query, print, delete. */
    const char *json_str = "{\"name\":\"cjson\",\"version\":\"1.7.18\",\"features\":[1,2,3]}";
    cJSON *json = cJSON_Parse(json_str);
    if (!json) {
        fprintf(stderr, "cJSON_Parse failed: %s\n", cJSON_GetErrorPtr());
        return 1;
    }

    cJSON *name = cJSON_GetObjectItem(json, "name");
    if (!name || !cJSON_IsString(name) || strcmp(name->valuestring, "cjson") != 0) {
        fprintf(stderr, "Failed to read 'name' field\n");
        cJSON_Delete(json);
        return 1;
    }

    cJSON *features = cJSON_GetObjectItem(json, "features");
    if (!features || !cJSON_IsArray(features) || cJSON_GetArraySize(features) != 3) {
        fprintf(stderr, "Failed to read 'features' array\n");
        cJSON_Delete(json);
        return 1;
    }

    char *printed = cJSON_PrintUnformatted(json);
    if (!printed) {
        fprintf(stderr, "cJSON_PrintUnformatted failed\n");
        cJSON_Delete(json);
        return 1;
    }

    cJSON *reparsed = cJSON_Parse(printed);
    free(printed);
    if (!reparsed) {
        fprintf(stderr, "Round-trip reparse failed\n");
        cJSON_Delete(json);
        return 1;
    }
    cJSON_Delete(reparsed);

    printf("cJSON test PASSED: parsed '%s', name='%s', features=%d\n",
           json_str, name->valuestring, cJSON_GetArraySize(features));
    cJSON_Delete(json);
    return 0;
}
