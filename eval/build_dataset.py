"""Builds eval/dataset.jsonl: the SEEDED answer key for the guardrail-panel eval.

It is synthetic. Every case starts from a clean asset written against Northwind's
context files, then changes one thing (or applies the VP's edits). The answer key
(expected verdict + the rule IDs that should fire) was written by hand from
context/approved_claims.md, brand_voice.md, regulations.md, channel_specs.json
and brief_mandatories.json. It is not a held-out set: the same people wrote the
rules and the cases.

  python eval/build_dataset.py
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).parent

EMAIL_IMAGE = {"file": "email-01.png", "size": [1200, 600], "ai_disclosure": "AI-generated image",
               "alt_text": "Hiker in a hooded rain shell on a wet forest trail, water beading on the fabric"}
RDA_IMAGE = {"file": "rda-01.png", "size": [1200, 628], "ai_disclosure": "AI-generated image",
             "alt_text": "Hood-up hiker on a wet forest trail in steady rain; water beads on the shell fabric"}

BASES = {
    "email": {"channel": "email", "image": EMAIL_IMAGE, "copy": {
        "subject": "Stay dry from both sides",
        "preheader": "Rain stays out, you stay dry inside. Fully taped seams and pit zips for venting.",
        "body": ("Wet trail, long day out. The Cascade Shell is waterproof, rated to 20,000 mm, and breathable, "
                 "rated to 15,000 g/m²/24h. Fully taped seams. Pit zips for venting. A helmet-compatible hood. "
                 "The face fabric is made from 100% recycled nylon.\n\nThe Cascade Shell is $249. Built to be "
                 "repaired, and backed by the Northwind Repair Promise. Terms at northwind.example/repair."),
        "cta_text": "Shop the Cascade Shell",
        "footer": "Northwind, {{postal_address}} | Unsubscribe: {{unsubscribe_link}}"}},
    "google_rda": {"channel": "google_rda", "image": RDA_IMAGE, "copy": {
        "short_headline": "Stay dry from both sides",
        "long_headline": "Rain stays out, you stay dry inside, rated to 20,000 mm and 15,000 g/m²/24h",
        "description": "Face fabric 100% recycled nylon. DWR made without intentionally added PFAS.",
        "business_name": "Northwind"}},
    "google_rsa": {"channel": "google_rsa", "copy": {
        "headlines": ["Stay dry from both sides", "Built to be repaired", "Waterproof, rated to 20,000 mm",
                      "Fully taped seams", "Pit zips for venting", "Helmet-compatible hood"],
        "descriptions": ["Waterproof, rated to 20,000 mm. Breathable, rated to 15,000 g/m²/24h.",
                         "Face fabric made from 100% recycled nylon. Fully taped seams and pit zips."],
        "paths": ["jackets", "cascade"]}},
}

PLACEMENT = {"email": "Launch email", "google_rda": "Google Display ad", "google_rsa": "Google Search ad"}


def case(case_id, channel, kind, expected_verdict, expected_rules, note, edits=None, image_edits=None, family=None):
    asset = copy.deepcopy(BASES[channel])
    for field, value in (edits or {}).items():
        if isinstance(value, tuple):  # (index, text): replace one item of a list field
            asset["copy"][field][value[0]] = value[1]
        else:
            asset["copy"][field] = value
    if image_edits:
        asset["image"].update(image_edits)
    return {"case_id": case_id, "kind": kind, "rule_family": family or (expected_rules[0].split("-")[0] if expected_rules else "clean"),
            "placement": PLACEMENT[channel], "expected_verdict": expected_verdict, "expected_rules": expected_rules,
            "note": note, "asset": {"asset_id": case_id, **asset}}


CASES = [
    # ---------- clean: should pass (tests false blocks) ----------
    case("C01", "email", "clean", "pass", [], "Clean launch email built only from approved claims and lines"),
    case("C02", "google_rda", "clean", "pass", [], "Clean display ad (the agents' version that auto-passed)"),
    case("C03", "google_rsa", "clean", "pass", [], "Clean search ad, approved claims only"),
    case("C04", "google_rda", "clean", "pass", [], "Weight quoted correctly with the size (CL-08)", family="CL",
         edits={"description": "Weighs 380 g (men's M). Face fabric made from 100% recycled nylon."}),
    case("C05", "google_rda", "clean", "pass", [], "Repair Promise with a pointer to the terms (CL-09)", family="CL",
         edits={"long_headline": "Backed by the Northwind Repair Promise. Terms at northwind.example/repair"}),
    case("C06", "google_rsa", "clean", "pass", [], "PFAS claim with the required 'intentionally added' (CL-04)", family="CL",
         edits={"descriptions": (1, "Water-repellent finish made without intentionally added PFAS.")}),
    case("C07", "email", "clean", "pass", [], "Dry, understated humor, on voice (BV-07)", family="BV",
         edits={"subject": "Your old rain jacket had a good run"}),
    case("C08", "google_rda", "clean", "pass", [], "Plain benefit words without numbers are allowed (CL-01/CL-02)", family="CL",
         edits={"short_headline": "Waterproof. Breathable."}),
    case("C09", "google_rda", "clean", "pass", [], "Both approved messaging lines (AM-01, AM-02)", family="AM",
         edits={"long_headline": "Rain stays out, you stay dry inside. Built to be repaired."}),

    # ---------- claims & regulatory: should block ----------
    case("V01", "google_rda", "violating", "block", ["CL-P01", "CL-01", "REG-01"], "Absolute waterproof claim",
         edits={"long_headline": "100% waterproof shell for long wet days on the trail"}),
    case("V02", "google_rda", "violating", "block", ["CL-P02", "CL-03", "REG-03"], "Whole jacket called recycled",
         edits={"description": "A 100% recycled jacket built for wet trails and long days."}),
    case("V03", "google_rsa", "violating", "block", ["CL-P03", "REG-02", "BV-10"], "Unqualified environmental claim",
         edits={"descriptions": (0, "An eco-friendly rain shell for wet trails and long days out.")}),
    case("V04", "google_rda", "violating", "block", ["CL-P04", "REG-05", "CL-09"], "Guarantee without terms",
         edits={"long_headline": "Guaranteed for life. The rain shell built for wet trails."}),
    case("V05", "google_rsa", "violating", "block", ["CL-P05", "REG-01", "BV-03"], "Unsubstantiated superlative",
         edits={"headlines": (0, "The most breathable shell")}),
    case("V06", "google_rda", "violating", "block", ["CL-P06", "REG-04", "CL-04"], "Chemical-free / non-toxic",
         edits={"description": "Chemical-free and non-toxic, with fully taped seams throughout."}),
    case("V07", "email", "violating", "block", ["CL-P07", "REG-06", "CL-P05"], "Invented testimonial",
         edits={"body": "\"Best jacket I've owned,\" says one trail guide. " + BASES["email"]["copy"]["body"]}),
    case("V08", "google_rda", "violating", "block", ["CL-P08", "REG-07"], "Made in USA, not substantiated",
         edits={"short_headline": "Made in USA"}),
    case("V09", "google_rsa", "violating", "block", ["CL-01", "CL-02", "REG-01"], "Numbers quoted without 'rated to'",
         edits={"descriptions": (0, "Waterproof to 20,000 mm and breathable to 15,000 g/m²/24h on wet days.")}),
    case("V10", "google_rda", "violating", "block", ["CL-08", "REG-01"], "Weight quoted without the size",
         edits={"description": "Weighs just 380 g, with fully taped seams and pit zips for venting."}),
    case("V11", "email", "violating", "block", ["AM-01", "CL-P01", "REG-01", "CL-02"], "Implies the wearer won't sweat",
         edits={"preheader": "Rain stays out and you'll never sweat again. Fully taped seams throughout."}),
    case("V22", "email", "violating", "block", ["BR-01", "CL-10"], "Wrong price vs. the brief ($229 vs $249)",
         edits={"body": BASES["email"]["copy"]["body"].replace("$249", "$229")}),

    # ---------- brand voice: should block ----------
    case("V12", "google_rda", "violating", "block", ["BV-04"], "Urgency tricks",
         edits={"description": "Hurry! Last chance to grab the Cascade Shell before it's gone."}),
    case("V13", "google_rda", "violating", "block", ["BV-05"], "Conquest language",
         edits={"long_headline": "Conquer the storm and dominate every ridgeline this fall"}),
    case("V14", "email", "violating", "block", ["BV-08"], "ALL CAPS and multiple exclamation marks",
         edits={"subject": "STAY DRY FROM BOTH SIDES!!"}),
    case("V15", "google_rsa", "violating", "block", ["BV-09"], "Exclusionary language",
         edits={"headlines": (1, "Built for weekend warriors")}),

    # ---------- channel specs, email law, accessibility (code checks): should block ----------
    case("V16", "email", "violating", "block", ["REG-08"], "Footer missing the unsubscribe link",
         edits={"footer": "Northwind, {{postal_address}}"}),
    case("V17", "email", "violating", "block", ["CH-EM-01"], "Subject over 50 characters",
         edits={"subject": "Stay dry from both sides on every wet weekend trail this fall"}),
    case("V18", "google_rda", "violating", "block", ["CH-RDA-01"], "Short headline over 30 characters",
         edits={"short_headline": "Stay dry from both sides on the trail"}),
    case("V19", "google_rda", "violating", "block", ["ACC-01"], "Missing alt text", image_edits={"alt_text": ""}),
    case("V20", "email", "violating", "block", ["ACC-03"], "Vague link text", edits={"cta_text": "Click here"}),
    case("V21", "google_rda", "violating", "block", ["REG-09"], "Missing AI-generated image disclosure",
         image_edits={"ai_disclosure": None}),

    # ---------- the demo scenario: VP of Sales edits ----------
    case("VP1", "google_rda", "violating", "block", ["CL-P02", "CL-P04", "CL-P05", "BV-04", "CL-04", "REG-03", "REG-05"],
         "VP edits, display ad", family="VP",
         edits={"long_headline": "100% recycled jacket. PFAS-free. Guaranteed for life.",
                "description": "The best rain jacket we've ever made. Hurry, launch stock won't last!"}),
    case("VP2", "email", "violating", "block", ["CL-P01", "CL-P04", "REG-08", "BR-01", "BV-08"],
         "VP edits, launch email", family="VP",
         edits={"subject": "100% WATERPROOF. GUARANTEED FOR LIFE!!!", "footer": "Northwind, {{postal_address}}",
                "preheader": "Launch week price: $229. Stay dry from both sides on every hike."}),

    # ---------- should warn, not block ----------
    case("W01", "google_rda", "warn_only", "warn", ["CH-MIN"], "Description under the 50-character house minimum",
         edits={"description": "Face fabric: 100% recycled nylon."}),
    case("W02", "email", "warn_only", "warn", ["BV-02"], "One long, clause-chained sentence (BV-02)",
         edits={"body": ("The Cascade Shell is waterproof, rated to 20,000 mm, and breathable, rated to 15,000 g/m²/24h, "
                         "and it has fully taped seams and pit zips for venting and a helmet-compatible hood and a face "
                         "fabric made from 100% recycled nylon, and it is $249 and built to be repaired and backed by the "
                         "Northwind Repair Promise, with terms at northwind.example/repair.")}),
]


if __name__ == "__main__":
    out = HERE / "dataset.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for c in CASES:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    kinds = {}
    for c in CASES:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print(f"Wrote {len(CASES)} cases to {out}: {kinds}")
