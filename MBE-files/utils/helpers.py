"""
Helper Functions for MBE Calculations.

This module provides convenience functions for calculating intermediate values
used in the Material Balance Equation (MBE) solvers. These functions encapsulate
common algebraic expressions to improve code readability and reduce manual errors.

All functions use US oilfield unit conventions consistent with the Handout.
"""

__all__ = [
    "calc_afactor_bo_rs",
    "calc_afactor_bt",
    "calc_cterm",
    "calc_rhs_per_n",
    "calc_freq",
]


def calc_afactor_bo_rs(bo: float, rp: float, rs: float, bg: float) -> float:
    """
    Calculate withdrawal coefficient (afactor) — Bo/Rs form.

    This is the coefficient used in the withdrawal equation F = Np * afactor + Wp*Bw.

    Formula (Handout p.2):
        afactor = Bo + (Rp - Rs) * Bg

    Args:
        bo : Current oil FVF, rb/STB
        rp : Cumulative producing GOR, SCF/STB
        rs : Current solution GOR, SCF/STB
        bg : Current gas FVF, rb/SCF

    Returns:
        afactor : Withdrawal coefficient, rb/STB
    """
    return bo + (rp - rs) * bg


def calc_afactor_bt(bt: float, rp: float, rsi: float, bg: float) -> float:
    """
    Calculate withdrawal coefficient (afactor) — two-phase Bt form.

    This is the coefficient used in the withdrawal equation F = Np * afactor + Wp*Bw.

    Formula (Handout p.3):
        afactor = Bt + (Rp - Rsi) * Bg

    Args:
        bt  : Current two-phase FVF, rb/STB
        rp  : Cumulative producing GOR, SCF/STB
        rsi : Initial solution GOR, SCF/STB
        bg  : Current gas FVF, rb/SCF

    Returns:
        afactor : Withdrawal coefficient, rb/STB
    """
    return bt + (rp - rsi) * bg


def calc_cterm(boi: float, ce: float, dp: float) -> float:
    """
    Calculate compressibility base term (cterm).

    Used in solving for m and dp via the Ef,w expansion term.

    Formula (derived from Handout p.2):
        cterm = Boi * ce * ΔP

    Where Ef,w = (1 + m) * cterm

    Args:
        boi : Initial oil FVF, rb/STB
        ce  : Effective compressibility, psi^-1
        dp  : Pressure drop (Pi - P), psi

    Returns:
        cterm : Compressibility term, rb/STB
    """
    return boi * ce * dp


def calc_rhs_per_n(f: float, we: float, inj_total: float, n: float) -> float:
    """
    Calculate normalized right-hand side of MBE (per STB of initial oil).

    This is used as input to solvers for m, dp, and bgi.

    Formula (derived from Handout p.2):
        rhs_per_n = (F - We - Inj) / N

    Args:
        f         : Total withdrawal, rb
        we        : Water influx, rb
        inj_total : Total injected volume (gas + water), rb
        n         : Initial oil-in-place, STB

    Returns:
        rhs_per_n : Right-hand side per STB, rb/STB

    Raises:
        ValueError: if n is zero
    """
    if n == 0:
        raise ValueError("N cannot be zero.")
    return (f - we - inj_total) / n


def calc_freq(n: float, eo: float, eg: float, efw: float, m: float,
              we: float, inj_total: float, wp: float, bw: float, np: float) -> float:
    """
    Calculate required withdrawal coefficient per STB oil (freq).

    Used in solving for Rp from the MBE.

    Formula (derived from Handout p.2):
        freq = (N*(Eo + m*Eg + Ef,w) + We + Inj - Wp*Bw) / Np

    Args:
        n         : Initial oil-in-place, STB
        eo        : Oil expansion term, rb/STB
        eg        : Gas cap expansion term, rb/STB
        efw       : Rock/water expansion term, rb/STB
        m         : Gas cap ratio, dimensionless
        we        : Water influx, rb
        inj_total : Total injected volume (gas + water), rb
        wp        : Cumulative water produced, STB
        bw        : Water FVF, rb/STB
        np        : Cumulative oil produced, STB

    Returns:
        freq : Required withdrawal coefficient, rb/STB

    Raises:
        ValueError: if np is zero
    """
    if np == 0:
        raise ValueError("Np cannot be zero.")
    return (n * (eo + m * eg + efw) + we + inj_total - wp * bw) / np
