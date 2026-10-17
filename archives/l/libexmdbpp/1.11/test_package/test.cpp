// test_package/test.cpp — libexmdbpp 1.11 consumer test suite (OpenHarmony aarch64)
//
// Upstream ships **no test suite** at all: the release tarball has no tests/
// directory, no enable_testing()/add_test() in CMakeLists.txt and therefore
// nothing `make check` or `ctest -N` could enumerate (upstream N = 0, see
// test_package/MANIFEST.yml).
//
// This binary is a **real consumer** of the installed package: it locates the
// library through `find_package(libexmdbpp)`, links `libexmdbpp::libexmdbpp`
// and drives it exactly the way an application would. It runs 7 test cases,
// each following the same shape:
//
//     construct input → execute for real → produce output → verify content
//
// Three of them are full end-to-end cases over a **real TCP socket**: an exmdb
// server simulator is started inside the test process, ExmdbClient performs a
// real connect() plus the ConnectRequest handshake, sends a business request,
// the simulator parses the wire bytes it actually received and answers with a
// response frame, and the client deserializes the result which is then verified.
//
// ⚠ The CI profile uses build_type=Release → **-DNDEBUG** is added to the
// compile flags, which turns <cassert>'s assert() into a no-op (the test would
// silently become a shell that always returns 0). Assertions therefore use the
// custom CHECK macro below — a plain `if` statement, immune to NDEBUG.

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include <errno.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include <exmdbpp/ExmdbClient.h>
#include <exmdbpp/IOBuffer.h>
#include <exmdbpp/IOBufferImpl.h> // Serialize<T> definitions used to build response frames
#include <exmdbpp/constants.h>
#include <exmdbpp/exceptions.h>
#include <exmdbpp/requests.h>
#include <exmdbpp/structures.h>
#include <exmdbpp/util.h>

static int g_cases = 0;
static int g_failedCases = 0;
static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond)                                                                    \
	do {                                                                               \
		++g_checks;                                                                    \
		if(!(cond)) {                                                                  \
			std::printf("    CHECK FAILED at %s:%d: %s\n", __FILE__, __LINE__, #cond); \
			++g_failures;                                                              \
		}                                                                              \
	} while(0)

static void runCase(const char* name, const std::function<void()>& body)
{
	++g_cases;
	const int failuresBefore = g_failures;
	const int checksBefore = g_checks;
	try {
		body();
	} catch(const std::exception& err) {
		std::printf("    EXCEPTION: %s\n", err.what());
		++g_failures;
	} catch(...) {
		std::printf("    UNKNOWN EXCEPTION\n");
		++g_failures;
	}
	const bool ok = (g_failures == failuresBefore);
	if(!ok)
		++g_failedCases;
	std::printf("  [%s] %s (%d checks)\n", ok? "PASS" : "FAIL", name, g_checks - checksBefore);
}

namespace
{

// constants::* are *namespaces* of static constants, and a using-declaration
// may not name a namespace — alias them instead.
namespace CallId = exmdbpp::constants::CallId;
namespace PropvalType = exmdbpp::constants::PropvalType;
namespace ResponseCode = exmdbpp::constants::ResponseCode;

bool littleEndian()
{
	const uint16_t probe = 0x0001;
	return *reinterpret_cast<const uint8_t*>(&probe) == 0x01;
}

uint32_t rd32le(const uint8_t* p)
{
	return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

void wr32le(uint8_t* p, uint32_t v)
{
	p[0] = uint8_t(v);
	p[1] = uint8_t(v >> 8);
	p[2] = uint8_t(v >> 16);
	p[3] = uint8_t(v >> 24);
}

/// Read a NUL-terminated string out of a request payload, returning the offset after it.
std::string readCstr(const std::vector<uint8_t>& data, size_t offset, size_t& end)
{
	std::string out;
	for(size_t i = offset; i < data.size() && data[i] != 0; ++i)
		out.push_back(char(data[i]));
	end = offset + out.size() + 1;
	return out;
}

///////////////////////////////////////////////////////////////////////////////
// exmdb server simulator — speaks the real exmdb wire protocol over loopback
///////////////////////////////////////////////////////////////////////////////

/**
 * Minimal stand-in for gromox' exmdb_provider.
 *
 * Frame layout (as implemented by the library):
 *   request  : [len:uint32 LE][callId:uint8][payload…]   (len excludes the header)
 *   response : [status:uint8][len:uint32 LE][payload…]
 *
 * The simulator records every request frame it received, so a test case can
 * verify what the client actually put on the wire.
 */
class MiniExmdbServer
{
public:
	MiniExmdbServer() : listenFd(::socket(AF_INET, SOCK_STREAM, 0))
	{
		if(listenFd < 0)
			throw std::runtime_error("simulator: socket() failed");
		int one = 1;
		::setsockopt(listenFd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
		sockaddr_in addr{};
		addr.sin_family = AF_INET;
		addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
		addr.sin_port = 0; // let the kernel pick a free port
		if(::bind(listenFd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0)
			throw std::runtime_error("simulator: bind() failed");
		sockaddr_in bound{};
		socklen_t boundLen = sizeof(bound);
		if(::getsockname(listenFd, reinterpret_cast<sockaddr*>(&bound), &boundLen) < 0)
			throw std::runtime_error("simulator: getsockname() failed");
		port = ntohs(bound.sin_port);
		if(::listen(listenFd, 8) < 0)
			throw std::runtime_error("simulator: listen() failed");
		worker = std::thread([this] { serve(); });
	}

	~MiniExmdbServer()
	{
		stop.store(true);
		if(listenFd >= 0) {
			::shutdown(listenFd, SHUT_RDWR);
			::close(listenFd);
			listenFd = -1;
		}
		if(worker.joinable())
			worker.join();
	}

	MiniExmdbServer(const MiniExmdbServer&) = delete;
	MiniExmdbServer& operator=(const MiniExmdbServer&) = delete;

	uint16_t port = 0;

	/// Snapshot of every request frame received so far (thread-safe).
	std::vector<std::vector<uint8_t>> snapshot() const
	{
		std::lock_guard<std::mutex> lock(mutex);
		return observed;
	}

private:
	static bool readAll(int fd, void* dst, size_t n)
	{
		auto* out = static_cast<uint8_t*>(dst);
		size_t done = 0;
		while(done < n) {
			ssize_t got = ::recv(fd, out + done, n - done, 0);
			if(got < 0 && errno == EINTR)
				continue;
			if(got <= 0)
				return false;
			done += size_t(got);
		}
		return true;
	}

	static bool writeAll(int fd, const void* src, size_t n)
	{
		const auto* in = static_cast<const uint8_t*>(src);
		size_t done = 0;
		while(done < n) {
			ssize_t sent = ::send(fd, in + done, n - done, MSG_NOSIGNAL);
			if(sent < 0 && errno == EINTR)
				continue;
			if(sent <= 0)
				return false;
			done += size_t(sent);
		}
		return true;
	}

	void sendFrame(int fd, uint8_t status, const std::vector<uint8_t>& payload)
	{
		std::vector<uint8_t> frame;
		frame.reserve(5 + payload.size());
		frame.push_back(status);
		uint8_t lenBuf[4];
		wr32le(lenBuf, uint32_t(payload.size()));
		frame.insert(frame.end(), lenBuf, lenBuf + 4);
		frame.insert(frame.end(), payload.begin(), payload.end());
		writeAll(fd, frame.data(), frame.size());
	}

	/// GET_STORE_PROPERTIES → two propvals (PT_LONG 4242, PT_STRING8 "Inbox")
	static std::vector<uint8_t> propvalPayload()
	{
		exmdbpp::IOBuffer buff;
		buff.push<uint16_t>(uint16_t(2));
		buff.push<uint32_t>(uint32_t(0x0FFF0003u));
		buff.push<uint32_t>(uint32_t(4242));
		buff.push<uint32_t>(uint32_t(0x0FFF001Eu));
		buff.push<std::string>("Inbox");
		return std::vector<uint8_t>(buff.begin(), buff.end());
	}

	/// GET_STORE_ALL_PROPTAGS → three proptags
	static std::vector<uint8_t> proptagPayload()
	{
		exmdbpp::IOBuffer buff;
		buff.push<uint16_t>(uint16_t(3));
		buff.push<uint32_t>(uint32_t(0x0FFF0003u));
		buff.push<uint32_t>(uint32_t(0x0E080003u));
		buff.push<uint32_t>(uint32_t(0x3001001Eu));
		return std::vector<uint8_t>(buff.begin(), buff.end());
	}

	void serve()
	{
		while(!stop.load()) {
			int conn = ::accept(listenFd, nullptr, nullptr);
			if(conn < 0)
				break;
			handle(conn);
			::close(conn);
		}
	}

	void handle(int conn)
	{
		int storePropsSeen = 0;
		while(!stop.load()) {
			uint8_t header[4];
			if(!readAll(conn, header, 4))
				return; // client closed the connection
			const uint32_t length = rd32le(header);
			std::vector<uint8_t> payload(length);
			if(length > 0 && !readAll(conn, payload.data(), length))
				return;
			{
				std::lock_guard<std::mutex> lock(mutex);
				observed.push_back(payload);
			}
			const uint8_t callId = payload.empty()? 0xFF : payload[0];
			uint8_t status = ResponseCode::SUCCESS;
			std::vector<uint8_t> response;
			if(callId == CallId::CONNECT) {
				// handshake — the library maps this to an empty response
			} else if(callId == CallId::GET_STORE_PROPERTIES) {
				// first call succeeds, the second one exercises the error path
				if(++storePropsSeen > 1)
					status = ResponseCode::MISCONFIG_PREFIX;
				else
					response = propvalPayload();
			} else if(callId == CallId::GET_STORE_ALL_PROPTAGS) {
				response = proptagPayload();
			} else {
				status = ResponseCode::PULL_ERROR;
			}
			sendFrame(conn, status, response);
		}
	}

	int listenFd = -1;
	std::atomic<bool> stop{false};
	std::thread worker;
	mutable std::mutex mutex;
	std::vector<std::vector<uint8_t>> observed;
};

///////////////////////////////////////////////////////////////////////////////
// End-to-end consumer cases (real socket round trips)
///////////////////////////////////////////////////////////////////////////////

/**
 * Case 1 — full RPC round trip over a real TCP connection.
 *
 * construct: exmdb server simulator + connection parameters + property tags
 * execute  : ExmdbClient::connect() (sends ConnectRequest) and then
 *            send<GetStorePropertiesRequest>() over the live socket
 * produce  : the simulator parses the wire bytes and answers with a
 *            PropvalResponse, which the client deserializes
 * verify   : the parsed propvals, plus what the server saw on the wire
 */
void caseEndToEndGetStoreProperties()
{
	MiniExmdbServer server;
	const std::string homedir = "/var/lib/gromox/domain/example.com/u/user";
	const std::vector<uint32_t> proptags{0x0FFF0003u, 0x0E080003u};

	// --- execute ---
	exmdbpp::ExmdbClient client("127.0.0.1", std::to_string(server.port), homedir, true);
	const auto response = client.send<exmdbpp::requests::GetStorePropertiesRequest>(
	    homedir, uint32_t(65001), exmdbpp::Collection<uint16_t, uint32_t>(proptags));

	// --- verify the deserialized result ---
	CHECK(response.propvals.size() == 2);
	CHECK(response.propvals.at(0).tag == 0x0FFF0003u);
	CHECK(response.propvals.at(0).type == PropvalType::LONG);
	CHECK(response.propvals.at(0).toString() == "4242");
	CHECK(response.propvals.at(1).tag == 0x0FFF001Eu);
	CHECK(response.propvals.at(1).type == PropvalType::STRING);
	CHECK(response.propvals.at(1).toString() == "Inbox");

	// --- verify what actually went over the wire ---
	const auto seen = server.snapshot();
	CHECK(seen.size() == 2); // ConnectRequest + GetStorePropertiesRequest
	CHECK(seen.at(0).at(0) == CallId::CONNECT);
	CHECK(seen.at(1).at(0) == CallId::GET_STORE_PROPERTIES);
	const std::vector<uint8_t>& request = seen.at(1);
	size_t cursor = 1;
	CHECK(readCstr(request, cursor, cursor) == homedir);
	CHECK(rd32le(request.data() + cursor) == 65001u); // cpid
	cursor += 4;
	const uint16_t tagCount = uint16_t(request.at(cursor)) | uint16_t(request.at(cursor + 1) << 8);
	CHECK(tagCount == 2);
	cursor += 2;
	CHECK(rd32le(request.data() + cursor) == proptags[0]);
	CHECK(rd32le(request.data() + cursor + 4) == proptags[1]);
}

/**
 * Case 2 — a server-side failure is propagated as a typed protocol exception.
 *
 * construct: the already established connection + the same request
 * execute  : a second GetStorePropertiesRequest, which the simulator answers
 *            with status MISCONFIG_PREFIX
 * produce  : the library raises ExmdbProtocolError
 * verify   : the exception type and its response code
 */
void caseEndToEndProtocolError()
{
	MiniExmdbServer server;
	const std::string homedir = "/var/lib/gromox/domain/example.com/u/user";
	const std::vector<uint32_t> proptags{0x0FFF0003u};

	exmdbpp::ExmdbClient client("127.0.0.1", std::to_string(server.port), homedir, true);
	// first call takes the happy path inside the simulator
	client.send<exmdbpp::requests::GetStorePropertiesRequest>(
	    homedir, uint32_t(65001), exmdbpp::Collection<uint16_t, uint32_t>(proptags));

	bool threw = false;
	uint8_t code = 0xFF;
	try {
		client.send<exmdbpp::requests::GetStorePropertiesRequest>(
		    homedir, uint32_t(65001), exmdbpp::Collection<uint16_t, uint32_t>(proptags));
	} catch(const exmdbpp::ExmdbProtocolError& err) {
		threw = true;
		code = err.code;
	}

	CHECK(threw);
	CHECK(code == ResponseCode::MISCONFIG_PREFIX);
}

/**
 * Case 3 — a second RPC on a fresh connection, returning a proptag list.
 *
 * construct: new connection to the simulator + homedir
 * execute  : send<GetAllStorePropertiesRequest>()
 * produce  : ProptagResponse deserialized from the response frame
 * verify   : the returned proptag list
 */
void caseEndToEndGetAllStoreProperties()
{
	MiniExmdbServer server;
	const std::string homedir = "/var/lib/gromox/domain/example.com/u/user";

	exmdbpp::ExmdbClient client("127.0.0.1", std::to_string(server.port), homedir, false);
	const auto response = client.send<exmdbpp::requests::GetAllStorePropertiesRequest>(homedir);

	CHECK(response.proptags.size() == 3);
	CHECK(response.proptags.at(0) == 0x0FFF0003u);
	CHECK(response.proptags.at(1) == 0x0E080003u);
	CHECK(response.proptags.at(2) == 0x3001001Eu);

	const auto seen = server.snapshot();
	CHECK(seen.size() == 2);
	CHECK(seen.at(1).at(0) == CallId::GET_STORE_ALL_PROPTAGS);
}

///////////////////////////////////////////////////////////////////////////////
// API-level consumer cases (construct → execute → produce → verify)
///////////////////////////////////////////////////////////////////////////////

/// exmdbpp::util — GC value / eid / timestamp helpers
void caseUtilConversions()
{
	using namespace exmdbpp::util;

	// Low 48 bits are kept and byte-swapped to big endian inside valueToGc().
	const uint64_t value = 0xAABBCCDDULL;
	CHECK(gcToValue(valueToGc(value)) == (value << 16));

	// The replica id is stored in the low 16 bits on little endian machines;
	// on a big endian host the GC value is not shifted up instead.
	const uint64_t eid = makeEid(0x0001, 0xABCDE0ULL);
	CHECK(eid == (littleEndian()? 0xABCDE00001ULL : 0xABCDE1ULL));
	CHECK(makeEidEx(0x0001, 0x00000042ULL) == makeEid(0x0001, valueToGc(0x00000042ULL)));

	// FILETIME (Windows NT epoch, 100 ns units) <-> UNIX time_t round trip.
	const time_t stamp = 1700000000L;
	CHECK(nxTime(ntTime(stamp)) == stamp);
	CHECK(ntTime(0) == 116444736000000000ULL);
}

/// exmdbpp::structures::TaggedPropval — tagged property values
void caseTaggedPropval()
{
	using exmdbpp::structures::TaggedPropval;

	const TaggedPropval number(0x0FFF0003u, uint32_t(4242)); // PT_LONG
	CHECK(number.tag == 0x0FFF0003u);
	CHECK(number.type == PropvalType::LONG);
	CHECK(number.count() == 1);
	CHECK(std::string(number.typeName()) == "LONG");
	CHECK(number.toString() == "4242");

	const TaggedPropval text(0x0FFF001Eu, std::string("Inbox")); // PT_STRING8
	CHECK(text.type == PropvalType::STRING);
	CHECK(text.count() == 1);
	CHECK(std::string(text.typeName()) == "STRING");
	CHECK(text.toString() == "Inbox");

	// Copy construction deep-copies the managed string buffer.
	const TaggedPropval copy(text);
	CHECK(copy.tag == text.tag);
	CHECK(copy.toString() == "Inbox");
	CHECK(std::string(copy.typeName()) == "STRING");

	const TaggedPropval flag(0x0FFF000Bu, uint8_t(1)); // PT_BOOLEAN
	CHECK(flag.type == PropvalType::BYTE);
	CHECK(std::string(flag.typeName()) == "BYTE");
	CHECK(flag.toString() == "1");
}

/// exmdbpp::structures::Restriction — filter serialization used by table loading
void caseRestrictionSerialization()
{
	using exmdbpp::structures::Restriction;

	const Restriction empty;
	CHECK(!bool(empty)); // XNULL restriction is falsy

	const Restriction res = Restriction::EXIST(0x0FFF0003u);
	CHECK(bool(res));

	exmdbpp::IOBuffer buff;
	res.serialize(buff);
	// 1 byte restriction type (0x08 = EXIST) + 4 bytes little endian proptag
	CHECK(buff.size() == 5);
	CHECK(buff[0] == 0x08);
	CHECK(buff[1] == 0x03);
	CHECK(buff[2] == 0x00);
	CHECK(buff[3] == 0xFF);
	CHECK(buff[4] == 0x0F);
}

/// exmdbpp::requests — request serialization consumed by ExmdbClient::send()
void caseRequestSerialization()
{
	using exmdbpp::Collection;
	using exmdbpp::requests::GetStorePropertiesRequest;

	const std::string homedir = "/var/lib/gromox/domain/example.com/u/user";
	const std::vector<uint32_t> proptags{0x0FFF0003u, 0x0E080003u};

	exmdbpp::IOBuffer buff;
	GetStorePropertiesRequest::write(buff, homedir, uint32_t(65001),
	                                Collection<uint16_t, uint32_t>(proptags));

	// callId(1) + homedir + '\0' + cpid(4) + count(2) + proptags(2 * 4)
	const size_t expected = 1 + homedir.size() + 1 + 4 + 2 + proptags.size()*sizeof(uint32_t);
	CHECK(buff.size() == expected);
	CHECK(buff[0] == GetStorePropertiesRequest::callId);
	CHECK(GetStorePropertiesRequest::callId == CallId::GET_STORE_PROPERTIES);
	CHECK(std::string(reinterpret_cast<const char*>(buff.data())+1, homedir.size()) == homedir);
}

} // namespace

int main()
{
	std::printf("test_libexmdbpp — consumer test suite for libexmdbpp 1.11\n");

	runCase("e2e-1 GET_STORE_PROPERTIES over a real TCP connection", caseEndToEndGetStoreProperties);
	runCase("e2e-2 protocol error propagated as ExmdbProtocolError", caseEndToEndProtocolError);
	runCase("e2e-3 GET_STORE_ALL_PROPTAGS over a fresh connection", caseEndToEndGetAllStoreProperties);
	runCase("util: gc value / eid / filetime conversions", caseUtilConversions);
	runCase("structures: TaggedPropval", caseTaggedPropval);
	runCase("structures: Restriction serialization", caseRestrictionSerialization);
	runCase("requests: GetStorePropertiesRequest serialization", caseRequestSerialization);

	std::printf("test_libexmdbpp: %d cases, %d failed (%d checks, %d failures)\n",
	            g_cases, g_failedCases, g_checks, g_failures);
	return (g_failedCases == 0 && g_failures == 0)? 0 : 1;
}
