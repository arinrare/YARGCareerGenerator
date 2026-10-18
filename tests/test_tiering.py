from yarg_career_builder.core.tiering import redistribute


def test_redistribute_exact_total():
    assert redistribute([5, 10, 5], 20) == [5, 10, 5]


def test_redistribute_proportional_scale():
    result = redistribute([5, 10, 5], 80)
    assert sum(result) == 80
    # proportions roughly preserved (4x)
    assert result[1] == 40
    assert result[0] + result[2] == 40


def test_redistribute_zero_total():
    assert redistribute([5, 10], 0) == [0, 0]


def test_redistribute_zero_weights():
    assert redistribute([0, 0], 10) == [0, 0]


def test_redistribute_rounds_without_loss():
    weights = [5, 10, 5, 5, 10, 5, 5, 10, 5, 5, 10, 5]
    result = redistribute(weights, 80)
    assert sum(result) == 80
    assert all(n >= 0 for n in result)
