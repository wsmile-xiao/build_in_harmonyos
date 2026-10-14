"""Parse full SWH XML into the original XML::Parser Tree representation.

Keep element order, attributes (including DTD defaults), and coalesced character
data, including CDATA. The original Perl generator remains responsible for C.
Only the release's local DTD may be loaded; no network/entity fallback is used.
"""
from pathlib import Path
from xml.parsers import expat


def parse_tree(filename):
    filename = Path(filename).resolve(strict=True)
    result, stack = [], []
    parser = expat.ParserCreate()

    def start(name, attrs):
        body = [attrs]
        (stack[-1] if stack else result).extend((name, body))
        stack.append(body)

    def characters(text):
        if not stack or not text:
            return
        body = stack[-1]
        if len(body) > 1 and body[-2] == 0:
            body[-1] += text
        else:
            body.extend((0, text))

    def external(context, base, system, public):
        if system != 'ladspa-swh.dtd' or public is not None:
            raise ValueError('Unexpected external XML entity: ' + str(system))
        dtd = filename.parent / system
        if dtd.is_symlink() or dtd.resolve().parent != filename.parent:
            raise ValueError('DTD must remain in release source directory')
        child = parser.ExternalEntityParserCreate(context)
        child.ExternalEntityRefHandler = external
        with dtd.open('rb') as stream:
            child.ParseFile(stream)
        return 1

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: stack.pop()
    parser.CharacterDataHandler = characters
    parser.ExternalEntityRefHandler = external
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_ALWAYS)
    with filename.open('rb') as stream:
        parser.ParseFile(stream)
    if stack or len(result) != 2 or result[0] != 'ladspa':
        raise ValueError('Expected exactly one ladspa root')
    return [result]
