from ingestion.web import parse_point, point_id, point_links

URL = "https://www.meine-tcm.com/en/acupuncture-points/acupuncture-point-tb-05/"

# Shaped like a meine-tcm.com point page; the content is invented.
PAGE = """
<html><head><script>var x = 1;</script></head><body>
<header><nav><a href="/">Home</a></nav></header>
<main>
  <div class="col-inner"><h1>Acupuncture Point Tb 05</h1></div>
  <h3>A test point for wrist comfort.</h3>
  <img src="lage.jpg" alt="Location graphic">
  <h4>Location:</h4>
  <p>Two finger-widths above the back of the wrist, between the bones.</p>
  <h2>Outer Test Gate — Wài Cè</h2>
  <p>A calming point, often combined with <a href="/x">Pe 06</a> for comfort.</p>
  <p>Second paragraph of description.</p>
  <div>Use: 30 seconds medium</div>
  <div>Name:</div><ul><li>Test name</li><li>Tb 05</li></ul>
  <h4>Helps with:</h4>
  <div>Wrist pain 1, <a href="/a">Wrist pain 2</a>, <a href="/b">Stiff neck</a>tired eyes</div>
  <span>Properties of the acupuncture point</span>
  <div>Meridian:</div><div><strong>Triple Burner</strong></div>
  <div>Element:</div><div>Fire</div>
  <div>Category:</div><div>Classical acupuncture point</div>
  <div>Effect from the point of view of TCM:</div>
  <ul><li>Relaxes the wrist</li><li>Calms the mind</li></ul>
  <div>Contraindication:</div><div>Pregnancy</div>
  <h2>Use:</h2>
  <div>AcuPen:</div><p>Press with the pen tip.</p>
  <div>Acupressure:</div>
  <p>Press the point with the thumb for 30 seconds.</p>
  <p>Repeat up to three times a day.</p>
  <p>These should of course have been clarified by a doctor.</p>
  <div>Acupuncture technique:</div><p>Needle 0.5 cun.</p>
</main>
<footer>Footer text</footer>
</body></html>
"""


def test_parse_point_extracts_curated_fields() -> None:
    point = parse_point(PAGE, URL)

    assert point.id == "TE5"
    assert point.name == "Outer Test Gate — Wài Cè"
    assert point.summary == "A test point for wrist comfort."
    assert point.location == "Two finger-widths above the back of the wrist, between the bones."
    assert point.description == [
        "A calming point, often combined with Pe 06 for comfort.",
        "Second paragraph of description.",
    ]
    # Numbered variants merge, and a missing comma after a link still splits items.
    assert point.helps_with == ["Wrist pain", "Stiff neck", "Tired eyes"]
    assert point.tcm_effects == ["Relaxes the wrist", "Calms the mind"]
    assert point.contraindication == "Pregnancy"
    assert point.instructions == [
        "Press the point with the thumb for 30 seconds.",
        "Repeat up to three times a day.",
    ]
    assert point.duration == "30 seconds"
    assert point.pressure == "Medium pressure"
    assert point.meridian == "Triple Burner"
    assert point.names == ["Test name", "Tb 05"]


def test_point_id_maps_slugs_to_who_and_extra_codes() -> None:
    assert point_id("lv-03", "Great Meeting") == "LR3"
    assert point_id("pc-06", "Inner Gate") == "PC6"
    assert point_id("ex-01", "Seal Hall — Yintang") == "EX-HN3"
    assert point_id("anmian", "Anmian") == "EX-ANMIAN"
    assert point_id("shou-jing-dian", "Shou Jing Dian") == "EX-SHOU-JING-DIAN"


def test_point_links_are_unique_and_sorted() -> None:
    base = "https://www.meine-tcm.com/en/acupuncture-points/acupuncture-point-"
    index = f'<a href="{base}st-36/">x</a><a href="{base}li-04/">y</a><a href="{base}st-36/">z</a>'
    assert point_links(index) == [f"{base}li-04/", f"{base}st-36/"]
