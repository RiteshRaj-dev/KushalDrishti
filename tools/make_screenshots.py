"""Makes the three prototype screenshots for the deck (small PNG files in shots/).
  1 shot1_map.png        the demo map with the red alert panel open (needs a browser, see below)
  2 shot2_detection.png  one frame from the processed video: blurred faces, boxes, counts
  3 shot3_notice.png     page 1 of the sample draft notice PDF
    python tools/make_screenshots.py --video processed_demo.mp4 [--map-url https://<you>.github.io/KushalDrishti/]"""
import argparse, os
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def detection_frame(video, out, at=0.5):
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        raise RuntimeError(f"Cannot read {video}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * at))
    ok, frame = cap.read(); cap.release()
    if not ok:
        raise RuntimeError("Could not read a frame")
    cv2.imwrite(out, frame)
    return out

def notice_png(pdf, out, dpi=130):
    import pymupdf   # pip install pymupdf
    page = pymupdf.open(pdf)[0]
    clip = pymupdf.Rect(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y0 + page.rect.height * 0.55)   # top part: title, facts, evidence
    page.get_pixmap(dpi=dpi, clip=clip).save(out)
    return out

def map_png(url, out, width=1500, height=900):
    """Screenshot of the static demo with the red dot clicked. Needs: pip install playwright && playwright install chromium"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": width, "height": height})
        pg.goto(url); pg.wait_for_timeout(2500)
        pg.locator(".dot.BREACH").first.click(); pg.wait_for_timeout(800)
        pg.screenshot(path=out); b.close()
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video"); ap.add_argument("--out", default="shots")
    ap.add_argument("--map-url", default="file://" + os.path.join(ROOT, "docs", "index.html"))
    ap.add_argument("--notice", default=os.path.join(ROOT, "docs", "sample_notice_draft.pdf"))
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    if a.video:
        print("made", detection_frame(a.video, os.path.join(a.out, "shot2_detection.png")))
    print("made", notice_png(a.notice, os.path.join(a.out, "shot3_notice.png")))
    try:
        print("made", map_png(a.map_url, os.path.join(a.out, "shot1_map.png")))
    except Exception as err:
        print("Map screenshot skipped:", str(err)[:120])
        print("Take it by hand: open the demo link, click the pulsing red dot, press Win+Shift+S and save as shots/shot1_map.png")
