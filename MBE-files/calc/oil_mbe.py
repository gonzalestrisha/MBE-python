"""
calc/oil_mbe.py
---------------
Pure calculation functions for Oil Reservoir Material Balance Equations.
No Streamlit imports. All functions take plain numbers, return plain numbers.

Reference: Material Balance Equation for Oil and Gas Reservoirs (Handout)

Unit conventions used throughout:
    Pressure      : psia
    Volume (oil)  : STB (surface) / rb (reservoir)
    Volume (gas)  : SCF (surface) / rb (reservoir)
    FVF oil (Bo)  : rb/STB
    FVF gas (Bg)  : rb/SCF
    Rs, Rp        : SCF/STB
    We, Wp*Bw     : rb
    N             : STB
"""

from utils.helpers import calc_afactor_bo_rs, calc_afactor_bt

# =============================================================================
# SECTION 1 — VOLUMETRIC OOIP
# Handout Page 1
# =============================================================================

def calc_volumetric_ooip(v_bulk: float, phi: float, swc: float, boi: float) -> float:
    """
    Calculate Initial Oil-in-Place (N) from reservoir geometry.

    Formula (Handout p.1):
        N = 7758 * V * phi * (1 - Swc) / Boi

    Args:
        v_bulk : Reservoir bulk volume, acre-ft
        phi    : Porosity, fraction
        swc    : Connate water saturation, fraction
        boi    : Initial oil FVF, rb/STB

    Returns:
        N : Initial oil-in-place, STB

    Raises:
        ValueError: if boi <= 0 or swc >= 1
    """
    if boi <= 0:
        raise ValueError("Boi must be greater than zero.")
    if swc >= 1:
        raise ValueError("Swc must be less than 1.")

    return (7758 * v_bulk * phi * (1 - swc)) / boi


# =============================================================================
# SECTION 2 — PVT EXPANSION TERMS (Havlena-Odeh components)
# Handout Pages 2–3
# These are shared building blocks used by ALL oil MBE solvers below.
# =============================================================================

def calc_eo(bo: float, boi: float, rs: float, rsi: float, bg: float) -> float:
    """
    Oil and originally dissolved gas expansion term (Eo).

    Formula (Handout p.2):
        Eo = (Bo - Boi) + (Rsi - Rs) * Bg

    Args:
        bo  : Current oil FVF, rb/STB
        boi : Initial oil FVF, rb/STB
        rs  : Current solution GOR, SCF/STB
        rsi : Initial solution GOR, SCF/STB
        bg  : Current gas FVF, rb/SCF

    Returns:
        Eo : rb/STB
    """
    return (bo - boi) + (rsi - rs) * bg

# TODO: what is bt?
def calc_eo_bt(bt: float, bti: float) -> float: 
    """
    Oil and dissolved gas expansion term (Eo) using two-phase FVF.

    Formula (Handout p.3):
        Eo = Bt - Bti    where Bti = Boi

    Args:
        bt  : Current two-phase FVF, rb/STB
        bti : Initial two-phase FVF (= Boi), rb/STB

    Returns:
        Eo : rb/STB
    """
    return bt - bti


def calc_eg(boi: float, bg: float, bgi: float) -> float:
    """
    Gas cap expansion term (Eg).

    Formula (Handout p.2):
        Eg = Boi * (Bg/Bgi - 1)

    Args:
        boi : Initial oil FVF, rb/STB
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF

    Returns:
        Eg : rb/STB

    Raises:
        ValueError: if bgi <= 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    return boi * ((bg / bgi) - 1)


def calc_eg_bt(bti: float, bg: float, bgi: float) -> float:
    """
    Gas cap expansion term (Eg) using two-phase FVF.

    Formula (Handout p.3):
        Eg = Bti * (Bg/Bgi - 1)    where Bti = Boi

    Args:
        bti : Initial two-phase FVF (= Boi), rb/STB
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF

    Returns:
        Eg : rb/STB

    Raises:
        ValueError: if bgi <= 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    return bti * ((bg / bgi) - 1)


def calc_efw(boi: float, m: float, swi: float, cw: float, cf: float, dp: float) -> float:
    """
    Formation rock and connate water expansion term (Ef,w).

    Formula (Handout p.2):
        Ef,w = Boi * (1 + m) * ((Swi*cw + cf) / (1 - Swi)) * delta_P

    Args:
        boi : Initial oil FVF, rb/STB
        m   : Gas cap ratio (gas cap vol / oil vol), dimensionless
        swi : Initial water saturation, fraction
        cw  : Water compressibility, psi^-1
        cf  : Formation compressibility, psi^-1
        dp  : Pressure drop (Pi - P), psi

    Returns:
        Ef,w : rb/STB

    Raises:
        ValueError: if swi >= 1
    """
    if swi >= 1:
        raise ValueError("Swi must be less than 1.")
    return boi * (1 + m) * ((swi * cw + cf) / (1 - swi)) * dp


def calc_withdrawal(np: float, bo: float, rp: float, rs: float,
                    bg: float, wp: float, bw: float) -> float:
    """
    Total underground withdrawal (F) — Bo/Rs form.

    Formula (Handout p.2):
        F = Np * (Bo + (Rp - Rs) * Bg) + Wp * Bw

    Args:
        np  : Cumulative oil produced, STB
        bo  : Current oil FVF, rb/STB
        rp  : Cumulative producing GOR, SCF/STB
        rs  : Current solution GOR, SCF/STB
        bg  : Current gas FVF, rb/SCF
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB

    Returns:
        F : Total withdrawal, rb
    """
    afactor = calc_afactor_bo_rs(bo, rp, rs, bg)
    return np * afactor + wp * bw


def calc_withdrawal_bt(np: float, bt: float, rp: float, rsi: float,
                       bg: float, wp: float, bw: float) -> float:
    """
    Total underground withdrawal (F) — two-phase Bt form.

    Formula (Handout p.3):
        F = Np * (Bt + (Rp - Rsi) * Bg) + Wp * Bw

    Args:
        np  : Cumulative oil produced, STB
        bt  : Current two-phase FVF, rb/STB
        rp  : Cumulative producing GOR, SCF/STB
        rsi : Initial solution GOR, SCF/STB
        bg  : Current gas FVF, rb/SCF
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB

    Returns:
        F : Total withdrawal, rb
    """
    afactor = calc_afactor_bt(bt, rp, rsi, bg)
    return np * afactor + wp * bw


# =============================================================================
# SECTION 3 — GENERAL MBE SOLVERS (Havlena-Odeh, full form)
# Handout Pages 2–3
# F = N*(Eo + m*Eg + Ef,w) + We  (± injection)
# These solve for one unknown given all others.
# =============================================================================
# TODO: Where to find the justification for this?
def solve_n(f: float, eo: float, eg: float, efw: float,
            m: float, we: float, inj_total: float = 0.0) -> float:
    """
    Solve for Initial Oil-in-Place (N).

    Based on the Havlena–Odeh material balance:
        F = N*(Eo + m*Eg + Ef,w) + We + Inj

    Rearranged:
        N = (F - We - Inj) / (Eo + m*Eg + Ef,w)

    Args:
        f         : Total withdrawal, rb
        eo        : Oil expansion term, rb/STB
        eg        : Gas cap expansion term, rb/STB
        efw       : Rock/water expansion term, rb/STB
        m         : Gas cap ratio, dimensionless
        we        : Water influx, rb
        inj_total : Total injected reservoir-volume-equivalent, rb
                    (i.e. G_inj * B_g_inj + W_inj * B_w_inj)

    Returns:
        N : Initial oil-in-place, STB

    Raises:
        ValueError: if denominator is zero or inputs produce non-physical N (<= 0).
    """
    denom = eo + m * eg + efw
    if denom == 0:
        raise ValueError("Denominator (Eo + m*Eg + Efw) is zero. Check PVT/pressure/injection inputs.")
    numer = f - we - inj_total
    if numer == 0:
        raise ValueError("Numerator (F - We - Inj) is zero. Check signs/units of F, We, and inj_total.")
    return numer / denom


def solve_we(f: float, n: float, eo: float, eg: float,
             efw: float, m: float, inj_total: float = 0.0) -> float:
    """
    Solve for Water Influx (We).

    Rearranged from (Handout p.2):
        We = F - N*(Eo + m*Eg + Ef,w) - Inj 

    Args:
        f         : Total withdrawal, rb
        n         : Initial oil-in-place, STB
        eo        : Oil expansion term, rb/STB
        eg        : Gas cap expansion term, rb/STB
        efw       : Rock/water expansion term, rb/STB
        m         : Gas cap ratio, dimensionless
        inj_total : Total injection (gas + water), rb (default 0)

    Returns:
        We : Water influx, rb
    """
    return f - n * (eo + m * eg + efw) - inj_total 

def solve_np(n: float, eo: float, eg: float, efw: float, m: float,
             we: float, wp: float, bw: float, afactor: float,
             inj_total: float = 0.0) -> float:
    """
    Solve for Cumulative Oil Production (Np).

    Rearranged from F = N*(Eo + m*Eg + Ef,w) + We + Inj:
        Np = (N*(Eo + m*Eg + Ef,w)denom + We + Inj - Wp*Bw) / afactor
        where afactor = Bo + (Rp - Rs)*Bg  OR  Bt + (Rp - Rsi)*Bg

    Args:
        n         : Initial oil-in-place, STB
        eo        : Oil expansion term, rb/STB
        eg        : Gas cap expansion term, rb/STB
        efw       : Rock/water expansion term, rb/STB
        m         : Gas cap ratio, dimensionless
        we        : Water influx, rb
        wp        : Cumulative water produced, STB
        bw        : Water FVF, rb/STB
        afactor   : Withdrawal coefficient per STB oil, rb/STB
        inj_total : Total injection, rb (default 0)

    Returns:
        Np : Cumulative oil production, STB

    Raises:
        ValueError: if afactor is zero
    """
    if afactor == 0:
        raise ValueError("Withdrawal coefficient (afactor) cannot be zero.")
    return (n * (eo + m * eg + efw) + we + inj_total - wp * bw) / afactor


def solve_wp(n: float, eo: float, eg: float, efw: float, m: float,
             we: float, np: float, afactor: float, bw: float,
             inj_total: float = 0.0) -> float:
    """
    Solve for Cumulative Water Production (Wp).

    Rearranged from F = N*(Eo + m*Eg + Ef,w) + We + Inj:
        Wp = (N*denom + We + Inj - Np*afactor) / Bw

    Args:
        n         : Initial oil-in-place, STB
        eo        : Oil expansion term, rb/STB
        eg        : Gas cap expansion term, rb/STB
        efw       : Rock/water expansion term, rb/STB
        m         : Gas cap ratio, dimensionless
        we        : Water influx, rb
        np        : Cumulative oil produced, STB
        afactor   : Withdrawal coefficient per STB oil, rb/STB
        bw        : Water FVF, rb/STB
        inj_total : Total injection, rb (default 0)

    Returns:
        Wp : Cumulative water production, STB

    Raises:
        ValueError: if bw is zero
    """
    if bw == 0:
        raise ValueError("Bw cannot be zero.")
    return (n * (eo + m * eg + efw) + we + inj_total - np * afactor) / bw


def solve_m(rhs_per_n: float, eo: float, eg: float, cterm: float) -> float:
    """
    Solve for gas cap ratio (m).

    Derivation from F - We - Inj = N*(Eo + m*Eg + Ef,w):
        (F - We - Inj)/N = Eo + m*Eg + (1+m)*cterm
        (F - We - Inj)/N - Eo - cterm = m*(Eg + cterm)
        m = ((F-We-Inj)/N - Eo - cterm) / (Eg + cterm)

    Args:
        rhs_per_n : (F - We - Inj) / N, rb/STB
        eo        : Oil expansion term, rb/STB
        eg        : Gas cap expansion term, rb/STB
        cterm     : Boi * ce * dp (compressibility base term), rb/STB

    Returns:
        m : Gas cap ratio, dimensionless

    Raises:
        ValueError: if (eg + cterm) is zero
    """
    denom = eg + cterm
    if denom == 0:
        raise ValueError("(Eg + cterm) is zero. Cannot solve for m.")
    return (rhs_per_n - eo - cterm) / denom


def solve_dp(rhs_per_n: float, eo: float, eg: float, m: float,
             boi: float, ce: float) -> float:
    """
    Solve for pressure drop (delta P).

    Derivation:
        Ef,w = (1+m)*Boi*ce*dp
        dp = ((F-We-Inj)/N - Eo - m*Eg) / ((1+m)*Boi*ce)

    Args:
        rhs_per_n : (F - We - Inj) / N, rb/STB
        eo        : Oil expansion term, rb/STB
        eg        : Gas cap expansion term, rb/STB
        m         : Gas cap ratio, dimensionless
        boi       : Initial oil FVF, rb/STB
        ce        : Effective compressibility, psi^-1

    Returns:
        dp : Pressure drop (Pi - P), psi

    Raises:
        ValueError: if factor (1+m)*Boi*ce is zero
    """
    factor = (1 + m) * boi * ce
    if factor == 0:
        raise ValueError("Compressibility factor (1+m)*Boi*ce is zero. Check inputs.")
    efw_req = rhs_per_n - eo - m * eg
    return efw_req / factor


def solve_bo(n: float, np: float, boi: float, ce: float, dp: float) -> float:
    """
    Solve for current oil FVF (Bo) — undersaturated reservoir case.

    BUG FIX: Original code had wrong formula. Correct derivation:
        N = Np*Bo / (Bo - Boi + Boi*ce*dp)
        N*(Bo - Boi + Boi*ce*dp) = Np*Bo
        N*Bo - N*Boi*(1 - ce*dp) = Np*Bo
        Bo*(N - Np) = N*Boi*(1 - ce*dp)
        Bo = N*Boi*(1 - ce*dp) / (N - Np)

    Ref: Handout p.4-5 (Undersaturated, with rock/liquid expansion)

    Args:
        n   : Initial oil-in-place, STB
        np  : Cumulative oil produced, STB
        boi : Initial oil FVF, rb/STB
        ce  : Effective compressibility, psi^-1
        dp  : Pressure drop (Pi - P), psi

    Returns:
        Bo : Current oil FVF, rb/STB

    Raises:
        ValueError: if (N - Np) is zero
    """
    denom = n - np
    if denom <= 0:
        raise ValueError("N - Np must be > 0")
    return (n * boi * (1 - ce * dp)) / denom


def solve_rp(freq: float, np: float, bo: float, rs: float,
             bg: float, pvt_mode: str = "bo_rs",
             bt: float = 0.0, rsi: float = 0.0) -> float:
    """
    Solve for cumulative producing GOR (Rp).

    Derivation:
        afactor = F_required / Np
        afactor = Bo + (Rp - Rs)*Bg  →  Rp = (afactor - Bo)/Bg + Rs
        OR (Bt mode):
        afactor = Bt + (Rp - Rsi)*Bg →  Rp = (afactor - Bt)/Bg + Rsi

    Args:
        freq     : Required withdrawal per STB = (N*denom + We + Inj - Wp*Bw) / Np, rb/STB
        np       : Cumulative oil produced, STB (used only for validation)
        bo       : Current oil FVF, rb/STB
        rs       : Current solution GOR, SCF/STB
        bg       : Current gas FVF, rb/SCF
        pvt_mode : "bo_rs" (default) or "bt"
        bt       : Two-phase FVF, rb/STB (required if pvt_mode="bt")
        rsi      : Initial solution GOR, SCF/STB (required if pvt_mode="bt")

    Returns:
        Rp : Cumulative producing GOR, SCF/STB

    Raises:
        ValueError: if bg is zero
    """
    if bg == 0:
        raise ValueError("Bg cannot be zero when solving for Rp.")
    if pvt_mode == "bt":
        return ((freq - bt) / bg) + rsi
    return ((freq - bo) / bg) + rs


def solve_bg(n: float, np: float, bo: float, boi: float, rp: float,
             rs: float, rsi: float, bgi: float, m: float,
             we: float, wp: float, bw: float, efw: float,
             inj_total: float = 0.0, pvt_mode: str = "bo_rs",
             bt: float = 0.0, bti: float = 0.0) -> float:
    """
    Solve for current gas FVF (Bg).

    Complex algebraic rearrangement of the full MBE.
    Both Bo/Rs and Bt modes are supported.

    Args:
        n         : Initial oil-in-place, STB
        np        : Cumulative oil produced, STB
        bo        : Current oil FVF, rb/STB
        boi       : Initial oil FVF, rb/STB
        rp        : Cumulative GOR, SCF/STB
        rs        : Current solution GOR, SCF/STB
        rsi       : Initial solution GOR, SCF/STB
        bgi       : Initial gas FVF, rb/SCF
        m         : Gas cap ratio, dimensionless
        we        : Water influx, rb
        wp        : Cumulative water produced, STB
        bw        : Water FVF, rb/STB
        efw       : Rock/water expansion term (pre-computed without Bg), rb/STB
        inj_total : Total injection, rb (default 0)
        pvt_mode  : "bo_rs" (default) or "bt"
        bt        : Two-phase FVF, rb/STB (required if pvt_mode="bt")
        bti       : Initial two-phase FVF, rb/STB (required if pvt_mode="bt")

    Returns:
        Bg : Current gas FVF, rb/SCF

    Raises:
        ValueError: if denominator is zero
    """
    if pvt_mode == "bt":
        bg_num = np * bt + wp * bw - we - inj_total - n * (bt - bti - m * bti + efw)
        bg_den = n * (m * bti / bgi if bgi else 0) - np * (rp - rsi)
    else:
        bg_num = np * bo + wp * bw - we - inj_total - n * (bo - boi - m * boi + efw)
        bg_den = n * (rsi - rs + (m * boi / bgi if bgi else 0)) - np * (rp - rs)

    if bg_den == 0:
        raise ValueError("Bg denominator is zero. Check input values.")
    return bg_num / bg_den

#TODO: FUNCTION NOT NEEDED?
def solve_bt(n: float, np: float, rp: float, rsi: float, bg: float,
             bti: float, m: float, eg: float, efw: float,
             we: float, wp: float, bw: float,
             inj_total: float = 0.0) -> float:
    """
    Solve for two-phase FVF (Bt).

    Rearranged from (Handout p.3):
        F = N*(Eo + m*Eg + Ef,w) + We + Inj
        Np*(Bt + (Rp-Rsi)*Bg) + Wp*Bw = N*(Bt-Bti + m*Eg + Ef,w) + We + Inj
        Bt*(Np - N) = N*(-Bti - m*Eg - Ef,w) + We + Inj - Np*(Rp-Rsi)*Bg - Wp*Bw
        Bt = (We + Inj - Np*(Rp-Rsi)*Bg - Wp*Bw + N*(Bti - m*Eg - Ef,w)) / (Np - N)

    Args:
        n         : Initial oil-in-place, STB
        np        : Cumulative oil produced, STB
        rp        : Cumulative GOR, SCF/STB
        rsi       : Initial solution GOR, SCF/STB
        bg        : Current gas FVF, rb/SCF
        bti       : Initial two-phase FVF (= Boi), rb/STB
        m         : Gas cap ratio, dimensionless
        eg        : Gas cap expansion term, rb/STB
        efw       : Rock/water expansion term, rb/STB
        we        : Water influx, rb
        wp        : Cumulative water produced, STB
        bw        : Water FVF, rb/STB
        inj_total : Total injection, rb (default 0)

    Returns:
        Bt : Two-phase FVF, rb/STB

    Raises:
        ValueError: if (Np - N) is zero
    """
    denom = np - n
    if denom == 0:
        raise ValueError("(Np - N) is zero. Cannot solve for Bt.")
    return (we + inj_total - np * (rp - rsi) * bg - wp * bw + n * (bti - m * eg - efw)) / denom


def solve_bgi(n: float, rhs_per_n: float, eo: float, efw: float,
              m: float, boi: float, bg: float) -> float:
    """
    Solve for initial gas FVF (Bgi).

    Derivation:
        Eg = (rhs/N - Eo - Ef,w) / m
        Boi*(Bg/Bgi - 1) = Eg
        Bg/Bgi = (Eg/Boi) + 1
        Bgi = Bg / ((Eg/Boi) + 1)

    Args:
        n         : Initial oil-in-place, STB (for validation only)
        rhs_per_n : (F - We - Inj) / N, rb/STB
        eo        : Oil expansion term, rb/STB
        efw       : Rock/water expansion term, rb/STB
        m         : Gas cap ratio, dimensionless
        boi       : Initial oil FVF, rb/STB
        bg        : Current gas FVF, rb/SCF

    Returns:
        Bgi : Initial gas FVF, rb/SCF

    Raises:
        ValueError: if m is zero, boi is zero, or denominator is zero
    """
    if m == 0:
        raise ValueError("m cannot be zero when solving for Bgi (no gas cap).")
    if boi == 0:
        raise ValueError("Boi cannot be zero.")
    req_eg = (rhs_per_n - eo - efw) / m
    denom = (req_eg / boi) + 1
    if denom <= 0:
        raise ValueError("Bgi denominator is zero. Check input values.")
    return bg / denom


# =============================================================================
# SECTION 4 — DRIVE INDICES
# Handout Pages 2–8 (implied from energy term breakdown)
# DDI + SDI + WDI + EDI must sum to 1.0
# =============================================================================

def calc_drive_indices(n: float, eo: float, eg: float, efw: float,
                       m: float, we: float, wp: float, bw: float,
                       withdrawal: float) -> dict:
    """
    Calculate all four drive mechanism indices.

    Definitions:
        DDI = N*Eo / F                (Depletion Drive Index)
        SDI = N*m*Eg / F              (Segregation/Gas Cap Drive Index)
        WDI = (We - Wp*Bw) / F       (Water Drive Index)
        EDI = N*Ef,w / F              (Expansion Drive Index)

    Args:
        n          : Initial oil-in-place, STB
        eo         : Oil expansion term, rb/STB
        eg         : Gas cap expansion term, rb/STB
        efw        : Rock/water expansion term, rb/STB
        m          : Gas cap ratio, dimensionless
        we         : Water influx, rb
        wp         : Cumulative water produced, STB
        bw         : Water FVF, rb/STB
        withdrawal : Total withdrawal F, rb

    Returns:
        dict with keys: ddi, sdi, wdi, edi, total
        (total should equal 1.0 if inputs are consistent)

    Raises:
        ValueError: if withdrawal is zero
    """
    if withdrawal == 0:
        raise ValueError("Total withdrawal (F) cannot be zero.")

    ddi = max(0.0, (n * eo) / withdrawal)
    sdi = max(0.0, (n * m * eg) / withdrawal)
    wdi = max(0.0, (we - wp * bw) / withdrawal)
    edi = max(0.0, (n * efw) / withdrawal)

    total = ddi + sdi + wdi + edi
    if total == 0:
        raise ValueError("Drive indices cannot be normalized because all contributions are zero.")

    ddi /= total
    sdi /= total
    wdi /= total
    edi /= total

    return {
        "ddi": ddi,
        "sdi": sdi,
        "wdi": wdi,
        "edi": edi,
        "total": ddi + sdi + wdi + edi
    }


# =============================================================================
# SECTION 5 — EFFECTIVE COMPRESSIBILITY
# Handout Page 5
# =============================================================================

def calc_ce_simple(swi: float, cw: float, cf: float) -> float:
    """
    Effective compressibility — simplified form used in general MBE.

    Formula (Handout p.2, denominator term):
        ce = (Swi*cw + cf) / (1 - Swi)

    Note: This is the correct form for the general MBE Ef,w term.
    For the undersaturated simplified N formula (p.5), the full form
    with co*So should be used via calc_ce_full().

    Args:
        swi : Initial water saturation, fraction
        cw  : Water compressibility, psi^-1
        cf  : Formation compressibility, psi^-1

    Returns:
        ce : Effective compressibility, psi^-1

    Raises:
        ValueError: if swi >= 1
    """
    if swi >= 1:
        raise ValueError("Swi must be less than 1.")
    return (swi * cw + cf) / (1 - swi)


def calc_ce_full(so: float, co: float, sw: float, cw: float, cf: float) -> float:
    """
    Effective compressibility — full form for undersaturated simplified MBE.

    Formula (Handout p.5):
        ce = (co*So + cw*Sw + cf) / (1 - Sw)

    Used specifically when computing N = Np*Bo / (Boi*ce*dp).

    Args:
        so : Current oil saturation, fraction
        co : Oil compressibility, psi^-1
        sw : Current water saturation, fraction
        cw : Water compressibility, psi^-1
        cf : Formation compressibility, psi^-1

    Returns:
        ce : Effective compressibility, psi^-1

    Raises:
        ValueError: if sw >= 1
    """
    if sw >= 1:
        raise ValueError("Sw must be less than 1.")
    return (co * so + cw * sw + cf) / (1 - sw)