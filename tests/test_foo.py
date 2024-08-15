from pyvcell.foo import foo


def test_foo() -> None:
    assert foo("foo") == "foo"
