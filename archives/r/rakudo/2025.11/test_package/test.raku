use v6.d;

my @qos = 0, 1, 2;
say "qos-sum={@qos.sum}";
my %packet = topic => "sensors/temp", retain => True;
say "topic={%packet<topic>}";
say "retain={%packet<retain> ?? 'yes' !! 'no'}";
my $encoded = "MQTT ✓".encode("utf8");
say "utf8-bytes={$encoded.elems}";
say "utf8-roundtrip={$encoded.decode('utf8')}";
class Packet {
    has Str $.topic;
    has Int $.qos;
    method label() { "{$!topic}:{$!qos}" }
}
my $packet = Packet.new(topic => "events", qos => 2);
say "class={$packet.label}";
say "raku-smoke=ok";
