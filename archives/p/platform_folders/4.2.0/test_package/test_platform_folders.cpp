// platform_folders 4.2.0 — 消费者测试
// 链接 libplatform_folders 并真实调用 API：OHOS（非 Windows/非 Apple）走
// XDG/Linux 目录查询实现，返回值非空即代表目录解析成功；internal 分词器
// 为无环境依赖的纯逻辑断言。
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include <sago/platform_folders.h>

static int failures = 0;

static void check_nonempty(const char* name, const std::string& v) {
    if (v.empty()) {
        std::cerr << "FAIL " << name << " returned empty\n";
        ++failures;
    }
}

int main() {
    // 主目录族 getter（XDG_* 变量优先，回退 $HOME/.xxx；非 root 用户 HOME 可用）
    check_nonempty("getDataHome", sago::getDataHome());
    check_nonempty("getConfigHome", sago::getConfigHome());
    check_nonempty("getCacheDir", sago::getCacheDir());
    check_nonempty("getStateDir", sago::getStateDir());

    // 用户目录族 getter（读 $XDG_CONFIG_HOME/user-dirs.dirs，缺失回退 $HOME 默认）
    check_nonempty("getDesktopFolder", sago::getDesktopFolder());
    check_nonempty("getDocumentsFolder", sago::getDocumentsFolder());
    check_nonempty("getDownloadFolder", sago::getDownloadFolder());
    check_nonempty("getDownloadFolder1", sago::getDownloadFolder1());
    check_nonempty("getPicturesFolder", sago::getPicturesFolder());
    check_nonempty("getPublicFolder", sago::getPublicFolder());
    check_nonempty("getMusicFolder", sago::getMusicFolder());
    check_nonempty("getVideoFolder", sago::getVideoFolder());
    check_nonempty("getSaveGamesFolder1", sago::getSaveGamesFolder1());

    // 类方法
    sago::PlatformFolders pf;
    check_nonempty("PlatformFolders::getDocumentsFolder", pf.getDocumentsFolder());
    check_nonempty("PlatformFolders::getDesktopFolder", pf.getDesktopFolder());
    check_nonempty("PlatformFolders::getPicturesFolder", pf.getPicturesFolder());
    check_nonempty("PlatformFolders::getDownloadFolder1", pf.getDownloadFolder1());
    check_nonempty("PlatformFolders::getSaveGamesFolder1", pf.getSaveGamesFolder1());

    // 附加目录向量（默认 /usr/local/share、/etc/xdg 等，非空）
    std::vector<std::string> extra;
    sago::appendAdditionalDataDirectories(extra);
    if (extra.empty()) {
        std::cerr << "FAIL appendAdditionalDataDirectories returned empty\n";
        ++failures;
    }
    extra.clear();
    sago::appendAdditionalConfigDirectories(extra);
    if (extra.empty()) {
        std::cerr << "FAIL appendAdditionalConfigDirectories returned empty\n";
        ++failures;
    }

    // internal 纯逻辑（无环境依赖）：冒号分隔 tokenizer 保留绝对路径、跳过相对项
    std::vector<std::string> tok;
    sago::internal::appendExtraFoldersTokenizer("", "/hello:two:/three", tok);
    if (tok.size() < 2 || tok.at(0) != "/hello" || tok.at(1) != "/three") {
        std::cerr << "FAIL appendExtraFoldersTokenizer result\n";
        ++failures;
    }

    if (failures == 0) {
        std::cout << "platform_folders 4.2.0 consumer: ALL OK (20 checks)\n";
        return 0;
    }
    std::cerr << "platform_folders 4.2.0 consumer: " << failures << " FAILURES\n";
    return 1;
}
