// HarmonyOS 专项测试 — libfex 0.1.0 (C++23 fusex userspace library)
//
// 覆盖 OHOS 平台（aarch64-linux-ohos / clang-15 / libc++15）下 libfex
// 真实公开 API 的编译与运行正确性：
//   1. std::expected 契约：OHOS libc++15 缺 <expected>，libfex 通过
//      fex/expected_compat.hpp polyfill 提供；本测试直接使用公共头
//      中的 std::expected 返回类型并断言 value/unexpected 语义。
//   2. NodeId / EntryOut / StatxOut 强类型与 statx_mask 位契约。
//   3. Filesystem 默认回调（setstatx/unlink 等）返回 function_not_supported。
//   4. 错误路径 std::unexpected{Errc} 与 operator bool / .error() 可用。
#include <cassert>
#include <chrono>
#include <cstdio>
#include <string_view>

#include <fex/fex.hpp>

namespace {

// 最小 Filesystem 实现：仅实现纯虚回调，用于实例化并触发公开 API。
class TestFs final : public fex::Filesystem {
public:
    std::expected<fex::EntryOut, fex::Errc> lookup_root(const fex::Context&) override {
        fex::EntryOut out{};
        out.nodeid      = fex::NodeId::root;
        out.entry_valid = std::chrono::seconds{2};
        return out;
    }
    std::expected<fex::EntryOut, fex::Errc>
    lookupx(const fex::Context&, fex::NodeId parent, std::string_view name) override {
        fex::EntryOut out{};
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

}  // namespace

int main() {
    std::printf("harmonyos libfex test: start (clang-%d libc++15 polyfill path)\n",
                __clang_major__);

    TestFs fs;
    fex::Context ctx{};

    // 1) lookup_root -> EntryOut.nodeid == NodeId::root (纯虚回调可运行)
    {
        auto r = fs.lookup_root(ctx);
        assert(r.has_value());
        assert(fex::to_underlying(r->nodeid) == fex::to_underlying(fex::NodeId::root));
    }

    // 2) lookupx -> nodeid = parent + name.size()（可观察确定性结果）
    {
        auto r = fs.lookupx(ctx, fex::NodeId::root, "abc");
        assert(r.has_value());
        assert(fex::to_underlying(r->nodeid) == 1u + 3u);
    }

    // 3) statx -> StatxOut.ino 与 mask 契约
    {
        auto r = fs.statx(ctx, fex::NodeId{99});
        assert(r.has_value());
        assert(r->ino == 99u);
        assert((r->mask & fex::statx_mask::ino) != 0u);
        assert((r->mask & fex::statx_mask::mode) != 0u);
    }

    // 4) 默认回调错误路径：std::unexpected{Errc::function_not_supported}
    {
        fex::SetStatxIn in{};
        auto r = fs.setstatx(ctx, fex::NodeId::root, fex::FileHandle{0}, in);
        assert(!r.has_value());
        assert(!r);
        assert(r.error() == fex::Errc::function_not_supported);

        auto u = fs.unlink(ctx, fex::NodeId::root, "x");
        assert(!u.has_value());
        assert(u.error() == fex::Errc::function_not_supported);

        auto m = fs.mkobjx(ctx, fex::NodeId::root, fex::MkobjxIn{});
        assert(!m.has_value());
        assert(m.error() == fex::Errc::function_not_supported);
    }

    // 5) void expected：init 默认成功；emplace 可作用于 expected<void>
    {
        fex::InitInfo ii{};
        auto i = fs.init(ii);
        assert(i.has_value());
        decltype(i) v{};
        v.emplace();
        assert(v.has_value());
    }

    // 6) R02 P1 回归：混合状态赋值（值→错 / 错→值，复制+移动）
    {
        using T = std::pair<int, int>;
        using Exp = std::expected<T, fex::Errc>;
        // 复制赋值：值→错（旧值需被析构、错误被构造）
        Exp a(std::in_place, 1, 2);
        Exp b = std::unexpected(fex::Errc::invalid_argument);
        a = b;
        assert(!a.has_value());
        assert(a.error() == fex::Errc::invalid_argument);
        // 复制赋值：错→值
        Exp c = std::unexpected(fex::Errc::io_error);
        Exp d(std::in_place, 3, 4);
        c = d;
        assert(c.has_value());
        assert(c.value().first == 3 && c.value().second == 4);
        // 移动赋值：值→错
        Exp e(std::in_place, 5, 6);
        Exp f = std::unexpected(fex::Errc::permission_denied);
        e = std::move(f);
        assert(!e.has_value());
        assert(e.error() == fex::Errc::permission_denied);
        // 移动赋值：错→值
        Exp g = std::unexpected(fex::Errc::timed_out);
        Exp h(std::in_place, 7, 8);
        g = std::move(h);
        assert(g.has_value());
        assert(g.value().first == 7 && g.value().second == 8);
        // 同态赋值保持：值→值 / 错→错
        Exp i2(std::in_place, 9, 9);
        Exp j2(std::in_place, 10, 10);
        i2 = j2;
        assert(i2.has_value() && i2.value().first == 10);
        Exp k2 = std::unexpected(fex::Errc::connection_refused);
        Exp l2 = std::unexpected(fex::Errc::not_connected);
        k2 = l2;
        assert(!k2.has_value() && k2.error() == fex::Errc::not_connected);
    }

    // 7) R02 P2 回归：or_else const&&（void 版）值/错误态语义
    {
        using Exp = std::expected<int, fex::Errc>;
        int called = 0;
        auto cb = [&](const fex::Errc& e) { (void)e; ++called; };
        // 值态：不调用 f，原样返回
        const Exp ok(std::in_place, 42);
        auto r1 = std::move(ok).or_else(cb);
        assert(called == 0);
        assert(r1.has_value() && r1.value() == 42);
        // 错误态：调用 f，返回错误态
        const Exp bad = std::unexpected(fex::Errc::no_such_file_or_directory);
        auto r2 = std::move(bad).or_else(cb);
        assert(called == 1);
        assert(!r2.has_value());
        assert(r2.error() == fex::Errc::no_such_file_or_directory);
    }

    std::printf("harmonyos libfex test: ALL PASSED\n");
    return 0;
}