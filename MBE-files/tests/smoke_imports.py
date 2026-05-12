# tests/smoke_imports.py
import sys
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]  # repo root
# Ensure repo root and MBE-files folder are importable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "MBE-files"))

# Import by package path if packages exist
try:
    from calc import oil_mbe, pvt
    from utils import helpers
    print("Imported calc.oil_mbe, calc.pvt, utils.helpers")
except Exception as e:
    print("Package import failed, trying file-based imports:", e)
    # file-based fallback
    spec = importlib.util.spec_from_file_location("oil_mbe", str(ROOT / "MBE-files" / "calc" / "oil_mbe.py"))
    oil_mbe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oil_mbe)
    spec2 = importlib.util.spec_from_file_location("pvt", str(ROOT / "MBE-files" / "calc" / "pvt.py"))
    pvt = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(pvt)
    spec3 = importlib.util.spec_from_file_location("helpers", str(ROOT / "MBE-files" / "utils" / "helpers.py"))
    helpers = importlib.util.module_from_spec(spec3)
    spec3.loader.exec_module(helpers)
    print("Loaded modules via file import")

# Quick function calls
print("calc_volumetric_ooip sample:", oil_mbe.calc_volumetric_ooip(1000, 0.2, 0.2, 1.2))
print("calc_bgi_from_pvt sample:", pvt.calc_bgi_from_pvt(0.9, 520, 3000))
print("calc_afactor_bo_rs sample:", helpers.calc_afactor_bo_rs(1.2, 500, 100, 0.003))