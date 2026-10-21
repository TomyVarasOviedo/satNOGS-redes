import pytest

from services.linkbudget import (
    REQUIRED_EBN0_DB,
    cnr_db,
    fsl_db,
    link_budget,
    slant_range_km,
)


def test_free_space_loss_matches_the_tfi_examples():
    assert fsl_db(1000, 437) == pytest.approx(145.25, abs=0.01)
    assert fsl_db(36000, 437) == pytest.approx(176.37, abs=0.01)
    assert fsl_db(36000, 437) - fsl_db(1000, 437) == pytest.approx(31.1, abs=0.1)


def test_slant_range_is_the_altitude_at_zenith_and_the_tangent_at_the_horizon():
    assert slant_range_km(90, 550) == pytest.approx(550, abs=1e-6)
    assert slant_range_km(0, 550) == pytest.approx((550**2 + 2 * 6371 * 550) ** 0.5, abs=1e-6)


def test_cnr_by_hand():
    # 0 dBW − 145.249 + 12 + 228.6 − 10·log10(500) − 10·log10(1200) = 37.569 dB
    assert cnr_db(0, fsl_db(1000, 437), 12, 500, 1200) == pytest.approx(37.569, abs=0.01)


def test_bpsk_margin_is_ebn0_minus_the_required_ebn0():
    budget = link_budget(distance_km=1000, freq_hz=437e6, eirp_dbw=0, gain_dbi=12, noise_temp_k=500, baud=1200, mode="BPSK")

    assert budget["ebn0_db"] == pytest.approx(37.569, abs=0.01)
    assert budget["required_ebn0_db"] == REQUIRED_EBN0_DB["BPSK"] == 9.6
    assert budget["margin_db"] == pytest.approx(37.569 - 9.6, abs=0.01)
    assert budget["decodable"] is True


def test_extra_losses_reduce_the_margin_one_for_one():
    base = link_budget(1000, 437e6, 0, 12, 500, 1200, "BPSK")
    lossy = link_budget(1000, 437e6, 0, 12, 500, 1200, "BPSK", losses_db=3)

    assert base["margin_db"] - lossy["margin_db"] == pytest.approx(3)


def test_modes_without_a_digital_threshold_have_no_margin():
    budget = link_budget(1000, 437e6, 0, 12, 500, baud=0, mode="CW")

    assert budget["margin_db"] is None and budget["decodable"] is None
    assert "fsl_db" in budget
