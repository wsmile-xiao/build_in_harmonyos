#include <cstdint>
#include <iostream>
#include <memory>
#include <utility>
#include <vector>

#include <arrow/api.h>
#include <arrow/flight/api.h>
#include <arrow/flight/sql/api.h>

// Test Arrow Flight RPC API on OHOS
// This test verifies:
// 1. Arrow core API works (array builder)
// 2. Flight Location can be constructed (gRPC address building)
// 3. A real Flight server can be started on an ephemeral localhost port
// 4. A Flight client can connect and a ListFlights round-trip succeeds over
//    localhost gRPC (proves the whole gRPC transport stack works on OHOS)
// 5. Flight SQL client wrapper can be constructed (arrow_flight_sql linked)

namespace af = arrow::flight;

// A minimal Flight server that serves one flight from an in-memory table
class EchoTestServer : public af::FlightServerBase {
 public:
  arrow::Status ListFlights(const af::ServerCallContext&,
                            const af::Criteria*,
                            std::unique_ptr<af::FlightListing>* listing) override {
    auto info_result = MakeFlightInfo();
    if (!info_result.ok()) {
      return info_result.status();
    }
    std::vector<af::FlightInfo> flights;
    flights.push_back(std::move(info_result).ValueOrDie());
    *listing = std::make_unique<af::SimpleFlightListing>(std::move(flights));
    return arrow::Status::OK();
  }

 private:
  arrow::Result<af::FlightInfo> MakeFlightInfo() {
    std::shared_ptr<arrow::Schema> schema =
        arrow::schema({arrow::field("values", arrow::int64())});
    af::FlightEndpoint endpoint;
    endpoint.ticket = af::Ticket{"echo-ticket"};
    endpoint.locations.push_back(af::Location::ForGrpcTcp("127.0.0.1", 0).ValueOrDie());
    return af::FlightInfo::Make(*schema, af::FlightDescriptor::Path({"echo"}), {endpoint},
                                /*total_records=*/5, /*total_bytes=*/40,
                                /*ordered=*/false);
  }
};

int main(int, char**) {
    // 1. Arrow core sanity
    arrow::Int64Builder builder(arrow::default_memory_pool());
    auto status = builder.AppendValues({1, 2, 3, 4, 5});
    if (!status.ok()) {
        std::cerr << "Failed to append values: " << status.message() << std::endl;
        return EXIT_FAILURE;
    }
    std::shared_ptr<arrow::Array> array;
    status = builder.Finish(&array);
    if (!status.ok()) {
        std::cerr << "Failed to finish array: " << status.message() << std::endl;
        return EXIT_FAILURE;
    }

    // 2. Flight Location (gRPC address parsing — proves grpc is linked & usable)
    auto location_result = af::Location::ForGrpcTcp("127.0.0.1", 31337);
    if (!location_result.ok()) {
        std::cerr << "Location::ForGrpcTcp failed: "
                  << location_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    af::Location location = *location_result;

    // 3. Start a real Flight server on an ephemeral localhost port.
    //    (Upstream's MakeServer pattern: Init() starts the gRPC listener;
    //    Serve() would block waiting for shutdown - upstream tests don't
    //    call it either.)
    af::FlightServerOptions server_options(location);
    EchoTestServer server;
    status = server.Init(server_options);
    if (!status.ok()) {
        std::cerr << "FlightServerBase::Init failed: " << status.message() << std::endl;
        return EXIT_FAILURE;
    }

    // Connect to the actual bound port (Init may bind an ephemeral port)
    std::string uri = "grpc+tcp://127.0.0.1:" + std::to_string(server.port());
    auto real_location_result = af::Location::Parse(uri);
    if (!real_location_result.ok()) {
        std::cerr << "Location::Parse failed: "
                  << real_location_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    af::Location real_location = *real_location_result;

    // 4. Client round-trip over localhost gRPC (full Flight RPC stack)
    auto client_result = af::FlightClient::Connect(real_location);
    if (!client_result.ok()) {
        std::cerr << "FlightClient::Connect failed: "
                  << client_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    std::unique_ptr<af::FlightClient> client = std::move(client_result).ValueOrDie();

    auto listing_result = client->ListFlights();
    if (!listing_result.ok()) {
        std::cerr << "ListFlights failed: " << listing_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    auto listing = std::move(listing_result).ValueOrDie();

    int n_flights = 0;
    while (true) {
        auto flight_result = listing->Next();
        if (!flight_result.ok()) {
            std::cerr << "listing->Next failed: " << flight_result.status().message() << std::endl;
            return EXIT_FAILURE;
        }
        auto flight = std::move(flight_result).ValueOrDie();
        if (!flight) break;  // end of listing
        ++n_flights;
    }
    if (n_flights != 1) {
        std::cerr << "Expected 1 flight from server, got " << n_flights << std::endl;
        return EXIT_FAILURE;
    }

    // 4b. Flight SQL client wrapper (proves arrow_flight_sql is linked)
    //     FlightSqlClient takes a shared_ptr<FlightClient>
    std::shared_ptr<af::FlightClient> client_shared(std::move(client));
    arrow::flight::sql::FlightSqlClient sql_client(client_shared);

    // 6. Shut down the server
    status = server.Shutdown();
    if (!status.ok()) {
        std::cerr << "Shutdown failed: " << status.message() << std::endl;
        return EXIT_FAILURE;
    }

    std::cout << "libarrow_flight test_package PASSED: "
              << "core=ok location=ok server=ok client=ok list_flights=" << n_flights
              << " sql_client=ok shutdown=ok" << std::endl;
    return EXIT_SUCCESS;
}
