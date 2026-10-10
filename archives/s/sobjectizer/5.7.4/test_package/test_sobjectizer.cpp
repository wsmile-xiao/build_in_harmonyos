// ---------------------------------------------------------------------------
// test_sobjectizer.cpp -- consumer end-to-end test for the packaged
// sobjectizer/5.7.4 (HarmonyOS PC, aarch64).
//
// This is the "shared library" layer: the program is built by Conan's CMakeDeps
// generator and links sobjectizer::SharedLib, i.e. it exercises exactly what a
// downstream HarmonyOS application would get from find_package(sobjectizer).
//
// Three parts, all driven through real library APIs:
//   Part 1  version/ABI sanity (SO_5_VERSION* macros)
//   Part 2  environment lifecycle: launch -> introduce_coop -> make_agent ->
//           direct mbox -> immediate message -> delayed message through the
//           real timer thread -> graceful stop
//   Part 3  ping/pong round-trip over ONE real mbox for 1000 exchanges, the
//           canonical SObjectizer usage pattern (cf. upstream
//           dev/sample/so_5/ping_pong). This is the rule-12 consumer
//           end-to-end case.
//
// IMPORTANT design note (root cause of an earlier false failure):
//   Agents created with coop.make_agent<T>() are OWNED BY THE COOPERATION and
//   are destroyed when so_5::launch() returns. Holding a raw pointer to an
//   agent and reading its members after launch() is a use-after-free and
//   silently yields zeros. Therefore every counter below lives in main()'s
//   frame and the agents only write to it through a reference. The agents are
//   deliberately not referenced after launch() returns.
// ---------------------------------------------------------------------------

#include <so_5/all.hpp>

#include <chrono>
#include <iostream>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, const char * what)
{
	++g_checks;
	if (ok)
		std::cout << "  [ OK ] " << what << std::endl;
	else
	{
		++g_failed;
		std::cout << "  [FAIL] " << what << std::endl;
	}
}

// ---------------------------------------------------------------------------
// Part 2: environment lifecycle.
// Counters are owned by main(); the agent writes through a reference.
// ---------------------------------------------------------------------------
struct lifecycle_counters_t
{
	int immediate{ 0 };
	int delayed{ 0 };
};

struct msg_immediate final : public so_5::signal_t {};
struct msg_delayed final : public so_5::signal_t {};

class a_lifecycle_t final : public so_5::agent_t
{
public:
	a_lifecycle_t(context_t ctx, lifecycle_counters_t & counters)
		: so_5::agent_t{ std::move(ctx) }
		, m_counters{ counters }
	{}

	// Subscriptions must be installed in so_define_agent(): it is called
	// during the agent registration process, before so_evt_start(). Putting
	// them in the constructor (which runs inside coop.make_agent<>(), i.e.
	// before registration) means they never take effect and every message is
	// dropped.
	void so_define_agent() override
	{
		so_subscribe_self().event([this](mhood_t<msg_immediate>) {
			++m_counters.immediate;
		});

		so_subscribe_self().event([this](mhood_t<msg_delayed>) {
			++m_counters.delayed;
			so_environment().stop();
		});
	}

	// At this point all agents are defined, so the subscriptions exist.
	void so_evt_start() override
	{
		so_5::send<msg_immediate>(so_direct_mbox());
		so_5::send_delayed<msg_delayed>(
				*this, std::chrono::milliseconds(50));
	}

private:
	lifecycle_counters_t & m_counters;
};

// ---------------------------------------------------------------------------
// Part 3 (rule 12): the canonical ping/pong round-trip. Both agents subscribe
// to the SAME mbox; every exchange is a real message dispatched by the runtime.
// ---------------------------------------------------------------------------
struct msg_ping final : public so_5::signal_t {};
struct msg_pong final : public so_5::signal_t {};

struct pingpong_counters_t
{
	unsigned int pongs{ 0 };
	unsigned int pings{ 0 };
};

class a_pinger_t final : public so_5::agent_t
{
public:
	a_pinger_t(context_t ctx, so_5::mbox_t mbox, unsigned int pings_left,
			pingpong_counters_t & counters)
		: so_5::agent_t{ std::move(ctx) }
		, m_mbox{ std::move(mbox) }
		, m_pings_left{ pings_left }
		, m_counters{ counters }
	{}

	// See the note in a_lifecycle_t: subscriptions belong in so_define_agent().
	void so_define_agent() override
	{
		so_subscribe(m_mbox).event([this](mhood_t<msg_pong>) {
			++m_counters.pongs;
			if (m_pings_left)
				--m_pings_left;
			if (m_pings_left)
				so_5::send<msg_ping>(m_mbox);
			else
				so_environment().stop();
		});
	}

	void so_evt_start() override
	{
		so_5::send<msg_ping>(m_mbox);
	}

private:
	const so_5::mbox_t m_mbox;
	unsigned int m_pings_left;
	pingpong_counters_t & m_counters;
};

class a_ponger_t final : public so_5::agent_t
{
public:
	a_ponger_t(context_t ctx, so_5::mbox_t mbox, pingpong_counters_t & counters)
		: so_5::agent_t{ std::move(ctx) }
		, m_mbox{ std::move(mbox) }
		, m_counters{ counters }
	{}

	void so_define_agent() override
	{
		so_subscribe(m_mbox).event([this](mhood_t<msg_ping>) {
			++m_counters.pings;
			so_5::send<msg_pong>(m_mbox);
		});
	}

private:
	const so_5::mbox_t m_mbox;
	pingpong_counters_t & m_counters;
};

} /* anonymous namespace */

int main()
{
	std::cout << "=== sobjectizer consumer test (CMakeDeps layer) ===" << std::endl;

	// ---------------------------------------------------------------- Part 1
	std::cout << "[Part 1] version sanity" << std::endl;
	std::cout << "  SO_5_VERSION_MAJOR=" << SO_5_VERSION_MAJOR
			<< " MINOR=" << SO_5_VERSION_MINOR
			<< " PATCH=" << SO_5_VERSION_PATCH << std::endl;
	// SO_5_VERSION is a *numeric* macro: SO_5_VERSION_MAKE(major, minor, patch).
	// The v.5.7.4 tarball ships framework version 7.4.0 (dev/so_5/version.hpp),
	// so it must never be compared against the string "5.7.4".
	check(SO_5_VERSION == SO_5_VERSION_MAKE(7, 4, 0),
			"SO_5_VERSION == SO_5_VERSION_MAKE(7, 4, 0)");
	check(SO_5_VERSION_MAJOR == 7, "SO_5_VERSION_MAJOR == 7");
	check(SO_5_VERSION_MINOR == 4, "SO_5_VERSION_MINOR == 4");
	check(SO_5_VERSION_PATCH == 0, "SO_5_VERSION_PATCH == 0");
	check(SO_5_VERSION >= SO_5_VERSION_MAKE(7, 0, 0),
			"SO_5_VERSION >= SO_5_VERSION_MAKE(7, 0, 0)");

	// ---------------------------------------------------------------- Part 2
	std::cout << "[Part 2] environment lifecycle + direct mbox + real timer"
			<< std::endl;
	{
		lifecycle_counters_t counters;

		so_5::launch(
			[&](so_5::environment_t & env) {
				env.introduce_coop([&](so_5::coop_t & coop) {
					coop.make_agent<a_lifecycle_t>(std::ref(counters));
				});
			});

		std::cout << "  immediate=" << counters.immediate
				<< " delayed=" << counters.delayed << std::endl;
		check(counters.immediate == 1, "immediate messages delivered == 1");
		check(counters.delayed == 1,
				"delayed message delivered via real timer == 1");
	}

	// ---------------------------------------------------------------- Part 3
	std::cout << "[Part 3] ping/pong round-trip over a real mbox (rule 12 e2e)"
			<< std::endl;
	{
		const unsigned int kRequests = 1000;
		pingpong_counters_t counters;

		so_5::launch(
			[&](so_5::environment_t & env) {
				env.introduce_coop(
					so_5::disp::active_obj::make_dispatcher(env).binder(),
					[&](so_5::coop_t & coop) {
						auto mbox = env.create_mbox();
						coop.make_agent<a_pinger_t>(
								mbox, kRequests, std::ref(counters));
						coop.make_agent<a_ponger_t>(
								mbox, std::ref(counters));
					});
			});

		std::cout << "  pongs_seen=" << counters.pongs
				<< " pings_seen=" << counters.pings << std::endl;
		check(counters.pongs == kRequests,
				"pinger received 1000 pongs over the real mbox");
		check(counters.pings == kRequests,
				"ponger received 1000 pings over the real mbox");
	}

	std::cout << "--- summary ---" << std::endl;
	std::cout << "checks=" << g_checks << " failed=" << g_failed << std::endl;
	std::cout << "HMBS_TEST_PACKAGE_RESULT={\"checks\":" << g_checks
			<< ",\"failed\":" << g_failed << "}" << std::endl;

	return g_failed == 0 ? 0 : 1;
}
