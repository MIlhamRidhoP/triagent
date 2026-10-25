import os
import socket

import pytest


def test_offline_flag_is_set():
    assert os.environ["TRIAGENT_OFFLINE"] == "1"


def test_sockets_are_blocked():
    with pytest.raises(RuntimeError, match="blocked"):
        socket.create_connection(("example.com", 80))
