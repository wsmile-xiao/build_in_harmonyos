#include <QtRemoteObjects/QRemoteObjectNode>

int main()
{
    QRemoteObjectNode node;
    node.setHeartbeatInterval(1500);
    if (node.heartbeatInterval() != 1500) {
        return 1;
    }
    return node.lastError() == QRemoteObjectNode::NoError ? 0 : 2;
}
