#include <glbinding/gl/gl.h>
#include <glbinding/gl/boolean.h>
#include <glbinding/Version.h>
#include <glbinding-aux/Meta.h>

#include <iostream>
#include <string>

// 消费者视角验证：仅通过 glbinding 公开头文件与公开 API，
// 在无 GL 上下文的环境下调用无需上下文的 API 并校验可观察结果。
int main()
{
    // 1) aux::Meta::getString 公开 API：枚举值 -> 字符串 映射（无需 GL 上下文）
    const std::string & s = glbinding::aux::Meta::getString(gl::GL_FALSE);
    std::cout << "Meta::getString(GL_FALSE) = " << s << std::endl;
    if (s != "GL_FALSE") {
        std::cerr << "FAIL: Meta::getString(GL_FALSE) expected 'GL_FALSE', got '" << s << "'" << std::endl;
        return 1;
    }

    // 2) Version 公开类：构造与比较（无需 GL 上下文）
    const glbinding::Version v(3, 2);
    if (!(v >= glbinding::Version(3, 2))) {
        std::cerr << "FAIL: Version(3,2) >= Version(3,2) expected true" << std::endl;
        return 2;
    }
    if (v >= glbinding::Version(4, 0)) {
        std::cerr << "FAIL: Version(3,2) >= Version(4,0) expected false" << std::endl;
        return 3;
    }

    // 3) aux::Meta::getString 对 GL_NO_ERROR（GLenum 枚举值）
    // glbinding 枚举中 GL_NO_ERROR 与 GL_NONE 同为 ErrorCode 0（enum.h 注释
    // "GL_NO_ERROR = 0, // reuse ErrorCode"），Meta 返回规范名 GL_NONE。
    const std::string & e = glbinding::aux::Meta::getString(gl::GL_NO_ERROR);
    std::cout << "Meta::getString(GL_NO_ERROR) = " << e << std::endl;
    if (e != "GL_NONE") {
        std::cerr << "FAIL: Meta::getString(GL_NO_ERROR) expected 'GL_NONE', got '" << e << "'" << std::endl;
        return 4;
    }

    std::cout << "glbinding 3.5.0 consumer test: OK" << std::endl;
    return 0;
}
