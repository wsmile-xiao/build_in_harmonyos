// test_package/test.cpp — vmime 0.9.2 smoke test
// Verifies: messageBuilder construction, header generation, body text,
//           MIME serialization, re-parse via component::parse(),
//           and header field round-trip.

#include <iostream>
#include <string>
#include <cstdlib>

#include "vmime/vmime.hpp"
#include "vmime/platforms/posix/posixHandler.hpp"

static int g_failures = 0;

#define CHECK(cond) do { \
	if (!(cond)) { \
		std::cerr << "FAIL: " << #cond << " (line " << __LINE__ << ")" << std::endl; \
		++g_failures; \
	} \
} while (0)

int main()
{
	vmime::platform::setHandler<vmime::platforms::posix::posixHandler>();

	try
	{
		// 1. Build a message with messageBuilder
		vmime::messageBuilder mb;
		mb.setExpeditor(vmime::mailbox("sender@harmonyos.test"));

		vmime::addressList to;
		to.appendAddress(vmime::make_shared<vmime::mailbox>("rcpt@harmonyos.test"));
		mb.setRecipients(to);

		mb.setSubject(vmime::text("vmime OHOS port test"));

		mb.getTextPart()->setText(
			vmime::make_shared<vmime::stringContentHandler>(
				"Hello from HarmonyOS aarch64."));

		vmime::shared_ptr<vmime::message> msg = mb.construct();

		// 2. Serialize to string
		std::string raw;
		vmime::utility::outputStreamStringAdapter out(raw);
		msg->generate(out);

		CHECK(raw.find("From: sender@harmonyos.test") != std::string::npos);
		CHECK(raw.find("To: rcpt@harmonyos.test") != std::string::npos);
		CHECK(raw.find("Subject: vmime OHOS port test") != std::string::npos);
		CHECK(raw.find("Hello from HarmonyOS aarch64.") != std::string::npos);

		// 3. Re-parse the serialized message
		vmime::shared_ptr<vmime::message> reparsed = vmime::make_shared<vmime::message>();
		reparsed->parse(raw);

		// 4. Verify header fields survived round-trip
		vmime::shared_ptr<const vmime::header> hdr = reparsed->getHeader();
		vmime::shared_ptr<const vmime::mailbox> fromFld = hdr->findFieldValue<vmime::mailbox>(vmime::fields::FROM);
		vmime::shared_ptr<const vmime::text> subjFld = hdr->findFieldValue<vmime::text>(vmime::fields::SUBJECT);

		CHECK(fromFld.get() != NULL);
		if (fromFld)
		{
			CHECK(fromFld->getEmail().toString() == "sender@harmonyos.test");
		}
		CHECK(subjFld.get() != NULL);
		if (subjFld)
		{
			std::string subj;
			vmime::utility::outputStreamStringAdapter subjOut(subj);
			subjFld->generate(subjOut);
			CHECK(subj == "vmime OHOS port test");
		}

		// 5. Verify body text via messageParser
		vmime::shared_ptr<vmime::messageParser> mp =
			vmime::make_shared<vmime::messageParser>(reparsed);
		CHECK(mp->getTextPartCount() >= 1);

		if (mp->getTextPartCount() >= 1)
		{
			const vmime::textPart& tp = *mp->getTextPartAt(0);
			std::string body;
			vmime::utility::outputStreamStringAdapter bodyOut(body);
			tp.getText()->extract(bodyOut);
			CHECK(body.find("Hello from HarmonyOS aarch64.") != std::string::npos);
		}

		if (g_failures == 0)
			std::cout << "vmime test_package: ALL CHECKS PASSED" << std::endl;
		else
			std::cout << "vmime test_package: " << g_failures << " FAILURES" << std::endl;
	}
	catch (vmime::exception& e)
	{
		std::cerr << "vmime exception: " << e.what() << std::endl;
		return 1;
	}
	catch (std::exception& e)
	{
		std::cerr << "std exception: " << e.what() << std::endl;
		return 1;
	}

	return (g_failures == 0) ? 0 : 1;
}
