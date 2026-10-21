import math

from services.orbits import EARTH_RADIUS_KM

BOLTZMANN_DB = -228.6

# Eb/N0 for BER 1e-5 over AWGN (Sklar, Digital Communications, 2nd ed., §4.7–4.8).
# Coherent BPSK/QPSK 9.6 dB; MSK/GMSK ≈ coherent BPSK; non-coherent binary FSK 13.4 dB
# (also used for GFSK and AFSK). Analog modes (CW, FM, SSB) have no digital threshold.
REQUIRED_EBN0_DB = {
    "BPSK": 9.6,
    "QPSK": 9.6,
    "MSK": 9.6,
    "GMSK": 9.6,
    "FSK": 13.4,
    "GFSK": 13.4,
    "AFSK": 13.4,
}
BITS_PER_SYMBOL = {"QPSK": 2}


def slant_range_km(elevation_deg: float, altitude_km: float) -> float:
    """d = −R·sin(E) + √(R²·sin²(E) + h² + 2·R·h) (TFI §3.5)."""
    sin_e = math.sin(math.radians(elevation_deg))
    r = EARTH_RADIUS_KM
    return -r * sin_e + math.sqrt(r**2 * sin_e**2 + altitude_km**2 + 2 * r * altitude_km)


def fsl_db(distance_km: float, freq_mhz: float) -> float:
    """FSL = 20·log10(d_km) + 20·log10(f_MHz) + 32.44 (TFI §3.7)."""
    return 20 * math.log10(distance_km) + 20 * math.log10(freq_mhz) + 32.44


def cnr_db(eirp_dbw: float, fsl: float, gain_dbi: float, noise_temp_k: float, bandwidth_hz: float) -> float:
    """CNR = EIRP − FSL + G_r − 10·log10(k) − 10·log10(T) − 10·log10(B) (TFI §3.7)."""
    return eirp_dbw - fsl + gain_dbi - BOLTZMANN_DB - 10 * math.log10(noise_temp_k) - 10 * math.log10(bandwidth_hz)


def link_budget(
    distance_km: float,
    freq_hz: float,
    eirp_dbw: float,
    gain_dbi: float,
    noise_temp_k: float,
    baud: float | None,
    mode: str | None,
    losses_db: float = 0,
) -> dict:
    """Noise bandwidth B is taken as the symbol rate; Eb/N0 = CNR + 10·log10(B/R_b).

    Omits atmospheric, polarization and pointing losses unless given as losses_db, so the margin is optimistic.
    """
    mode_key = (mode or "").upper()
    fsl = fsl_db(distance_km, freq_hz / 1e6)
    budget = {
        "distance_km": distance_km,
        "freq_hz": freq_hz,
        "fsl_db": fsl,
        "eirp_dbw": eirp_dbw,
        "gain_dbi": gain_dbi,
        "noise_temp_k": noise_temp_k,
        "losses_db": losses_db,
        "mode": mode,
        "baud": baud,
        "cnr_db": None,
        "ebn0_db": None,
        "required_ebn0_db": REQUIRED_EBN0_DB.get(mode_key),
        "margin_db": None,
        "decodable": None,
    }
    if not baud or baud <= 0:
        return budget

    bit_rate = baud * BITS_PER_SYMBOL.get(mode_key, 1)
    cnr = cnr_db(eirp_dbw, fsl + losses_db, gain_dbi, noise_temp_k, baud)
    ebn0 = cnr + 10 * math.log10(baud / bit_rate)
    budget.update(cnr_db=cnr, ebn0_db=ebn0)
    if budget["required_ebn0_db"] is not None:
        margin = ebn0 - budget["required_ebn0_db"]
        budget.update(margin_db=margin, decodable=margin >= 0)
    return budget
