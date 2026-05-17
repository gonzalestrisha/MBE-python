"""
calc/gas_mbe.py
---------------
Pure calculation functions for Gas Reservoir Material Balance Equations.
No Streamlit imports. All functions take plain numbers, return plain numbers.

Reference: Material Balance Equation for Oil and Gas Reservoirs (Handout)

Unit conventions used throughout:
    Pressure        : psia
    Temperature     : °R (Rankine = °F + 459.67)
    Volume (gas)    : SCF (surface) / rb or ft³ (reservoir)
    FVF gas (Bg)    : rb/SCF
    G, Gp           : SCF
    We              : rb
    Wp              : STB
    Bw              : rb/STB
    Swi, cw, cf     : fraction / psi^-1

Bullet map (Gas Reservoir breakdown):
    1.  Volumetric GIIP         → calc_volumetric_giip()
    2.  Gas produced (depletion)→ calc_gp_volumetric()
    3.  p/z method              → calc_pz(), calc_g_from_pz()
    4.  General Bg-based MBE    → solve_g_general()
    5.  Without bottom water    → solve_g_no_water()
    6.  With bottom water       → solve_g_with_water()
    7.  With bottom water + Efw → solve_g_overpressured()
    8.  Havlena-Odeh terms      → calc_f_gas(), calc_eg_gas(), calc_efw_gas()
    9.  Drive indices            → calc_drive_indices_gas()
    (Bg formula lives in pvt.py)
"""

#TODO: recheck ALL formulas 


# =============================================================================
# SECTION 1 — VOLUMETRIC GIIP
# Handout Page 9
# G = 43560 * A * h * phi * (1 - Swi) / Bgi
# =============================================================================

def calc_volumetric_giip(area: float, h: float, phi: float,
                         swi: float, bgi: float) -> float:
    """
    Calculate Gas Initial-in-Place (G) from reservoir geometry.

    Formula (Handout p.9):
        G = 43560 * A * h * phi * (1 - Swi) / Bgi

    Note: If bulk volume (V = A * h) is already known as acre-ft, pass
    area = V and h = 1.0. The constant 43560 converts acre-ft to ft³.

    Args:
        area : Reservoir area, acres
        h    : Average reservoir thickness, ft
        phi  : Porosity, fraction
        swi  : Initial water saturation, fraction
        bgi  : Initial gas FVF, ft³/SCF

    Returns:
        G : Gas initial-in-place, SCF

    Raises:
        ValueError: if bgi <= 0 or swi >= 1 or any geometric input <= 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    if swi >= 1:
        raise ValueError("Swi must be less than 1.")
    if area <= 0:
        raise ValueError("Reservoir area must be greater than zero.")
    if h <= 0:
        raise ValueError("Reservoir thickness must be greater than zero.")
    if phi <= 0:
        raise ValueError("Porosity must be greater than zero.")

    return (43560 * area * h * phi * (1 - swi)) / bgi


# =============================================================================
# SECTION 2 — GAS PRODUCED FROM VOLUMETRIC DEPLETION
# Handout Page 9
# Gp = 43560 * A * h * phi * (1 - Swi) * (1/Bgi - 1/Bga)
# =============================================================================

def calc_gp_volumetric(area: float, h: float, phi: float,
                       swi: float, bgi: float, bga: float) -> float:
    """
    Calculate cumulative gas produced at abandonment from volumetric depletion.

    Formula (Handout p.9):
        Gp = 43560 * A * h * phi * (1 - Swi) * (1/Bgi - 1/Bga)

    Args:
        area : Reservoir area, acres
        h    : Average reservoir thickness, ft
        phi  : Porosity, fraction
        swi  : Initial water saturation, fraction
        bgi  : Initial gas FVF, ft³/SCF
        bga  : Gas FVF at abandonment, ft³/SCF

    Returns:
        Gp : Cumulative gas produced at abandonment, SCF

    Raises:
        ValueError: if bgi <= 0, bga <= 0, swi >= 1, or geometry invalid
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    if bga <= 0:
        raise ValueError("Bga must be greater than zero.")
    if swi >= 1:
        raise ValueError("Swi must be less than 1.")
    if area <= 0:
        raise ValueError("Reservoir area must be greater than zero.")
    if h <= 0:
        raise ValueError("Reservoir thickness must be greater than zero.")
    if phi <= 0:
        raise ValueError("Porosity must be greater than zero.")

    hcpv = 43560 * area * h * phi * (1 - swi)
    return hcpv * ((1 / bgi) - (1 / bga))


# =============================================================================
# SECTION 3 — p/z METHOD
# Handout Pages 10–11
# p/z = pi/zi - (pi/zi) * (1/G) * Gp  →  linear: slope = -pi/(zi*G)
# =============================================================================

def calc_pz(p: float, z: float) -> float:
    """
    Calculate p/z ratio at a given pressure and z-factor.

    Formula (Handout p.10):
        p/z = p / z

    Used as the y-axis value in the p/z vs Gp straight-line plot.
    Extrapolation to p/z = 0 gives G (gas-in-place).

    Args:
        p : Reservoir pressure, psia
        z : Gas deviation (compressibility) factor, dimensionless

    Returns:
        pz : p/z ratio, psia

    Raises:
        ValueError: if z <= 0 or p <= 0
    """
    if p <= 0:
        raise ValueError("Pressure must be greater than zero.")
    if z <= 0:
        raise ValueError("Z-factor must be greater than zero.")
    return p / z


def calc_g_from_pz(pi: float, zi: float, p: float, z: float, gp: float) -> float:
    """
    Estimate Gas-in-Place (G) from two p/z data points using the linear MBE.

    Formula (Handout p.10–11):
        p/z = pi/zi - (pi/zi * 1/G) * Gp
        Rearranged for G given one production point:
        G = (pi/zi) * Gp / (pi/zi - p/z)

    This is equivalent to finding where the straight line through
    (0, pi/zi) and (Gp, p/z) intersects the x-axis (p/z = 0).

    Args:
        pi : Initial reservoir pressure, psia
        zi : Initial gas z-factor, dimensionless
        p  : Current reservoir pressure, psia
        z  : Current gas z-factor, dimensionless
        gp : Cumulative gas produced at current pressure, SCF

    Returns:
        G : Estimated gas-in-place, SCF

    Raises:
        ValueError: if pi/zi == p/z (no depletion) or any input invalid
    """
    if pi <= 0 or zi <= 0 or p <= 0 or z <= 0:
        raise ValueError("Pressure and z-factor values must be greater than zero.")
    if gp < 0:
        raise ValueError("Cumulative gas production (Gp) cannot be negative.")

    pz_i = pi / zi
    pz   = p / z
    denom = pz_i - pz

    if denom == 0:
        raise ValueError(
            "pi/zi equals p/z — no pressure depletion detected. "
            "Cannot estimate G without measurable production."
        )
    return pz_i * gp / denom


# =============================================================================
# SECTION 4 — HAVLENA-ODEH TERMS FOR GAS
# Handout Page 12
# F = G*(Eg + Efw) + We
# =============================================================================

def calc_f_gas(gp: float, bg: float, wp: float, bw: float) -> float:
    """
    Total underground withdrawal (F) for gas reservoir.

    Formula (Handout p.12):
        F = Gp * Bg + Wp * Bw

    Args:
        gp : Cumulative gas produced, SCF
        bg : Current gas FVF, rb/SCF
        wp : Cumulative water produced, STB
        bw : Water FVF, rb/STB

    Returns:
        F : Total withdrawal, rb
    """
    return gp * bg + wp * bw


def calc_eg_gas(bg: float, bgi: float) -> float:
    """
    Gas expansion term (Eg) — Havlena-Odeh gas form.

    Formula (Handout p.12):
        Eg = Bg - Bgi

    Note: This is different from the oil Eg (calc_eg in oil_mbe.py),
    which uses Boi*(Bg/Bgi - 1). This form is specific to gas reservoirs.

    Args:
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF

    Returns:
        Eg : Gas expansion term, rb/SCF

    Raises:
        ValueError: if bgi <= 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    return bg - bgi


def calc_efw_gas(bgi: float, swi: float, cw: float, cf: float, dp: float) -> float:
    """
    Formation rock and connate water expansion term (Ef,w) for gas reservoir.

    Formula (Handout p.12):
        Ef,w = Bgi * ((Swi*cw + cf) / (1 - Swi)) * delta_P

    Note: Unlike the oil Efw, there is no (1 + m) factor here — gas
    reservoirs don't have a separate oil zone to account for.

    Args:
        bgi : Initial gas FVF, rb/SCF
        swi : Initial water saturation, fraction
        cw  : Water compressibility, psi^-1
        cf  : Formation compressibility, psi^-1
        dp  : Pressure drop (Pi - P), psi

    Returns:
        Ef,w : Rock/water expansion term, rb/SCF

    Raises:
        ValueError: if swi >= 1
    """
    if swi >= 1:
        raise ValueError("Swi must be less than 1.")
    return bgi * ((swi * cw + cf) / (1 - swi)) * dp


# =============================================================================
# SECTION 5 — GENERAL Bg-BASED MBE (full form)
# Handout Page 11
# G = (Gp*Bg - (We - Wp*Bw)) / (Bg - Bgi + Bgi*(Swi*cw+cf)/(1-Swi)*dp)
# All sub-cases below are derived/simplified from this.
# =============================================================================

def solve_g_general(gp: float, bg: float, bgi: float,
                    we: float, wp: float, bw: float,
                    swi: float, cw: float, cf: float, dp: float) -> float:
    """
    Solve for Gas-in-Place (G) — full general Bg-based MBE.

    Formula (Handout p.11):
        G = (Gp*Bg - (We - Wp*Bw)) / (Bg - Bgi + Bgi*(Swi*cw+cf)/(1-Swi)*dp)

    This is the parent equation. All sub-cases (no water, with water,
    overpressured) are simplifications of this formula.

    Args:
        gp  : Cumulative gas produced, SCF
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF
        we  : Cumulative water influx, rb
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB
        swi : Initial water saturation, fraction
        cw  : Water compressibility, psi^-1
        cf  : Formation compressibility, psi^-1
        dp  : Pressure drop (Pi - P), psi

    Returns:
        G : Gas-in-place, SCF

    Raises:
        ValueError: if bgi <= 0, swi >= 1, or denominator is zero
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    if swi >= 1:
        raise ValueError("Swi must be less than 1.")

    eg  = calc_eg_gas(bg, bgi)
    efw = calc_efw_gas(bgi, swi, cw, cf, dp)
    denom = eg + efw

    if denom == 0:
        raise ValueError(
            "Denominator (Eg + Efw) is zero. "
            "Check Bg, Bgi, compressibility, and pressure drop inputs."
        )

    numer = gp * bg - (we - wp * bw)
    return numer / denom


def solve_g_no_water(gp: float, bg: float, bgi: float) -> float:
    """
    Solve for Gas-in-Place (G) — no bottom water, no rock/water expansion.

    Formula (Handout p.12):
        G = Gp * Bg / (Bg - Bgi)

    Simplification: We = 0, Wp = 0, Efw neglected.

    Havlena-Odeh linear form:
        F = G * Eg  →  Gp*Bg = G*(Bg - Bgi)

    Args:
        gp  : Cumulative gas produced, SCF
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF

    Returns:
        G : Gas-in-place, SCF

    Raises:
        ValueError: if bgi <= 0 or (Bg - Bgi) == 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")

    eg = calc_eg_gas(bg, bgi)

    if eg == 0:
        raise ValueError(
            "Gas expansion (Bg - Bgi) is zero. "
            "No pressure depletion detected — cannot solve for G."
        )

    return (gp * bg) / eg


def solve_g_with_water(gp: float, bg: float, bgi: float,
                       we: float, wp: float, bw: float) -> float:
    """
    Solve for Gas-in-Place (G) — with bottom water, no rock/water expansion.

    Formula (Handout p.13):
        G = (Gp*Bg - (We - Wp*Bw)) / (Bg - Bgi)

    Simplification: Efw neglected (not overpressured).

    Havlena-Odeh linear form:
        F = G*Eg + We  →  Gp*Bg + Wp*Bw = G*(Bg - Bgi) + We

    Args:
        gp  : Cumulative gas produced, SCF
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF
        we  : Cumulative water influx, rb
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB

    Returns:
        G : Gas-in-place, SCF

    Raises:
        ValueError: if bgi <= 0 or (Bg - Bgi) == 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")

    eg = calc_eg_gas(bg, bgi)

    if eg == 0:
        raise ValueError(
            "Gas expansion (Bg - Bgi) is zero. "
            "No pressure depletion detected — cannot solve for G."
        )

    return (gp * bg - (we - wp * bw)) / eg


def solve_g_overpressured(gp: float, bg: float, bgi: float,
                          we: float, wp: float, bw: float,
                          swi: float, cw: float, cf: float, dp: float) -> float:
    """
    Solve for Gas-in-Place (G) — with bottom water AND rock/water expansion.

    Formula (Handout p.13):
        G = (Gp*Bg - (We - Wp*Bw)) / (Bg - Bgi + Bgi*(Swi*cw+cf)/(1-Swi)*dp)

    Used for overpressured reservoirs where rock/connate water expansion
    contributes meaningfully to production (Efw cannot be neglected).

    Havlena-Odeh linear form:
        F = G*(Eg + Efw) + We

    Args:
        gp  : Cumulative gas produced, SCF
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF
        we  : Cumulative water influx, rb
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB
        swi : Initial water saturation, fraction
        cw  : Water compressibility, psi^-1
        cf  : Formation compressibility, psi^-1
        dp  : Pressure drop (Pi - P), psi

    Returns:
        G : Gas-in-place, SCF

    Raises:
        ValueError: if bgi <= 0, swi >= 1, or denominator is zero
    """
    # Delegates to general form — identical equation, just named
    # separately so the UI can label it correctly and set Efw != 0
    return solve_g_general(gp, bg, bgi, we, wp, bw, swi, cw, cf, dp)


# =============================================================================
# SECTION 6 — REVERSE SOLVERS (G known, solve for other unknowns)
# Derived from: F = G*(Eg + Efw) + We
# Mirrors the oil_mbe.py pattern for the UI's "what are we looking for?" flow
# =============================================================================

def solve_we_gas(gp: float, bg: float, bgi: float, g: float,
                 wp: float, bw: float,
                 swi: float = 0.0, cw: float = 0.0,
                 cf: float = 0.0, dp: float = 0.0) -> float:
    """
    Solve for Water Influx (We) given G.

    Rearranged from F = G*(Eg + Efw) + We:
        We = F - G*(Eg + Efw)
           = Gp*Bg + Wp*Bw - G*(Bg - Bgi + Efw)

    Args:
        gp  : Cumulative gas produced, SCF
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF
        g   : Known gas-in-place, SCF
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB
        swi : Initial water saturation, fraction (0 if Efw neglected)
        cw  : Water compressibility, psi^-1 (0 if Efw neglected)
        cf  : Formation compressibility, psi^-1 (0 if Efw neglected)
        dp  : Pressure drop (Pi - P), psi (0 if Efw neglected)

    Returns:
        We : Water influx, rb
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")

    f   = calc_f_gas(gp, bg, wp, bw)
    eg  = calc_eg_gas(bg, bgi)
    efw = calc_efw_gas(bgi, swi, cw, cf, dp) if swi > 0 else 0.0

    return f - g * (eg + efw)


def solve_gp_gas(g: float, bg: float, bgi: float,
                 we: float, wp: float, bw: float,
                 swi: float = 0.0, cw: float = 0.0,
                 cf: float = 0.0, dp: float = 0.0) -> float:
    """
    Solve for Cumulative Gas Production (Gp) given G.

    Rearranged from F = G*(Eg + Efw) + We:
        Gp*Bg = G*(Eg + Efw) + We - Wp*Bw
        Gp = (G*(Eg + Efw) + We - Wp*Bw) / Bg

    Args:
        g   : Known gas-in-place, SCF
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF
        we  : Cumulative water influx, rb
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB
        swi : Initial water saturation, fraction (0 if Efw neglected)
        cw  : Water compressibility, psi^-1 (0 if Efw neglected)
        cf  : Formation compressibility, psi^-1 (0 if Efw neglected)
        dp  : Pressure drop (Pi - P), psi (0 if Efw neglected)

    Returns:
        Gp : Cumulative gas production, SCF

    Raises:
        ValueError: if bg == 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    if bg == 0:
        raise ValueError("Bg cannot be zero when solving for Gp.")

    eg  = calc_eg_gas(bg, bgi)
    efw = calc_efw_gas(bgi, swi, cw, cf, dp) if swi > 0 else 0.0

    return (g * (eg + efw) + we - wp * bw) / bg


def solve_wp_gas(g: float, gp: float, bg: float, bgi: float,
                 we: float, bw: float,
                 swi: float = 0.0, cw: float = 0.0,
                 cf: float = 0.0, dp: float = 0.0) -> float:
    """
    Solve for Cumulative Water Production (Wp) given G.

    Rearranged from F = G*(Eg + Efw) + We:
        Gp*Bg + Wp*Bw = G*(Eg + Efw) + We
        Wp = (G*(Eg + Efw) + We - Gp*Bg) / Bw

    Args:
        g   : Known gas-in-place, SCF
        gp  : Cumulative gas produced, SCF
        bg  : Current gas FVF, rb/SCF
        bgi : Initial gas FVF, rb/SCF
        we  : Cumulative water influx, rb
        bw  : Water FVF, rb/STB
        swi : Initial water saturation, fraction (0 if Efw neglected)
        cw  : Water compressibility, psi^-1 (0 if Efw neglected)
        cf  : Formation compressibility, psi^-1 (0 if Efw neglected)
        dp  : Pressure drop (Pi - P), psi (0 if Efw neglected)

    Returns:
        Wp : Cumulative water production, STB

    Raises:
        ValueError: if bw == 0
    """
    if bgi <= 0:
        raise ValueError("Bgi must be greater than zero.")
    if bw == 0:
        raise ValueError("Bw cannot be zero when solving for Wp.")

    eg  = calc_eg_gas(bg, bgi)
    efw = calc_efw_gas(bgi, swi, cw, cf, dp) if swi > 0 else 0.0

    return (g * (eg + efw) + we - gp * bg) / bw


# =============================================================================
# SECTION 7 — DRIVE INDICES FOR GAS
# Derived from Havlena-Odeh: F = G*(Eg + Efw) + We
# GEI + EDI + WDI must sum to 1.0
# =============================================================================

def calc_drive_indices_gas(g: float, eg: float, efw: float,
                           we: float, wp: float, bw: float,
                           f: float) -> dict:
    """
    Calculate gas reservoir drive mechanism indices.

    Definitions:
        GEI = G*Eg / F          (Gas Expansion Index)
        EDI = G*Efw / F         (Expansion/Rock-Water Drive Index)
        WDI = (We - Wp*Bw) / F  (Water Drive Index)

    GEI + EDI + WDI must sum to 1.0 for a consistent solution.

    Args:
        g   : Gas-in-place, SCF
        eg  : Gas expansion term (Bg - Bgi), rb/SCF
        efw : Rock/water expansion term, rb/SCF (0 if neglected)
        we  : Cumulative water influx, rb
        wp  : Cumulative water produced, STB
        bw  : Water FVF, rb/STB
        f   : Total withdrawal (Gp*Bg + Wp*Bw), rb

    Returns:
        dict with keys: gei, edi, wdi, total
        (total should equal 1.0 if inputs are consistent)

    Raises:
        ValueError: if f is zero
    """
    if f == 0:
        raise ValueError("Total withdrawal (F) cannot be zero.")

    gei = max(0.0, (g * eg) / f)
    edi = max(0.0, (g * efw) / f)
    wdi = max(0.0, (we - wp * bw) / f)

    total = gei + edi + wdi
    if total == 0:
        raise ValueError("Drive indices cannot be normalized because all contributions are zero.")

    gei /= total
    edi /= total
    wdi /= total

    return {
        "gei": gei,
        "edi": edi,
        "wdi": wdi,
        "total": gei + edi + wdi
    }