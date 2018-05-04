import re
from typing import Text, Optional, Tuple, List


def parse_command_args(text: Text) -> Optional[Tuple[Text, List[Text]]]:
    """
    Parses command text, returning id and args.

    `/foo bar baz` => (foo, [bar, baz])
    `/foo "bar" "baz"` => (foo, [bar, baz])
    `/foo "a long string" baz` => (foo, [a long string, baz])
    """
    cmd_re = re.compile(r'/(\w*)@?\w*\s*(.*)$')
    arg_re = re.compile(r'([^"]\S*|".+?")\s*')

    if not cmd_re.match(text):
        return None

    cmd = cmd_re.search(text).groups()
    cmd_id = cmd[0].strip('"')
    if len(cmd) == 2:
        args = arg_re.findall(cmd[1])
        return cmd_id, [x.strip('"') for x in args]
    else:
        return cmd_id, []


def memegen_str(text: Text) -> Text:
    if not text:
        return '_'
    return text.replace(' ', '_')