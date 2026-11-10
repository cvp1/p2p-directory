"""Centre -> dial conversion per mode, as Pat v1.0.0 sets the rig
(app/freq.go:68-92: "fm" modes unshifted; pactor/ardop/vara -1500 Hz)."""
from testlib import check, done
import p2pdir

CASES = [("VARA_HF", 7103.5, 7102.0), ("ARDOP", 7101.5, 7100.0), ("PACTOR", 14108, 14106.5),
         ("VARA_FM", 145050, 145050), ("PACKET", 145090, 145090), ("PACKET", 10147.3, 10147.3),
         ("ROBUST_PACKET", 10147.3, None)]
for mode, centre, dial in CASES:
    got = p2pdir.dial_khz(centre, mode)
    check(f"{mode} {centre} -> {dial}", got == dial, str(got))
check("every mode has a rule or an explicit None", set(p2pdir.MODES) == {m for m, _, _ in CASES})
check("unknown mode gives None", p2pdir.dial_khz(7100, "FT8") is None)
done()
