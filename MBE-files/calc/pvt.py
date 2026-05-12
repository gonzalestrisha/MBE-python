"""
PVT Helper Functions for Gas Properties.

This module provides functions to calculate gas volumetric properties (FVF, expansion factors)
from PVT data. All functions follow US oilfield unit conventions (psia, °R, rb/SCF) as specified
in the Handout reference material.

Functions conform to standard Material Balance Equation (MBE) calculations.
"""

__all__ = ["calc_bgi_from_pvt", "calc_bg_from_pvt", "calc_eg_from_pvt"]


def calc_bgi_from_pvt(zi: float, ti: float, pi: float) -> float:
    """
    Calculate initial gas FVF (Bgi) from PVT data.

    Formula (US oilfield units, Handout):
        Bgi = 0.02827 * Z * T / P

    Args:
        zi : Initial gas compressibility factor, dimensionless
        ti : Initial reservoir temperature, °R (Rankine = °F + 459.67)
        pi : Initial reservoir pressure, psia

    Returns:
        Bgi : Initial gas FVF, rb/SCF

    Raises:
        ValueError: if pi <= 0, ti <= 0, or zi <= 0
    """
    if pi <= 0:
        raise ValueError("Pi (initial pressure) must be greater than zero.")
    if ti <= 0:
        raise ValueError("Ti (initial temperature in Rankine) must be greater than zero.")
    if zi <= 0:
        raise ValueError("Zi (initial compressibility factor) must be greater than zero.")
    return 0.02827 * zi * ti / pi


def calc_bg_from_pvt(z: float, t: float, p: float) -> float:
    """
    Calculate current gas FVF (Bg) from PVT data.

    Formula (US oilfield units, Handout):
        Bg = 0.02827 * Z * T / P

    Args:
        z : Current gas compressibility factor, dimensionless
        t : Current reservoir temperature, °R (Rankine = °F + 459.67)
        p : Current reservoir pressure, psia

    Returns:
        Bg : Current gas FVF, rb/SCF

    Raises:
        ValueError: if p <= 0, t <= 0, or z <= 0
    """
    if p <= 0:
        raise ValueError("P (current pressure) must be greater than zero.")
    if t <= 0:
        raise ValueError("T (current temperature in Rankine) must be greater than zero.")
    if z <= 0:
        raise ValueError("Z (gas compressibility factor) must be greater than zero.")
    return 0.02827 * z * t / p


def calc_eg_from_pvt(z: float, t: float, p: float) -> float:
    """
    Calculate gas expansion factor (Eg) from PVT data.

    Formula (US oilfield units, Handout):
        Eg = 35.37 * P / (Z * T)

    Args:
        z : Gas compressibility factor, dimensionless
        t : Reservoir temperature, °R (Rankine)
        p : Reservoir pressure, psia

    Returns:
        Eg : Gas expansion term, rb/STB (or appropriate units per usage)

    Raises:
        ValueError: if any input <= 0
    """
    if p <= 0:
        raise ValueError("P (pressure) must be greater than zero.")
    if t <= 0:
        raise ValueError("T (reservoir temperature in Rankine) must be greater than zero.")
    if z <= 0:
        raise ValueError("Z (gas compressibility factor) must be greater than zero.")
    return 35.37 * p / (z * t)