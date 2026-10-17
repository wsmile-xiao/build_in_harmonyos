// ns-3 3.48 HarmonyOS PC 冒烟测试：
// 构建 2 节点 point-to-point 点对点链路，从节点0发一个 100 字节数据包，
// 断言节点1 实际收到 1 个包（事件循环真实推进），失败非 0 退出。
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <iostream>

using namespace ns3;

static uint32_t g_rxCount = 0;

static bool RxTrace(Ptr<NetDevice> device, Ptr<const Packet> packet,
                    uint16_t protocol, const Address &address) {
  g_rxCount++;
  return true;
}

int main(int argc, char *argv[]) {
  CommandLine cmd;
  cmd.Parse(argc, argv);

  NodeContainer nodes;
  nodes.Create(2);

  PointToPointHelper p2p;
  p2p.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
  p2p.SetChannelAttribute("Delay", StringValue("2ms"));

  NetDeviceContainer devices = p2p.Install(nodes);
  devices.Get(1)->SetReceiveCallback(MakeCallback(&RxTrace));

  Ptr<Packet> packet = Create<Packet>(100);
  devices.Get(0)->Send(packet, devices.Get(1)->GetAddress(), 0);

  Simulator::Stop(Seconds(1.0));
  Simulator::Run();
  Simulator::Destroy();

  if (g_rxCount != 1) {
    std::cerr << "FAIL: expected 1 received packet, got " << g_rxCount
              << std::endl;
    return 1;
  }
  std::cout << "ns-3 smoke OK: 2-node point-to-point link delivered 1 packet ("
            << packet->GetSize() << " bytes)" << std::endl;
  return 0;
}
