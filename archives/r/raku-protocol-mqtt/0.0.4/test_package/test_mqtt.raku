use v6.d;
use Protocol::MQTT:ver<0.0.4> :qos;

sub hex(Blob:D $bytes --> Str:D) {
    $bytes.list.map({ .fmt('%02x') }).join;
}

my $connect = Protocol::MQTT::Packet::Connect.new(
    client-identifier => 'atomcode-client',
    keep-alive-interval => 30,
    clean-start => True,
);
my $connect-wire = $connect.encode;
say "connect-wire={hex($connect-wire)}";

my $publish = Protocol::MQTT::Packet::Publish.new(
    topic => 'sensors/temp',
    payload => '23.5'.encode,
    qos => At-least-once,
    packet-id => 42,
);
my $publish-wire = $publish.encode;
say "publish-wire={hex($publish-wire)}";

my $buffer = Protocol::MQTT::PacketBuffer.new;
$buffer.add-data($publish-wire);
my $decoded = $buffer.get-packet;
say "decoded-type={$decoded.^name}";
say "decoded-topic={$decoded.topic}";
say "decoded-packet-id={$decoded.packet-id}";
say "decoded-payload={$decoded.payload.decode}";

my $filter = Protocol::MQTT::Filter.new(topic => 'sensors/+/status');
say "filter-match={$filter.ACCEPTS('sensors/kitchen/status') ?? 'yes' !! 'no'}";
say "filter-reject={$filter.ACCEPTS('sensors/status') ?? 'no' !! 'yes'}";

my $malformed = Protocol::MQTT::PacketBuffer.new;
$malformed.add-data(buf8.new(0x30, 0x80, 0x80, 0x80, 0x80, 0x00));
my $length-status = 'accepted';
try {
    $malformed.has-packet;
    CATCH {
        when Protocol::MQTT::Error::InvalidValue { $length-status = 'rejected' }
    }
}
say "oversize-length={$length-status}";
say "mqtt-consumer=ok";
