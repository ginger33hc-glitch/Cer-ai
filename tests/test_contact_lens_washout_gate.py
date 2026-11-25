"""Retired contact-lens questionnaire cannot gate measured analysis."""
import pytest
from canonical_readiness import evaluate_precore_readiness


@pytest.mark.parametrize('modifiers', [None, {},
    {'contact_lens_type': 'UNKNOWN'},
    {'contact_lens_type': 'SOFT'},
    {'contact_lens_type': 'SOFT', 'contact_lens_discontinuation_days': 9},
    {'contact_lens_type': 'RIGID', 'contact_lens_discontinuation_days': 20},
    {'contact_lens_type': 'NONE'},
])
def test_removed_lens_questionnaire_is_not_a_readiness_dependency(modifiers):
    result = evaluate_precore_readiness(
        age_years=30,
        eye_plans={'OD': {'prior': 'unknown', 'procedure': 'LASIK'}},
        patient_modifiers=modifiers,
    )
    assert result['ready'] is True
    assert result['blockers'] == []
    assert 'contact_lens_washout' not in result
