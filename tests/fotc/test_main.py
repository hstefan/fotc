#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import fotc.main as fm


def test_parse_command_args():
    cmd_id, args = fm._parse_command_args('/foo "does a nice" bar')
    assert cmd_id == "foo"
    assert len(args) == 2


def test_memegen_str():
    out = fm._memegen_str('a string with spaces')
    assert out == "a_string_with_spaces"
    empty =fm._memegen_str('')
    assert empty == '_'