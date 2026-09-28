// test_fcitx5_utils.cpp — fcitx5-utils 5.1.13 test_package 消费者测试
// R34: 实质调用被测包 API，不打印空壳。
// 鸿蒙专项：本机为 aarch64 HarmonyOS，可执行文件真机运行，验证 OHOS 平台
// 头文件/库（libFcitx5Utils.so）链接与 Fcitx5Utils API 可用性。
#include <fcitx-utils/stringutils.h>
#include <fcitx-utils/key.h>
#include <fcitx-utils/semver.h>
#include <fcitx-utils/standardpaths.h>

#include <cassert>
#include <iostream>
#include <string>

int main() {
    // stringutils：trim 真实 API（返回 std::string）
    const std::string trimmed = fcitx::stringutils::trim("  hello  ");
    assert(trimmed == "hello");

    // Key：字符串构造解析真实按键（keynametable/keysymgen 数据）
    const fcitx::Key key("Control+A");
    assert(key.isValid());
    assert(key.sym() == fcitx::KeySym::FcitxKey_a);
    assert(key.states() == fcitx::KeyState::Ctrl);

    // SemanticVersion：版本解析（semver.h，类名 SemanticVersion）
    const auto semver = fcitx::SemanticVersion::parse("5.1.13");
    assert(semver.has_value());
    assert(semver->major() == 5 && semver->minor() == 1 && semver->patch() == 13);

    // StandardPaths：OHOS 平台路径查询（standardpaths_p_unix.cpp 平台适配路径）
    const auto &standardPaths = fcitx::StandardPaths::global();
    const auto dataDirs = standardPaths.directories(fcitx::StandardPathsType::Data);
    (void)dataDirs;
    const auto userDataDir =
        standardPaths.userDirectory(fcitx::StandardPathsType::Data);
    (void)userDataDir;
    const auto addonDirs = standardPaths.directories(fcitx::StandardPathsType::Addon);
    (void)addonDirs;

    std::cout << "fcitx5-utils test OK: trim='" << trimmed << "' key="
              << key.toString() << " semver=" << semver->major() << "."
              << semver->minor() << "." << semver->patch() << std::endl;
    return 0;
}