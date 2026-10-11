"""Posterior-source retry, principal-axis completion, and absent-radius contracts."""
import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError

from iol_module.extraction import extract_image
from iol_module.models import PosteriorCorneaInput


def source(**updates):
    result = {"document_type": "PENTACAM_4_MAPS_REFRACTIVE", "eye": "OD",
              "cornea_back": {"k1_d": -5.8, "k2_d": -6.1, "k1_axis_deg": None, "k2_axis_deg": 110},
              "unreadable_fields": ["cornea_back.k1_axis_deg"]}
    result.update(updates)
    return result


class Reader:
    MODEL = "test-model"

    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []
        self.responses = self

    def openai_client(self):
        return self

    def with_options(self, **kwargs):
        assert kwargs == {"timeout": 60, "max_retries": 0}
        return self

    def data_url(self, raw, name):
        return name

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(output_text=json.dumps(output))


def read(core):
    raw = BytesIO()
    Image.new("RGB", (300, 200)).save(raw, format="PNG")
    return extract_image(core, raw.getvalue(), "source.png")


def test_single_printed_steep_axis_needs_no_retry_or_radii():
    core = Reader(source())
    result = read(core)
    assert len(core.calls) == 1
    assert result["cornea_back"]["k1_axis_deg"] == 20
    assert result["cornea_back_derived_fields"] == ["k1_axis_deg"]
    assert result["unreadable_fields"] == []
    case = PosteriorCorneaInput(eye="OD", source="PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK", **result["cornea_back"])
    assert case.rh_mm is None and case.rv_mm is None


def test_retry_recovers_only_missing_posterior_field():
    primary = source(cornea_back={"k1_d": -5.8, "k2_d": None, "k1_axis_deg": None, "k2_axis_deg": 110},
                     unreadable_fields=["cornea_back.k2_d", "pentacam.hwtw_mm"])
    core = Reader(primary, source())
    result = read(core)
    assert len(core.calls) == 2
    assert len(core.calls[1]["input"][0]["content"]) == 3
    assert result["cornea_back"]["k2_d"] == -6.1
    assert result["cornea_back"]["k1_axis_deg"] == 20
    assert result["unreadable_fields"] == ["pentacam.hwtw_mm"]


@pytest.mark.parametrize("change", [{"eye": "OS"}, {"document_type": "PENTACAM_CATARACT_PREOP"},
                                    {"cornea_back": {"k1_d": -7, "k2_d": -8, "k2_axis_deg": 110}}])
def test_retry_rejects_other_eye_document_or_conflicting_measurements(change):
    primary = source(cornea_back={"k1_d": -5.8, "k2_d": None, "k1_axis_deg": None, "k2_axis_deg": 110})
    result = read(Reader(primary, source(**change)))
    assert result["cornea_back"]["k2_d"] is None
    assert result["cornea_back"]["k1_d"] == -5.8


def test_retry_failure_preserves_primary_and_manual_completion():
    primary = source(cornea_back={"k1_d": -5.8, "k2_d": None, "k1_axis_deg": None, "k2_axis_deg": 110})
    result = read(Reader(primary, TimeoutError()))
    assert result["cornea_back"]["k2_d"] is None


def test_retry_rejects_inconsistent_axes():
    primary = source(cornea_back={"k1_d": -5.8, "k2_d": -6.1, "k1_axis_deg": None, "k2_axis_deg": None})
    retry = source(cornea_back={"k1_d": -5.8, "k2_d": -6.1, "k1_axis_deg": 20, "k2_axis_deg": 40})
    result = read(Reader(primary, retry))
    assert result["cornea_back"]["k1_axis_deg"] is None
    assert result["cornea_back"]["k2_axis_deg"] is None


@pytest.mark.parametrize("axis,expected", [(0,90), (90,0), (180,90), (110,20)])
def test_input_model_completes_companion_axis_without_radii(axis, expected):
    case = PosteriorCorneaInput(eye="OD", source="PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK",
                              k1_d=-5.8, k2_d=-6.1, k2_axis_deg=axis)
    assert case.k1_axis_deg == expected


def test_no_axis_is_not_invented():
    with pytest.raises(ValidationError):
        PosteriorCorneaInput(eye="OD", source="PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK", k1_d=-5.8, k2_d=-6.1)


def test_non_four_maps_source_does_not_trigger_posterior_retry():
    core = Reader(source(document_type="PENTACAM_CATARACT_PREOP", cornea_back={}))
    read(core)
    assert len(core.calls) == 1


def test_input_model_preserves_two_printed_axes_and_rejects_conflict():
    payload = dict(eye="OD", source="PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK", k1_d=-5.8, k2_d=-6.1,
                   k1_axis_deg=21, k2_axis_deg=110)
    assert PosteriorCorneaInput(**payload).k1_axis_deg == 21
    with pytest.raises(ValidationError):
        PosteriorCorneaInput(**{**payload, "k1_axis_deg": 40})
