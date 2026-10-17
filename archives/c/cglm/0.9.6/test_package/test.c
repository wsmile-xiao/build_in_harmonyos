#include <stdio.h>
#include <cglm/call.h>

int main(void) {
    vec3 v1 = {1.0f, 2.0f, 3.0f};
    vec3 v2 = {4.0f, 5.0f, 6.0f};
    vec3 result;

    /* Test glmc_vec3_add - calls into libcglm */
    glmc_vec3_add(v1, v2, result);

    if (result[0] == 5.0f && result[1] == 7.0f && result[2] == 9.0f) {
        printf("cglm glmc_vec3_add: PASSED\n");
    } else {
        printf("cglm glmc_vec3_add: FAILED (%.2f, %.2f, %.2f)\n",
               result[0], result[1], result[2]);
        return 1;
    }

    /* Test glmc_vec3_norm */
    vec3 v3 = {3.0f, 4.0f, 0.0f};
    float norm = glmc_vec3_norm(v3);
    if (norm == 5.0f) {
        printf("cglm glmc_vec3_norm: PASSED\n");
    } else {
        printf("cglm glmc_vec3_norm: FAILED (%.2f)\n", norm);
        return 1;
    }

    /* Test mat4 operations */
    mat4 m = GLM_MAT4_IDENTITY_INIT;
    vec3 trans = {1.0f, 2.0f, 3.0f};
    glmc_translate(m, trans);

    if (m[3][0] == 1.0f && m[3][1] == 2.0f && m[3][2] == 3.0f) {
        printf("cglm glmc_translate: PASSED\n");
    } else {
        printf("cglm glmc_translate: FAILED\n");
        return 1;
    }

    printf("All cglm tests passed\n");
    return 0;
}
