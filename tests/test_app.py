from nsp_grok.app import main
from nsp_grok.nsp_api import NspApiError, UserCancelled


def test_main_ctrl_c_returns_130(monkeypatch):
    monkeypatch.setattr(
        "nsp_grok.app._main",
        lambda argv=None: (_ for _ in ()).throw(UserCancelled("Cancelado con Ctrl-C.")),
    )
    assert main([]) == 130


def test_main_keyboard_interrupt_returns_130(monkeypatch):
    monkeypatch.setattr(
        "nsp_grok.app._main",
        lambda argv=None: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert main([]) == 130


def test_main_nsp_error_returns_1(monkeypatch):
    monkeypatch.setattr(
        "nsp_grok.app._main",
        lambda argv=None: (_ for _ in ()).throw(NspApiError("timeout de 60s")),
    )
    assert main([]) == 1


def test_main_unexpected_returns_1(monkeypatch):
    monkeypatch.setattr(
        "nsp_grok.app._main",
        lambda argv=None: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert main([]) == 1
