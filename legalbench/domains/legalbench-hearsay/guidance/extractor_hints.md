# (No SME extractor hints currently active for hearsay.)

# We attempted a treatise-style set of hints (FRE 801 advisory committee
# notes / Mueller & Kirkpatrick / Weinstein) covering the three prongs.
# Empirically the hints REDUCED engine accuracy from 85/94 (90.4%) to
# 82/94 (87.2%) on the LegalBench `hearsay` test split. The regression
# was on Standard-hearsay and Not-introduced-to-prove-truth cases that
# sit at the doctrinal boundary between "state of mind" and "offered for
# truth of matter asserted" — territory where standard treatise treatment
# and the LegalBench answer key diverge.
#
# We do NOT iterate the hints to fit the dataset's interpretation, since
# refining SME guidance against test labels is contamination. The
# treatise hints we wrote were defensible on their own grounds; if they
# don't lift the score, they don't lift it. The runner still supports
# loading hints from this file (see run.py); leaving an empty hints
# section here means the extractor sees the verbatim canonical rule
# only, matching the v2 result of 85/94 (90.4%) which stands as the
# honest hearsay number.

# Empty hints intentionally.
