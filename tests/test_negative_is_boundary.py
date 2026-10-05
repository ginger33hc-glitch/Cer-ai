import pytest

from clinical_core.rules import signed_i_s_category


@pytest.mark.parametrize("value", [-2.4999, -2.49, -1.14, -0.98, -0.90, -0.5001, -0.50, 0, 0.50])
def test_signed_normal_interval(value):
    assert signed_i_s_category(value) == "NORMAL_SYMMETRIC"


@pytest.mark.parametrize("value", [-2.50, -2.5001, -3.0, -5.0, 0.5001, 1.0])
def test_signed_asymmetric_bowtie_intervals(value):
    assert signed_i_s_category(value) == "ASYMMETRIC_BOWTIE"


@pytest.mark.parametrize("value", [1.0001, 1.01, 1.39, 1.3999])
def test_positive_inferior_steepening_is_preserved(value):
    assert signed_i_s_category(value) == "INFERIOR_STEEPENING_SRA"


@pytest.mark.parametrize("value", [1.40, 1.50, 3.0])
def test_positive_ectatic_boundary_is_inclusive(value):
    assert signed_i_s_category(value) == "ABNORMAL_ECTATIC"
