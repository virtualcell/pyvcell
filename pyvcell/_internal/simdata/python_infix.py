def get_numexpr_expression(vcell_expression: str) -> str:
    # libvcell (the `native` extra) is imported lazily so that importing the data
    # models / VCML reader does not require it.
    from libvcell import vcell_infix_to_num_expr_infix

    # First, get the string from vcell
    translation_result: bool
    result_message: str
    num_expr_expression: str
    translation_result, result_message, num_expr_expression = vcell_infix_to_num_expr_infix(vcell_expression)
    if not translation_result:
        raise ValueError(
            result_message if result_message is not None else "Unable to convert expression: " + vcell_expression
        )
    # NumExpr has a restricted set of what's allowed, in order to protect `eval`
    sanitized_expression: str = (
        num_expr_expression.lstrip(" ")
        .rstrip(" ")
        .replace(" and ", " & ")
        .replace(" or ", " | ")
        .replace(" not ", " ~")
        .replace("math.", "")
    )
    return sanitized_expression
