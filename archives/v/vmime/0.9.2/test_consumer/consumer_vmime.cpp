// test_consumer/consumer_vmime.cpp — vmime 0.9.2 消费者端到端用例
//
// 模拟业务上层组件仅通过 vmime 公开 C++ API（已安装的 Conan 包导出的
// find_package(vmime) cmake 目标）使用该库，验证：
//
//   C1  构造含二进制附件的 MIME 消息 → 序列化 → 写入文件（TMPDIR）
//   C2  从磁盘文件重新读取并解析，核查发件人/收件人/主题
//   C3  提取附件内容，逐字节校验往返一致
//
// 本程序仅使用 vmime 公开头文件与已安装的静态库，不包含任何库内部符号
// 或内部构建目录引用。

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

#include "vmime/vmime.hpp"
#include "vmime/platforms/posix/posixHandler.hpp"

static int g_failures = 0;

#define CHECK(cond)                                              \
	do {                                                         \
		if (!(cond)) {                                           \
			std::cerr << "FAIL: " << #cond << " (line "          \
				  << __LINE__ << ")" << std::endl;               \
			++g_failures;                                        \
		}                                                        \
	} while (0)

int main()
{
	vmime::platform::setHandler<vmime::platforms::posix::posixHandler>();

	const char* tmpdir = std::getenv("TMPDIR");
	if (!tmpdir || !*tmpdir) {
		std::cerr << "TMPDIR not set — consumer must run with writable temp dir\n";
		return 1;
	}

	try {
		// ── C1: Build message with binary attachment, serialize, write file ──
		vmime::messageBuilder mb;
		mb.setExpeditor(vmime::mailbox("consumer@example.com"));

		vmime::addressList to;
		to.appendAddress(vmime::make_shared<vmime::mailbox>("recipient@example.com"));
		mb.setRecipients(to);

		mb.setSubject(vmime::text("OHOS consumer E2E test"));

		mb.getTextPart()->setText(
			vmime::make_shared<vmime::stringContentHandler>("Consumer body text."));

		// Binary attachment (small PNG-like payload) base64 encoded
		static const unsigned char payload[] = {
			0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
			0xAA, 0xBB, 0xCC, 0xDD, 0x00, 0x01, 0x02, 0x03,
		};
		const vmime::string attData(reinterpret_cast<const char*>(payload),
		                            sizeof(payload));
		vmime::shared_ptr<vmime::contentHandler> attCth =
			vmime::make_shared<vmime::stringContentHandler>(attData);

		vmime::shared_ptr<vmime::attachment> att =
			vmime::make_shared<vmime::defaultAttachment>(
				attCth,
				vmime::mediaType("application/octet-stream"),
				vmime::text("consumer test attachment"),
				vmime::word("consumer-test.bin"));

		mb.appendAttachment(att);

		// Serialize to string
		vmime::shared_ptr<vmime::message> msg = mb.construct();
		std::string serialized;
		vmime::utility::outputStreamStringAdapter strOut(serialized);
		msg->generate(strOut);

		CHECK(serialized.find("consumer@example.com") != std::string::npos);
		CHECK(serialized.find("OHOS consumer E2E test") != std::string::npos);
		CHECK(serialized.find("Consumer body text.") != std::string::npos);
		// Attachment filename appears in Content-Disposition
		CHECK(serialized.find("consumer-test.bin") != std::string::npos);

		// Write to disk via TMPDIR
		std::string fpath = std::string(tmpdir) + "/vmime_consumer_"
			+ std::to_string(std::rand()) + ".eml";
		{
			vmime::shared_ptr<vmime::utility::fileSystemFactory> fsf =
				vmime::platform::getHandler()->getFileSystemFactory();
			vmime::shared_ptr<vmime::utility::file> outFile =
				fsf->create(fsf->stringToPath(fpath));
			outFile->createFile();
			outFile->getFileWriter()->getOutputStream()->write(
				serialized.data(), serialized.size());
		}

		std::cout << "C1: build message + attachment, serialize, write file PASS\n";

		// ── C2: Read back and re-parse ──
		vmime::shared_ptr<vmime::utility::fileSystemFactory> fsf2 =
			vmime::platform::getHandler()->getFileSystemFactory();
		vmime::shared_ptr<vmime::utility::file> inFile =
			fsf2->create(fsf2->stringToPath(fpath));
		vmime::shared_ptr<vmime::utility::inputStream> is =
			inFile->getFileReader()->getInputStream();

		// Read entire file into memory
		std::string fileContent;
		vmime::byte_t buf[4096];
		while (!is->eof()) {
			const vmime::size_t n = is->read(buf, sizeof(buf));
			fileContent.append(reinterpret_cast<const char*>(buf), n);
		}

		vmime::shared_ptr<vmime::message> parsed = vmime::make_shared<vmime::message>();
		parsed->parse(fileContent);

		vmime::messageParser mp(parsed);

		// Verify headers
		vmime::shared_ptr<const vmime::header> hdr = parsed->getHeader();
		vmime::shared_ptr<const vmime::mailbox> fromFld =
			hdr->findFieldValue<vmime::mailbox>(vmime::fields::FROM);
		CHECK(fromFld.get() != NULL
		      && fromFld->getEmail().toString() == "consumer@example.com");

		vmime::shared_ptr<const vmime::text> subjFld =
			hdr->findFieldValue<vmime::text>(vmime::fields::SUBJECT);
		CHECK(subjFld.get() != NULL);

		std::string subjStr;
		vmime::utility::outputStreamStringAdapter subjOut(subjStr);
		subjFld->generate(subjOut);
		CHECK(subjStr == "OHOS consumer E2E test");

		std::cout << "C2: parse from disk, verify headers PASS\n";

		// ── C3: Extract attachment, compare byte-exact ──
		CHECK(mp.getAttachmentCount() >= 1);

		if (mp.getAttachmentCount() >= 1) {
			vmime::shared_ptr<const vmime::attachment> rAtt =
				mp.getAttachmentAt(0);

			// Verify filename
			const vmime::word& rName = rAtt->getName();
			std::string rNameStr;
			vmime::utility::outputStreamStringAdapter rnOut(rNameStr);
			rName.generate(rnOut);
			CHECK(rNameStr == "consumer-test.bin");

			// Extract and compare data
			vmime::shared_ptr<const vmime::contentHandler> rCth = rAtt->getData();
			std::string extracted;
			vmime::utility::outputStreamStringAdapter exOut(extracted);
			rCth->extract(exOut);

			const std::string expected(reinterpret_cast<const char*>(payload),
			                           sizeof(payload));
			CHECK(extracted == expected);
		}

		std::cout << "C3: attachment filename + content round-trip PASS\n";

		// Clean up
		std::remove(fpath.c_str());
	}
	catch (vmime::exception& e) {
		std::cerr << "vmime exception: " << e.what() << std::endl;
		return 1;
	}
	catch (std::exception& e) {
		std::cerr << "std exception: " << e.what() << std::endl;
		return 1;
	}

	if (g_failures == 0) {
		std::cout << "CONSUMER_USE_CASE_ALL_PASS" << std::endl;
		return 0;
	}
	std::cerr << g_failures << " consumer checks FAILED" << std::endl;
	return 1;
}