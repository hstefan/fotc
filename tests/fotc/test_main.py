#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import fotc.main as fm
import fotc.util


def test_parse_command_args():
    cmd_id, args = fotc.util.parse_command_args('/foo "does a nice" bar')
    assert cmd_id == "foo"
    assert len(args) == 2


def test_memegen_str():
    out = fotc.util.memegen_str('a string with spaces')
    assert out == "a_string_with_spaces"
    empty = fotc.util.memegen_str('')
    assert empty == '_'