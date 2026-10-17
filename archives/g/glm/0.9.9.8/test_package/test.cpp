#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <cstdio>

int main() {
    // Test basic vec types
    glm::vec4 v(1.0f, 2.0f, 3.0f, 4.0f);
    if (v.x != 1.0f || v.y != 2.0f || v.z != 3.0f || v.w != 4.0f) {
        return 1;
    }

    // Test matrix operations
    glm::mat4 m = glm::mat4(1.0f);
    glm::vec4 transformed = m * v;
    if (transformed.x != 1.0f || transformed.y != 2.0f ||
        transformed.z != 3.0f || transformed.w != 4.0f) {
        return 1;
    }

    // Test translation matrix
    glm::mat4 trans = glm::translate(glm::mat4(1.0f), glm::vec3(1.0f, 0.0f, 0.0f));
    glm::vec4 result = trans * glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    if (result.x != 1.0f) {
        return 1;
    }

    printf("test glm 0.9.9.8: OK\n");
    return 0;
}
