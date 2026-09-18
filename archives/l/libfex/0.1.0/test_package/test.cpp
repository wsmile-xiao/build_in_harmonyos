// SPDX-License-Identifier: BSD-2-Clause OR GPL-2.0-only
//
// libfex 消费者用例（test_package）：仅通过已安装的公开头文件与公开 API
// 使用 libfex，验证第三方使用者能否编译、链接、调用并正常运行。
//
// 覆盖点：
//  1) 继承 fex::Filesystem 并实现纯虚回调 lookup_root/lookupx/statx；
//  2) 调用公开 API statx()/setstatx()/unlink() 的默认实现，验证返回
//     std::expected 的 std::unexpected{Errc::function_not_supported} 错误；
//  3) 调用默认空实现 init()/forget() 可正常执行（无崩溃）；
//  4) 检查 NodeId/EntryOut/SessionOptions 类型契约。
//
// 该用例不依赖 fusex 内核模块（OHOS 无该内核支持），只验证库本身
// 的 API 契约与错误路径。

#include <fex/fex.hpp>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string_view>

namespace {

// 最小可运行 Filesystem 实现：lookup_root 返回根节点 nodeid=root。
class MinimalFs final : public fex::Filesystem {
public:
    std::expected<fex::EntryOut, fex::Errc> lookup_root(const fex::Context&) override {
        fex::EntryOut out{};
        out.nodeid     = fex::NodeId::root;
        out.entry_valid = std::chrono::seconds{1};
        out.negative   = false;
        return out;
    }
    std::expected<fex::EntryOut, fex::Errc>
    lookupx(const fex::Context&, fex::NodeId parent, std::string_view name) override {
        fex::EntryOut out{};
        // nodeid = parent 基址 + name 长度（可观察、确定性）
        out.nodeid = static_cast<fex::NodeId>(
            fex::to_underlying(parent) + static_cast<std::uint64_t>(name.size()));
        return out;
    }
    std::expected<fex::StatxOut, fex::Errc>
    statx(const fex::Context&, fex::NodeId nodeid) override {
        fex::StatxOut out{};
        out.mask = fex::statx_mask::ino | fex::statx_mask::mode;
        out.ino  = fex::to_underlying(nodeid);
        out.mode = 0x8000;  // S_IFREG
        return out;
    }
};

int check(bool cond, const char* what) {
    if (!cond) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        return 1;
    }
    std::printf("PASS: %s\n", what);
    return 0;
}

}  // namespace

int main() {
    int rc = 0;

    // 1) 公开 API：子类实现 + 纯虚回调可调用
    MinimalFs fs;
    fex::Context ctx{};
    auto root = fs.lookup_root(ctx);
    rc |= check(root.has_value() &&
                    fex::to_underlying(root->nodeid) == fex::to_underlying(fex::NodeId::root),
                "lookup_root returns nodeid=root");

    auto lx = fs.lookupx(ctx, fex::NodeId::root, "abc");
    rc |= check(lx.has_value() &&
                    fex::to_underlying(lx->nodeid) == 1u + 3u,
                "lookupx computes nodeid from parent+name");

    auto st = fs.statx(ctx, fex::NodeId{99});
    rc |= check(st.has_value() &&
                    st->ino == 99u &&
                    (st->mask & fex::statx_mask::ino) != 0u,
                "statx returns nodeid + ino mask");

    // 2) 默认实现返回 function_not_supported（std::expected 错误路径）
    fex::SetStatxIn setin{};
    auto sset = fs.setstatx(ctx, fex::NodeId::root, fex::FileHandle{0}, setin);
    rc |= check(!sset.has_value() &&
                    sset.error() == fex::Errc::function_not_supported,
                "setstatx default -> function_not_supported");

    auto unl = fs.unlink(ctx, fex::NodeId::root, "x");
    rc |= check(!unl.has_value() &&
                    unl.error() == fex::Errc::function_not_supported,
                "unlink default -> function_not_supported");

    // 3) 默认空实现可执行（无崩溃）
    fex::InitInfo ii{};
    auto ini = fs.init(ii);
    rc |= check(ini.has_value(), "init default returns ok");
    fs.forget(fex::NodeId{2}, 1);
    rc |= check(true, "forget default executes");

    // 4) SessionOptions 默认构造
    fex::SessionOptions opts{};
    rc |= check(opts.dev_fd == -1, "SessionOptions default dev_fd == -1");

    // 5) R02 P1 回归（消费者视角）：混合状态赋值（值→错 / 错→值，复制+移动）
    {
        using T = std::pair<int, int>;
        using Exp = std::expected<T, fex::Errc>;
        Exp a(std::in_place, 1, 2);
        Exp b = std::unexpected(fex::Errc::invalid_argument);
        a = b;  // 复制：值→错
        rc |= check(!a.has_value() && a.error() == fex::Errc::invalid_argument,
                    "operator= copy value->error (R02 P1)");
        Exp c = std::unexpected(fex::Errc::io_error);
        Exp d(std::in_place, 3, 4);
        c = d;  // 复制：错→值
        rc |= check(c.has_value() && c.value().first == 3 && c.value().second == 4,
                    "operator= copy error->value (R02 P1)");
        Exp e(std::in_place, 5, 6);
        Exp f = std::unexpected(fex::Errc::permission_denied);
        e = std::move(f);  // 移动：值→错
        rc |= check(!e.has_value() && e.error() == fex::Errc::permission_denied,
                    "operator= move value->error (R02 P1)");
        Exp g = std::unexpected(fex::Errc::timed_out);
        Exp h(std::in_place, 7, 8);
        g = std::move(h);  // 移动：错→值
        rc |= check(g.has_value() && g.value().first == 7 && g.value().second == 8,
                    "operator= move error->value (R02 P1)");
    }

    // 6) R02 P2 回归（消费者视角）：or_else const&& 值/错误态语义
    {
        using Exp = std::expected<int, fex::Errc>;
        int called = 0;
        auto cb = [&](const fex::Errc& e) { (void)e; ++called; };
        const Exp ok(std::in_place, 42);
        auto r1 = std::move(ok).or_else(cb);  // 值态：不应调用 f
        rc |= check(called == 0 && r1.has_value() && r1.value() == 42,
                    "or_else const&& value-state (R02 P2)");
        const Exp bad = std::unexpected(fex::Errc::no_such_file_or_directory);
        auto r2 = std::move(bad).or_else(cb);  // 错误态：应调用 f
        rc |= check(called == 1 && !r2.has_value() &&
                        r2.error() == fex::Errc::no_such_file_or_directory,
                    "or_else const&& error-state (R02 P2)");
    }

    if (rc == 0) {
        std::printf("libfex consumer test: ALL PASSED\n");
        return 0;
    }
    std::printf("libfex consumer test: %d check(s) FAILED\n", rc);
    return 1;
}