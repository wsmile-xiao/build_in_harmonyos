cmake_minimum_required(VERSION 3.5)
project(smtpping_consumer_test C)

# Mock SMTP server used by test.sh to drive the packaged smtpping binary
# through a complete SMTP transaction over loopback.
add_executable(mock_smtp_server mock_smtp_server.c)
