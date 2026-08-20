my $sum := 20 + 22;
say("arithmetic=$sum");
my $text := "mqtt" ~ "-nqp";
say("string=$text");
my @values := nqp::list(3, 5, 8);
say("array-elems=" ~ nqp::elems(@values));
say("array-value=" ~ nqp::atpos(@values, 2));
my %values := nqp::hash("protocol", "mqtt", "qos", 2);
say("hash-value=" ~ nqp::atkey(%values, "protocol"));
say("hash-exists=" ~ nqp::existskey(%values, "qos"));
class Counter {
    has $!value;
    method set($value) { $!value := $value; }
    method value() { $!value; }
}
my $counter := nqp::create(Counter);
$counter.set(7);
say("class-value=" ~ $counter.value());
say("nqp-smoke=ok");
