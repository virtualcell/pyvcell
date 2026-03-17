import numexpr  # type: ignore[import-untyped]
from numpy import ndarray

from pyvcell._internal.simdata.python_infix import get_numexpr_expression


def test_vcell_infix_to_num_expr_infix() -> None:
    vcell_infix = "id_1 * csc(id_0 ^ 2.2)"
    value = get_numexpr_expression(vcell_infix)
    assert value == "(id_1 * (1.0/sin(((id_0)**(2.2)))))"


def test_bad_vcell_infix() -> None:
    vcellInfix = "id_1 / + / /-  cos(/ / /) id_2"
    try:
        get_numexpr_expression(vcellInfix)
    except ValueError:
        return
    raise AssertionError("Should have raised ValueError")


def test_if_else_in_expression() -> None:
    vcell_infix = "(id_2 && id_3) * 1.2"
    value = get_numexpr_expression(vcell_infix)
    assert value == "(where(((0.0!=id_2) & (0.0!=id_3)), 1.2, 0.0))"
    result: ndarray = ndarray(1)
    result = numexpr.evaluate(value, {"id_2": 2.2, "id_3": 3.3, "float": float, bool: bool}, out=result)
    assert result == 1.2

