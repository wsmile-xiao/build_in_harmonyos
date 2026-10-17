/*
 * test_package — sobjectizer 5.7.4 static-link consumer.
 *
 * Links sobjectizer::StaticLib (the exported name of upstream's libso_s.a) via
 * Conan's CMakeDeps files, independently of the shared-library consumer.
 *
 * Purpose: prove the recipe's SOBJECTIZER_BUILD_STATIC=ON product is genuinely
 * usable by a downstream project. The static build compiles in a different
 * configuration (SO_5_STATIC_LIB is defined PUBLIC on the static target), so a
 * link/ABI problem here would not be caught by the shared-library test.
 *
 * It runs a full env -> coop -> agent -> message -> stop cycle and finally
 * reports the framework version.
 *
 * IMPORTANT: agents created by coop.make_agent<T>() are owned by the
 * cooperation and destroyed when so_5::launch() returns. Reading an agent's
 * members through a raw pointer afterwards is a use-after-free and silently
 * yields zeros, so the received-message counter lives in main()'s frame and the
 * agent writes to it through a reference.
 */
#include <so_5/all.hpp>

#include <iostream>

namespace {

struct msg_probe final : public so_5::signal_t {};

class a_probe_t final : public so_5::agent_t
{
public:
	a_probe_t(context_t ctx, int & received)
		: so_5::agent_t{ std::move(ctx) }
		, m_received{ received }
	{}

	// Subscriptions must be installed in so_define_agent(): it runs during
	// agent registration, before so_evt_start(). Subscribing in the
	// constructor (which runs inside make_agent<>, before registration) means
	// the subscription never takes effect and messages are dropped.
	void so_define_agent() override
	{
		so_subscribe_self().event([this](mhood_t<msg_probe>) {
			++m_received;
			so_environment().stop();
		});
	}

	void so_evt_start() override
	{
		so_5::send<msg_probe>(so_direct_mbox());
	}

private:
	int & m_received;
};

} /* anonymous namespace */

int main()
{
	std::cout << "=== sobjectizer static-link consumer ===" << std::endl;

	int received = 0;

	so_5::launch([&](so_5::environment_t & env) {
		env.introduce_coop([&](so_5::coop_t & coop) {
			coop.make_agent<a_probe_t>(std::ref(received));
		});
	});

	// SO_5_VERSION 是【数值】宏：SO_5_VERSION_MAKE(major, minor, patch)。
	// 注意上游的版本号方案与压缩包名不同：v.5.7.4 这个 tar 包对应的框架
	// 版本是 7.4.0（major=7, minor=4, patch=0），见 dev/so_5/version.hpp。
	const bool version_ok =
			SO_5_VERSION == SO_5_VERSION_MAKE(7, 4, 0);
	const bool roundtrip_ok = (received == 1);
	const bool api_level_ok =
			SO_5_VERSION >= SO_5_VERSION_MAKE(7, 0, 0);

	std::cout << "  SO_5_VERSION_MAJOR=" << SO_5_VERSION_MAJOR
			<< " MINOR=" << SO_5_VERSION_MINOR
			<< " PATCH=" << SO_5_VERSION_PATCH << std::endl;
	std::cout << "  received=" << received << std::endl;
	std::cout << "  version_ok=" << (version_ok ? "true" : "false")
			<< " roundtrip_ok=" << (roundtrip_ok ? "true" : "false")
			<< " api_level_ok=" << (api_level_ok ? "true" : "false")
			<< std::endl;

	std::cout << "HMBS_TEST_STATIC_RESULT={\"version_ok\":"
			<< (version_ok ? "true" : "false") << ",\"roundtrip_ok\":"
			<< (roundtrip_ok ? "true" : "false") << ",\"api_level_ok\":"
			<< (api_level_ok ? "true" : "false")
			<< ",\"received\":" << received << "}" << std::endl;

	return (version_ok && roundtrip_ok && api_level_ok) ? 0 : 1;
}
