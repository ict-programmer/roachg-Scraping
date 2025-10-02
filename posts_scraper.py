# roachag_scraper.py
# Scrapes Roach Ag "Resources" posts into Excel/CSV for WordPress import.
# Tested with Python 3.12/3.13 on Windows (Git Bash / CMD / PowerShell).

import sys
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://roachag.com"
LISTING_URL_TPL = "https://roachag.com/Resources/BlogPage/{page}"
DELAY = 0.7  # polite delay between requests

# ---- Easy mode: scrape pages 1..8 automatically ----
# To use CLI instead, set LISTING_PAGES = [].
LISTING_PAGES = [
    "https://roachag.com/Resources/BlogPage/1",
    "https://roachag.com/Resources/BlogPage/2", 
    "https://roachag.com/Resources/BlogPage/3",
    "https://roachag.com/Resources/BlogPage/4",
    "https://roachag.com/Resources/BlogPage/5",
    "https://roachag.com/Resources/BlogPage/6",
    "https://roachag.com/Resources/BlogPage/7",
    "https://roachag.com/Resources/BlogPage/8",
]

# Timestamped outputs to avoid "Permission denied" if a file is open
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_XLSX = f"roachag_blog_posts_{TS}.xlsx"
OUT_CSV  = f"roachag_blog_posts_{TS}.csv"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

# Section/category slugs to ignore
BAD_SLUGS = {
    "Presentations", "Calendar", "Author", "World-Crop-Weather", "Brazil", "Argentina",
    "China", "Russia", "Europe", "Australia", "Brazil-Crop-Updates",
    "Yield-Reports", "Sell-Signal-Charts", "Futures-Prices", "Recent-Webinars", "WASDE"
}

def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=4, connect=4, read=4,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://",  HTTPAdapter(max_retries=retries))
    s.headers.update(HEADERS)
    return s

def get_html(session: requests.Session, url: str, timeout: int = 20) -> str:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text

def normalize_spaces(s: str) -> str:
    # Replace NBSPs and collapse whitespace
    return re.sub(r"\s+", " ", s.replace("\xa0", " ").replace("\u202f", " ")).strip()

def norm_url(href: str) -> str:
    if not href: return ""
    return href if href.startswith("http") else urljoin(BASE, href)

def slugify(t: str) -> str:
    s = t.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    return s.strip("-")

def is_clean_post_path(href: str) -> bool:
    """
    Accept /Resources/<slug> patterns, skip known non-post sections.
    """
    try:
        path = urlparse(href).path or ""
        parts = [p for p in path.split("/") if p]
        
        # Must start with "Resources"
        if not parts or parts[0] != "Resources":
            return False
            
        # Skip if it's a known bad section
        if len(parts) >= 2 and parts[1] in BAD_SLUGS:
            return False
            
        # Accept /Resources/<slug> or /Resources/<slug>/<anything>
        # But skip if it's just /Resources/ (empty slug)
        if len(parts) >= 2 and parts[1]:
            return True
        return False
    except Exception:
        return False

YEAR_RE = re.compile(r"\b20\d{2}\b")

def parse_listing(list_html: str):
    """
    Robust listing parser:
      - target article.post > h2.lb-title > a links specifically,
      - keep only /Resources/<slug> (no extras),
      - dedupe, keep first 10 (each page lists 10 posts).
    """
    soup = BeautifulSoup(list_html, "lxml")
    seen, out = set(), []
    
    # Target the specific structure: article.post > h2.lb-title > a
    all_links = []
    
    # First try: look for article.post > h2.lb-title > a structure
    articles = soup.find_all("article", class_="post")
    for article in articles:
        h2 = article.find("h2", class_="lb-title")
        if h2:
            a = h2.find("a", href=True)
            if a:
                href = a["href"]
                if is_clean_post_path(href):
                    text = a.get_text(strip=True)
                    if text and len(text) >= 10:
                        full_url = norm_url(href)
                        if full_url not in seen:
                            seen.add(full_url)
                            has_year = bool(YEAR_RE.search(text))
                            all_links.append((full_url, text, has_year))
    
    # If no articles found, fallback to general approach but be more selective
    if not all_links:
        print("      FALLBACK: No article.post structure found, using general approach")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not is_clean_post_path(href):
                continue
                
            text = a.get_text(strip=True)
            if not text or len(text) < 10:
                continue
                
            # Skip obvious sidebar content
            parent = a.parent
            is_sidebar = False
            for _ in range(3):
                if parent and hasattr(parent, 'get'):
                    classes = parent.get('class', [])
                    class_text = ' '.join(classes).lower()
                    if any(word in class_text for word in ['recentposts', 'mwidgetposts', 'widget', 'sidebar']):
                        is_sidebar = True
                        break
                    parent = parent.parent
                else:
                    break
            
            if is_sidebar:
                continue
                
            full_url = norm_url(href)
            if full_url not in seen:
                seen.add(full_url)
                has_year = bool(YEAR_RE.search(text))
                all_links.append((full_url, text, has_year))
    
    # Sort by year presence (posts with years first), then by order found
    indexed_links = [(i, link) for i, link in enumerate(all_links)]
    indexed_links.sort(key=lambda x: (not x[1][2], x[0]))
    all_links = [link for _, link in indexed_links]
    
    # Take first 10
    for url, title, _ in all_links[:10]:
        out.append((url, title))

    return out

MONTHS_RE = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_RE = re.compile(
    rf"(?:{MONTHS_RE}\s+\d{{1,2}},\s*\d{{4}}|\d{{1,2}}\s+{MONTHS_RE}\s+\d{{4}})",
    re.I
)

def to_iso_date(date_str: str) -> str:
    """
    "September 12, 2025" or "12 September 2025" -> "YYYY-MM-DD 10:00".
    Return normalized original if parsing fails.
    """
    ds = normalize_spaces(date_str)
    for fmt in ("%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(ds, fmt).strftime("%Y-%m-%d 10:00")
        except ValueError:
            pass
    return ds

def extract_category(soup: BeautifulSoup) -> str:
    a = soup.find("a", href=lambda h: h and "Category=" in h)
    return a.get_text(strip=True) if a else ""

def extract_tags(soup: BeautifulSoup):
    # find heading "Tags" then take anchors in the next sibling container
    h = soup.find(lambda t: isinstance(t, Tag)
                  and t.name in ("h3", "h4", "h5")
                  and t.get_text(strip=True).lower() == "tags")
    cont = h.find_next_sibling() if h else None
    if not cont: return []
    tags = [a.get_text(strip=True) for a in cont.find_all("a")]
    return list(dict.fromkeys([t for t in tags if t]))

def extract_date_text(soup: BeautifulSoup, title_text: str) -> str:
    # 1) <time> if present
    t = soup.find("time")
    if t and t.get_text(strip=True):
        return normalize_spaces(t.get_text(strip=True))

    # 2) scan near the H1/H2 title (site prints the date here)
    title_el = soup.find(lambda x: isinstance(x, Tag)
                         and x.name in ("h1", "h2")
                         and title_text.lower() in x.get_text(strip=True).lower())
    probe = title_el or soup.find(["h1", "h2"])
    cur = probe
    for _ in range(8):
        if not cur: break
        text = normalize_spaces(cur.get_text(" ", strip=True))
        m = DATE_RE.search(text)
        if m: return normalize_spaces(m.group(0))
        cur = cur.find_next()

    # 3) fallback: whole page
    text = normalize_spaces(soup.get_text(" ", strip=True))
    m = DATE_RE.search(text)
    return normalize_spaces(m.group(0)) if m else ""

def absolutize_links(fragment_html: str) -> str:
    if not fragment_html: return fragment_html
    s = BeautifulSoup(fragment_html, "lxml")
    for a in s.find_all("a", href=True):
        a["href"] = norm_url(a["href"])
    for img in s.find_all("img", src=True):
        img["src"] = norm_url(img["src"])
    return str(s)

def extract_content_html(soup: BeautifulSoup, title_text: str) -> str:
    """
    Take siblings after the H1/H2 title until we hit sidebar/related sections.
    """
    title_el = soup.find(lambda t: isinstance(t, Tag)
                         and t.name in ("h1", "h2")
                         and title_text.lower() in t.get_text(strip=True).lower())
    if not title_el:
        title_el = soup.find(["h1", "h2"])
        if not title_el:
            return ""

    stop_words = {"related posts", "recent posts", "categories", "tags", "contact us"}
    allowed = {"p","ul","ol","li","h3","h4","h5","blockquote","figure","img","table",
               "thead","tbody","tr","th","td","em","strong","a","span"}

    parts = []
    for sib in title_el.next_siblings:
        if not isinstance(sib, Tag): continue
        heading = sib.get_text(strip=True).lower()[:40]
        if any(w in heading for w in stop_words): break
        if sib.name in allowed or sib.find(lambda t: isinstance(t, Tag) and t.name in allowed):
            parts.append(str(sib))
    return "".join(parts).strip()

def first_image_url_from_html(html, page_soup):
    s = BeautifulSoup(html or "", "lxml")
    img = s.find("img") or page_soup.find("img")
    src = img.get("src") if img else ""
    return norm_url(src) if src else ""

def parse_post(session: requests.Session, url: str, expected_title: str):
    html = get_html(session, url)
    soup = BeautifulSoup(html, "lxml")

    h = soup.find(lambda t: isinstance(t, Tag) and t.name in ("h1","h2"))
    title = expected_title or (h.get_text(strip=True) if h else url.rsplit("/", 1)[-1].replace("-", " "))

    body_html = extract_content_html(soup, title)
    body_html = absolutize_links(body_html)

    tags = extract_tags(soup)
    category = extract_category(soup) or "USDA Supply/Demand"
    date_txt = extract_date_text(soup, title)
    post_date = to_iso_date(date_txt)
    featured = first_image_url_from_html(body_html, soup)

    # If clearly not a post (no body & no date), skip
    skip = (not body_html) and (not date_txt)

    return {
        "title": title,
        "date": post_date,
        "category": category,
        "tags": tags,
        "content_html": body_html,
        "featured": featured,
        "skip": skip,
    }

def main():
    session = make_session()
    rows = []
    seen_urls = set()  # Global deduplication across all pages

    # Determine listing URLs: prefer LISTING_PAGES; else use CLI pages; else page 1.
    if LISTING_PAGES:
        listing_urls = LISTING_PAGES
    else:
        if len(sys.argv) > 1:
            pages = [int(x) for x in sys.argv[1:]]
        else:
            pages = [1]
        listing_urls = [LISTING_URL_TPL.format(page=p) for p in pages]

    for list_url in listing_urls:
        print(f"[list] {list_url}")
        try:
            listing_html = get_html(session, list_url)
        except Exception as e:
            print(f"  !! failed listing: {e}")
            continue

        posts = parse_listing(list_html=listing_html)
        print(f"  found {len(posts)} post links")
        if len(posts) < 10:
            print("  !! WARNING: fewer than 10 post links found on this page")
        
        # Debug: show what links were found
        print(f"  DEBUG: Found {len(posts)} posts on this page:")
        for i, (url, title) in enumerate(posts, 1):
            print(f"    {i:2d}. {title} -> {url}")

        for i, (url, title) in enumerate(posts, 1):
            # Skip if we've already processed this URL
            if url in seen_urls:
                print(f"    {i:2d}. {title} (duplicate - skipping)")
                continue
                
            print(f"    {i:2d}. {title}")
            try:
                data = parse_post(session, url, title)
            except Exception as e:
                print(f"         !! skip ({e})")
                continue

            if data["skip"]:
                print(f"         .. skipped (no body/date detected)")
                continue

            # Mark this URL as seen
            seen_urls.add(url)
            
            rows.append({
                "source_url": url,
                "post_title": data["title"],
                "post_slug": slugify(data["title"]),
                "post_status": "draft",
                "post_author": "admin",
                "post_date": data["date"],           # e.g., 2025-09-12 10:00
                "categories": data["category"],
                "tags": "|".join(data["tags"]),
                "excerpt": "",
                "content_html": data["content_html"],
                "featured_image_url": data["featured"],
                "featured_image_alt": "",
                "image_gallery_urls": "",
                "canonical_url": "",
                "seo_title": "",
                "seo_meta_description": "",
                "redirect_from": "",
                "menu_order": "0",
                "comment_status": "closed",
                "ping_status": "closed",
                "meta__source": "Roach Ag Resources",
                "meta__external_id": "",
                "meta__custom1": "",
                "meta__custom2": "",
            })
            time.sleep(DELAY)

    df = pd.DataFrame(rows)
    df.to_excel(OUT_XLSX, index=False)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"[done] {len(rows)} unique posts → {OUT_XLSX} / {OUT_CSV}")
    print(f"[stats] Total URLs seen: {len(seen_urls)}, Duplicates skipped: {len(seen_urls) - len(rows)}")

if __name__ == "__main__":
    main()
