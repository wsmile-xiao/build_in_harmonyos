/************************************************************************
 * nuraft 3.0.0 HarmonyOS PC 冒烟测试
 *
 * 单进程内起 3 节点内存状态机集群（asio 回环地址 127.0.0.1），
 * 验证：
 *   1. leader 选举（初始单节点自动当选，add_srv 扩展为 3 节点）
 *   2. 一条日志复制（append_entries 后所有节点 commit index 前进）
 *
 * 参考上游 examples/quick_start.cxx 与 raft_server_test.cxx 形态。
 **************************************************************************/
#include "in_memory_state_mgr.hxx"
#include "libnuraft/nuraft.hxx"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>
#include <thread>

using namespace nuraft;

// ---- 简易状态机（参考上游 examples/echo_state_machine.hxx，记录最近提交 index） ----
class test_state_machine : public state_machine {
public:
    test_state_machine() : last_committed_idx_(0) {}
    ~test_state_machine() {}

    ptr<buffer> pre_commit(const ulong log_idx, buffer& data) override {
        (void)log_idx; (void)data;
        return nullptr;
    }

    ptr<buffer> commit(const ulong log_idx, buffer& data) override {
        (void)data;
        last_committed_idx_ = log_idx;
        return nullptr;
    }

    void commit_config(const ulong log_idx, ptr<cluster_config>& new_conf) override {
        (void)new_conf;
        last_committed_idx_ = log_idx;
    }

    void rollback(const ulong log_idx, buffer& data) override {
        (void)log_idx; (void)data;
    }

    int read_logical_snp_obj(snapshot& s, void*& user_snp_ctx,
                             ulong obj_id, ptr<buffer>& data_out,
                             bool& is_last_obj) override {
        (void)s; (void)user_snp_ctx; (void)obj_id;
        data_out = buffer::alloc(sizeof(int32));
        buffer_serializer bs(data_out);
        bs.put_i32(0);
        is_last_obj = true;
        return 0;
    }

    void save_logical_snp_obj(snapshot& s, ulong& obj_id, buffer& data,
                              bool is_first_obj, bool is_last_obj) override {
        (void)s; (void)data; (void)is_first_obj; (void)is_last_obj;
        obj_id++;
    }

    bool apply_snapshot(snapshot& s) override {
        (void)s;
        return true;
    }

    void free_user_snp_ctx(void*& user_snp_ctx) override { (void)user_snp_ctx; }

    ptr<snapshot> last_snapshot() override { return nullptr; }

    ulong last_commit_index() override {
        return last_committed_idx_.load();
    }

    void create_snapshot(snapshot& s,
                         async_result<bool>::handler_type& when_done) override {
        (void)s;
        ptr<std::exception> except(nullptr);
        bool ret = true;
        when_done(ret, except);
    }

    ulong get_committed() const { return last_committed_idx_.load(); }

private:
    std::atomic<ulong> last_committed_idx_;
};

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        ++g_checks;                                             \
        if (!(cond)) {                                          \
            ++g_fails;                                          \
            std::printf("  [FAIL] %s (line %d)\n", msg, __LINE__); \
        } else {                                                \
            std::printf("  [ OK ] %s\n", msg);                  \
        }                                                       \
    } while (0)

static void wait_until(std::function<bool()> pred, int timeout_ms) {
    auto deadline = std::chrono::steady_clock::now()
                    + std::chrono::milliseconds(timeout_ms);
    while (std::chrono::steady_clock::now() < deadline) {
        if (pred()) return;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
}

static raft_params make_params() {
    raft_params params;
    params.heart_beat_interval_ = 100;
    params.election_timeout_lower_bound_ = 300;
    params.election_timeout_upper_bound_ = 500;
    params.leadership_expiry_ = 500;
    params.reserved_log_items_ = 5;
    params.snapshot_distance_ = 0;   // 禁用 snapshot，纯内存验证
    params.client_req_timeout_ = 3000;
    params.return_method_ = raft_params::async_handler;
    return params;
}

int main() {
    std::printf("=== nuraft 3.0.0 HarmonyOS smoke test ===\n");

    const int num_nodes = 3;
    std::vector<std::string> endpoints = {
        "127.0.0.1:21000",
        "127.0.0.1:21001",
        "127.0.0.1:21002",
    };
    std::vector<ptr<test_state_machine>> sms(num_nodes);
    std::vector<ptr<inmem_state_mgr>> mgrs(num_nodes);
    std::vector<raft_launcher> launchers(num_nodes);
    std::vector<ptr<raft_server>> servers(num_nodes);

    // ---- 启动 3 个节点（初始各自为单节点集群） ----
    for (int i = 0; i < num_nodes; ++i) {
        sms[i] = cs_new<test_state_machine>();
        mgrs[i] = cs_new<inmem_state_mgr>(i + 1, endpoints[i]);
        raft_params params = make_params();
        int port = 21000 + i;
        asio_service::options asio_opt;
        servers[i] = launchers[i].init(sms[i], mgrs[i], nullptr, port, asio_opt, params);
        if (!servers[i]) {
            std::printf("  [FAIL] node %d launcher.init failed\n", i + 1);
            return 1;
        }
    }
    wait_until([&]() {
        return servers[0]->is_initialized() && servers[1]->is_initialized()
               && servers[2]->is_initialized();
    }, 8000);
    CHECK(servers[0]->is_initialized() && servers[1]->is_initialized()
          && servers[2]->is_initialized(), "3 节点均已初始化");

    // ---- 单节点阶段：节点 1 自动当选 leader ----
    wait_until([&]() { return servers[0]->is_leader(); }, 8000);
    CHECK(servers[0]->is_leader(), "节点 1 初始选举为 leader");

    // ---- 扩展集群：add_srv 加入节点 2、节点 3 ----
    ptr<srv_config> cfg2 = mgrs[1]->get_srv_config();
    ptr<cmd_result<ptr<buffer>>> add_ret2 = servers[0]->add_srv(*cfg2);
    CHECK(add_ret2.get() != nullptr, "add_srv(节点2) 返回非空结果");
    wait_until([&]() {
        return servers[0]->get_config()->get_servers().size() >= 2;
    }, 8000);
    CHECK(servers[0]->get_config()->get_servers().size() >= 2, "节点 2 加入集群");

    ptr<srv_config> cfg3 = mgrs[2]->get_srv_config();
    ptr<cmd_result<ptr<buffer>>> add_ret3 = servers[0]->add_srv(*cfg3);
    CHECK(add_ret3.get() != nullptr, "add_srv(节点3) 返回非空结果");
    wait_until([&]() {
        return servers[0]->get_config()->get_servers().size() >= 3;
    }, 8000);
    CHECK(servers[0]->get_config()->get_servers().size() >= 3, "节点 3 加入集群");

    // ---- 3 节点稳定：撤销单节点 leader 状态后重新选举（leader 不变则保持） ----
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    bool leader_found = false;
    int leader_id = -1;
    for (int i = 0; i < num_nodes; ++i) {
        if (servers[i]->is_leader()) {
            leader_found = true;
            leader_id = i;
            break;
        }
    }
    CHECK(leader_found, "3 节点集群存在 leader");

    // ---- leader 追加一条日志 ----
    std::string msg = "hello-nuraft-3.0.0";
    ptr<buffer> log = buffer::alloc(sizeof(int) + msg.size());
    buffer_serializer bs(log);
    bs.put_str(msg);

    // 记录追加前 committed index。
    // 注意：两次 add_srv 的配置条目本身是日志（index 2、3），且已提交，
    // 因此追加前的 committed index 可能已 >= 3 —— 断言必须基于"追加前后递增"，
    // 不能写死固定阈值（否则为恒真空断言）。
    ulong before_committed = servers[leader_id]->get_committed_log_idx();
    std::printf("  [INFO] before append: leader committed=%lu\n",
                (unsigned long)before_committed);

    ptr<cmd_result<ptr<buffer>>> append_ret =
        servers[leader_id]->append_entries({log});
    CHECK(append_ret.get() != nullptr, "append_entries 返回非空结果");

    // ---- 等待 commit index 超过追加前值（数据日志复制成功） ----
    wait_until([&]() {
        return servers[leader_id]->get_committed_log_idx() > before_committed;
    }, 10000);
    wait_until([&]() {
        bool ok = true;
        for (int i = 0; i < num_nodes; ++i) {
            if (servers[i]->get_committed_log_idx() <= before_committed) ok = false;
        }
        return ok;
    }, 10000);

    ulong leader_committed = servers[leader_id]->get_committed_log_idx();
    CHECK(leader_committed > before_committed, "leader commit index 在追加后前进");
    for (int i = 0; i < num_nodes; ++i) {
        std::printf("  [INFO] node %d committed=%lu\n", i + 1,
                    (unsigned long)servers[i]->get_committed_log_idx());
        CHECK(servers[i]->get_committed_log_idx() > before_committed,
              "全部节点已提交追加的日志");
    }

    // ---- 收尾 ----
    for (int i = 0; i < num_nodes; ++i) {
        launchers[i].shutdown();
    }

    std::printf("=== smoke test: %d checks, %d failed ===\n", g_checks, g_fails);
    return g_fails == 0 ? 0 : 1;
}