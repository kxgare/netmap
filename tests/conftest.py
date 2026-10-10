from dataclasses import replace
import pytest
from netmap.core.models import Connection, Location


@pytest.fixture
def connection():
    return Connection(123,"browser.exe","C:/Browser/browser.exe",10.0,"TCP","192.168.1.2",51000,
                      "8.8.8.8",443,"ESTABLISHED","2026-10-10T10:00:00.000+00:00",
                      Location("США","",37.751,-97.822,1000))
