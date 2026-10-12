project('libspiel-consumer', 'c', default_options: ['c_std=gnu11'])

spiel = dependency('spiel-1.0', required: true)
consumer = executable('consumer', 'consumer.c', dependencies: spiel)

foreach case_name : [
  'version',
  'utterance-text',
  'utterance-language',
  'utterance-defaults',
  'utterance-numeric',
  'utterance-ssml',
  'voice-metadata',
  'voice-format',
  'voice-identity',
  'utterance-voice',
]
  test('consumer-' + case_name, consumer, args: ['-p', '/spiel/' + case_name])
endforeach
