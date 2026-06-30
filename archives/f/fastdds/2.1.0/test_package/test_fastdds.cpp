// test_fastdds.cpp - Functional test for Fast-DDS v2.1.0 on OHOS
// Tests: Participant creation, Type registration, Topic, Publisher/Subscriber, cleanup
#include <fastdds/dds/domain/DomainParticipantFactory.hpp>
#include <fastdds/dds/domain/DomainParticipant.hpp>
#include <fastdds/dds/topic/Topic.hpp>
#include <fastdds/dds/topic/TypeSupport.hpp>
#include <fastdds/dds/topic/TopicDataType.hpp>
#include <fastdds/dds/publisher/Publisher.hpp>
#include <fastdds/dds/subscriber/Subscriber.hpp>
#include <fastrtps/rtps/common/SerializedPayload.h>
#include <fastrtps/rtps/common/InstanceHandle.h>
#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <cstdint>

using namespace eprosima::fastdds::dds;
using eprosima::fastrtps::rtps::SerializedPayload_t;
using eprosima::fastrtps::rtps::InstanceHandle_t;

// ---- Test framework ----
static int g_tests_run = 0;
static int g_tests_passed = 0;
static std::vector<std::string> g_failures;

#define TEST(cond, name) \
    do { \
        g_tests_run++; \
        if (cond) { \
            g_tests_passed++; \
            std::cout << "  [PASS] " << name << std::endl; \
        } else { \
            g_failures.push_back(name); \
            std::cout << "  [FAIL] " << name << std::endl; \
        } \
    } while(0)

// ---- Simple data type for testing ----
class HelloWorldType : public TopicDataType
{
public:
    HelloWorldType()
    {
        setName("HelloWorld");
    }

    bool serialize(
            void* data,
            SerializedPayload_t* payload) override
    {
        (void)data; (void)payload;
        return true;
    }

    bool deserialize(
            SerializedPayload_t* payload,
            void* data) override
    {
        (void)payload; (void)data;
        return true;
    }

    std::function<uint32_t()> getSerializedSizeProvider(
            void* data) override
    {
        (void)data;
        return []() -> uint32_t { return 4; };
    }

    void* createData() override
    {
        return new int(0);
    }

    void deleteData(
            void* data) override
    {
        delete static_cast<int*>(data);
    }

    bool getKey(
            void* data,
            InstanceHandle_t* handle,
            bool force_md5 = false) override
    {
        (void)data; (void)handle; (void)force_md5;
        return false;
    }
};

int main()
{
    std::cout << "========================================" << std::endl;
    std::cout << "Fast-DDS v2.1.0 Functional Test on OHOS" << std::endl;
    std::cout << "Platform: aarch64 (HarmonyOS)" << std::endl;
    std::cout << "Compiler: Clang 15.0.4" << std::endl;
    std::cout << "Build:   Static (libfastrtps.a)" << std::endl;
    std::cout << "Date:    2026-06-29" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;

    // ---- Test 1: DomainParticipantFactory singleton ----
    std::cout << "[Test 1] DomainParticipantFactory" << std::endl;
    DomainParticipantFactory* factory = DomainParticipantFactory::get_instance();
    TEST(factory != nullptr, "Factory singleton not null");

    // ---- Test 2: Create DomainParticipant ----
    std::cout << "[Test 2] DomainParticipant creation" << std::endl;
    DomainParticipant* participant =
        factory->create_participant(0, PARTICIPANT_QOS_DEFAULT);
    TEST(participant != nullptr, "Participant created on domain 0");

    if (!participant) {
        std::cerr << "FATAL: Cannot proceed without participant" << std::endl;
    } else
    {

    // ---- Test 3: Register type ----
    std::cout << "[Test 3] Type registration" << std::endl;
    {
        TypeSupport type(new HelloWorldType());
        ReturnCode_t ret = participant->register_type(type);
        TEST(ret == ReturnCode_t::RETCODE_OK, "HelloWorld type registered");
    }

    // ---- Test 4: Create Topic ----
    std::cout << "[Test 4] Topic creation" << std::endl;
    Topic* topic = participant->create_topic(
        "HelloWorldTopic", "HelloWorld", TOPIC_QOS_DEFAULT);
    TEST(topic != nullptr, "Topic 'HelloWorldTopic' created");

    // ---- Test 5: Create Publisher ----
    std::cout << "[Test 5] Publisher creation" << std::endl;
    Publisher* publisher =
        participant->create_publisher(PUBLISHER_QOS_DEFAULT);
    TEST(publisher != nullptr, "Publisher created");

    // ---- Test 6: Create Subscriber ----
    std::cout << "[Test 6] Subscriber creation" << std::endl;
    Subscriber* subscriber =
        participant->create_subscriber(SUBSCRIBER_QOS_DEFAULT);
    TEST(subscriber != nullptr, "Subscriber created");

    // ---- Test 7: Cleanup Publisher/Subscriber ----
    std::cout << "[Test 7] Cleanup Publisher/Subscriber" << std::endl;
    {
        bool cleanup_ok = true;
        if (publisher) {
            cleanup_ok &= (participant->delete_publisher(publisher) == ReturnCode_t::RETCODE_OK);
        }
        if (subscriber) {
            cleanup_ok &= (participant->delete_subscriber(subscriber) == ReturnCode_t::RETCODE_OK);
        }
        TEST(cleanup_ok, "Publisher/Subscriber deleted");
    }

    // ---- Test 8: Cleanup Topic ----
    std::cout << "[Test 8] Cleanup Topic" << std::endl;
    {
        bool topic_ok = true;
        if (topic) {
            topic_ok = (participant->delete_topic(topic) == ReturnCode_t::RETCODE_OK);
        }
        TEST(topic_ok, "Topic deleted");
    }

    // ---- Test 9: Delete Participant ----
    std::cout << "[Test 9] Participant deletion" << std::endl;
    {
        bool del_ok = (factory->delete_participant(participant) == ReturnCode_t::RETCODE_OK);
        TEST(del_ok, "Participant deleted successfully");
    }

    // ---- Test 10: Memory leak check (simplified) ----
    std::cout << "[Test 10] Second participant (memory sanity)" << std::endl;
    {
        DomainParticipant* p2 = factory->create_participant(1, PARTICIPANT_QOS_DEFAULT);
        bool ok = (p2 != nullptr);
        if (p2) {
            ok &= (factory->delete_participant(p2) == ReturnCode_t::RETCODE_OK);
        }
        TEST(ok, "Second participant created and deleted on domain 1");
    }
    } // end else (participant != nullptr)

summary:
    // ---- Summary ----
    std::cout << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Test Summary" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Total:  " << g_tests_run << std::endl;
    std::cout << "Passed: " << g_tests_passed << std::endl;
    std::cout << "Failed: " << (g_tests_run - g_tests_passed) << std::endl;
    if (!g_failures.empty()) {
        std::cout << "Failed tests:" << std::endl;
        for (const auto& f : g_failures) {
            std::cout << "  - " << f << std::endl;
        }
    }
    std::cout << "========================================" << std::endl;

    return (g_tests_run == g_tests_passed) ? 0 : 1;
}
