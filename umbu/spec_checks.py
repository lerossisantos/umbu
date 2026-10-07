"""Deterministic checks: channel specs + accessibility + AI disclosure.
No model involved. A limit is either met or it isn't, so code is cheaper,
faster and 100% repeatable here."""
import json

from PIL import Image

from umbu.context import CONTEXT_DIR

SPECS = json.loads((CONTEXT_DIR / "channel_specs.json").read_text(encoding="utf-8"))


def _finding(rule_id, field, message, severity="block"):
    return {"checker": "channel_spec", "rule_id": rule_id, "field": field,
            "issue": message, "severity": severity}


def _max_chars(findings, rule_id, field, text, limit):
    if text is None or text == "":
        findings.append(_finding(rule_id, field, "Missing"))
    elif len(text) > limit:
        findings.append(_finding(rule_id, field, f"{len(text)} characters, limit is {limit}: \"{text}\""))


def _check_rsa(copy, f):
    s = SPECS["google_rsa"]
    heads, descs, paths = copy.get("headlines", []), copy.get("descriptions", []), copy.get("paths", [])
    if not s["headlines"]["min_count"] <= len(heads) <= s["headlines"]["max_count"]:
        f.append(_finding("CH-RSA-01", "headlines", f"{len(heads)} headlines, need 3-15"))
    for i, h in enumerate(heads, 1):
        _max_chars(f, "CH-RSA-01", f"headline {i}", h, s["headlines"]["max_chars"])
    if len(set(h.lower() for h in heads)) < len(heads):
        f.append(_finding("CH-RSA-04", "headlines", "Duplicate headlines"))
    if not s["descriptions"]["min_count"] <= len(descs) <= s["descriptions"]["max_count"]:
        f.append(_finding("CH-RSA-02", "descriptions", f"{len(descs)} descriptions, need 2-4"))
    for i, d in enumerate(descs, 1):
        _max_chars(f, "CH-RSA-02", f"description {i}", d, s["descriptions"]["max_chars"])
    for i, p in enumerate(paths[: s["paths"]["max_count"]], 1):
        _max_chars(f, "CH-RSA-03", f"path {i}", p, s["paths"]["max_chars"])


def _check_rda(copy, f):
    s = SPECS["google_rda"]
    _max_chars(f, "CH-RDA-01", "short_headline", copy.get("short_headline"), s["short_headline"]["max_chars"])
    _max_chars(f, "CH-RDA-02", "long_headline", copy.get("long_headline"), s["long_headline"]["max_chars"])
    _max_chars(f, "CH-RDA-03", "description", copy.get("description"), s["description"]["max_chars"])
    _max_chars(f, "CH-RDA-04", "business_name", copy.get("business_name"), s["business_name"]["max_chars"])


def _check_email(copy, f):
    s = SPECS["email"]
    _max_chars(f, "CH-EM-01", "subject", copy.get("subject"), s["subject"]["max_chars"])
    pre = copy.get("preheader", "")
    if not s["preheader"]["min_chars"] <= len(pre) <= s["preheader"]["max_chars"]:
        f.append(_finding("CH-EM-02", "preheader", f"{len(pre)} characters, need 40-100"))
    words = len(copy.get("body", "").split())
    if words > s["body"]["max_words"]:
        f.append(_finding("CH-EM-04", "body", f"{words} words, limit is {s['body']['max_words']}"))
    if not copy.get("cta_text"):
        f.append(_finding("CH-EM-05", "cta_text", "Missing CTA"))
    footer = copy.get("footer", "")
    if "{{postal_address}}" not in footer:
        f.append(_finding("REG-08", "footer", "Missing physical postal address (CAN-SPAM)"))
    if "{{unsubscribe_link}}" not in footer:
        f.append(_finding("REG-08", "footer", "Missing unsubscribe link (CAN-SPAM)"))


def _check_image(asset, run_dir, f):
    image = asset.get("image")
    if not image:
        return
    acc = SPECS["accessibility"]
    alt = image.get("alt_text", "")
    if not alt:
        f.append(_finding("ACC-01", "alt_text", "Missing alt text"))
    elif len(alt) > acc["alt_text"]["max_chars"]:
        f.append(_finding("ACC-01", "alt_text", f"{len(alt)} characters, limit is {acc['alt_text']['max_chars']}"))
    if image.get("ai_disclosure") != "AI-generated image":
        f.append(_finding("REG-09", "image", "Missing 'AI-generated image' disclosure"))
    path = run_dir / image["file"]
    if not path.exists():
        f.append(_finding("CH-IMG", "image", "Image file not found"))
        return
    with Image.open(path) as im:
        size = list(im.size)
    if size != list(image["size"]):
        f.append(_finding("CH-IMG", "image", f"Image is {size[0]}x{size[1]}, spec is {image['size'][0]}x{image['size'][1]}"))
    kb = path.stat().st_size / 1024
    if asset["channel"] == "google_rda" and kb > SPECS["google_rda"]["images"]["max_file_kb"]:
        f.append(_finding("CH-RDA-07", "image", f"{kb:.0f} KB, limit is 5120 KB"))


def _check_cta(copy, f):
    cta = (copy.get("cta_text") or "").strip().lower()
    if cta in SPECS["accessibility"]["banned_link_text"]:
        f.append(_finding("ACC-03", "cta_text", f"Vague link text: \"{copy.get('cta_text')}\""))


def check_asset(asset: dict, run_dir) -> list[dict]:
    findings = []
    copy = asset["copy"]
    {"google_rsa": _check_rsa, "google_rda": _check_rda, "email": _check_email}[asset["channel"]](copy, findings)
    _check_cta(copy, findings)
    _check_image(asset, run_dir, findings)
    return findings
