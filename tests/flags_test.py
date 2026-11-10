"""97.221(b) flag: by occupied band edge, US-looking calls, auto only; flagged
entries are still published."""
from testlib import check, done
import p2pdir


def flags(call, freq, mode="VARA_HF", width=500, control="auto"):
    row = p2pdir.parse_listing(f"P2PDIR 1\ngrid: EM12\nentry: {freq} {mode} {width} {control} 24/7\n", call)
    return row["entries"][0]["flags"]


F = [p2pdir.FLAG_HF_AUTO]
check("nine segments are defined", len(p2pdir.AUTO_SEGMENTS_KHZ) == 9)
for lo, hi in p2pdir.AUTO_SEGMENTS_KHZ:
    mid = round((lo + hi) / 2, 3)
    width = 500 if hi - lo >= 1 else 200
    mode = "VARA_HF" if width == 500 else "ARDOP"
    check(f"centre of {lo}-{hi} not flagged", flags("N9ABC", mid, mode, width) == [])
    check(f"just below {lo} flagged", flags("N9ABC", round(lo - 0.3, 3), mode, width) == F)
check("centre inside, edge outside: flagged", flags("N9ABC", 7104.8) == F)
check("edge exactly on the segment edge: not flagged", flags("N9ABC", 7104.75) == [])
check("a 2300 Hz signal centred in a 5 kHz segment is fine", flags("N9ABC", 7102.5, width=2300) == [])
check("a 2750 Hz signal does not fit 18105-18110 off-centre", flags("N9ABC", 18106, width=2750) == F)
check("attended is never flagged", flags("N9ABC", 7090, control="attended") == [])
check("sked is never flagged", flags("N9ABC", 7090, control="sked") == [])
check("non-US call not flagged", flags("VE3XYZ", 7090) == [])
for call in ("K1ABC", "W1AW", "N9ABC", "AA1A", "AL7XX"):
    check(f"{call} counts as US", flags(call, 7090) == F)
check("AM1A is not a US prefix", flags("AM1A", 7090) == [])
check("6 m auto never flagged", flags("N9ABC", 50300) == [])
check("2 m packet auto never flagged", flags("N9ABC", 145090, "PACKET", 1200) == [])
check("HF packet uses 500 Hz occupied width", flags("N9ABC", 14099.4, "PACKET", 300) == F)
check("HF packet inside a segment not flagged", flags("N9ABC", 14098, "PACKET", 300) == [])
row = p2pdir.parse_listing("P2PDIR 1\ngrid: EM12\nentry: 7090 VARA_HF 500 auto 24/7\n", "N9ABC")
check("a flagged entry is still published", len(row["entries"]) == 1)
done()
