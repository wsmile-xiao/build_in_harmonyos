project('libspeechprovider-consumer-test', 'c')

speech_provider = dependency('speech-provider-1.0', version: '>=1.0.3')
iface_xml = speech_provider.get_variable('iface_xml')
assert(import('fs').is_file(iface_xml), 'speech-provider interface XML is missing')
consumer = executable('test_libspeechprovider', 'test.c', dependencies: speech_provider)
test('libspeechprovider-public-api', consumer)
