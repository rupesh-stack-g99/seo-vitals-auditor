import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from urllib.parse import urlparse

# --- CONFIGURATION & UI SETUP ---
st.set_page_config(
    page_title="PageSpeed Auditor | Growth99", 
    page_icon="🔍", 
    layout="wide"
)

# Custom Premium Styling
st.markdown("""
    <style>
        /* Main background and overall text tweaks */
        .main {
            background-color: #0f111a;
        }
        /* Header styling block */
        .brand-header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 2.5rem;
            border-radius: 12px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .brand-header h1 {
            color: white !important;
            font-size: 2.8rem !important;
            font-weight: 800 !important;
            margin-bottom: 0.2rem !important;
        }
        .brand-header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        /* Card Container Styling */
        .card-box {
            background-color: #1a1c24;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #2d313e;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- COLLAPSIBLE LEFT SIDEBAR PANEL ---
with st.sidebar:
    st.markdown("### ⚙️ How the Audit Engine Works")
    st.markdown("---")
    st.markdown("""
    * **Automated Discovery:** Finds and decompresses your website's primary XML sitemap layouts.
    * **Target Mapping:** Extracts high-value page, service, and portfolio links.
    * **Smart Filtering:** Automatically ignores media files (.webp, .png, .pdf) & Blogs to protect your API limits.
    * **Real-time Core Vitals Diagnostics:** Directly analyzes performance, LCP, CLS, TBT, and responsiveness metrics via the Google PageSpeed API.
    """)

# --- MAIN WORKSPACE ---
# Brand Hero Banner Block
st.markdown("""
    <div class="brand-header">
        <h1>PageSpeed Auditor</h1>
        <p>Advanced Core Web Vitals Crawl Engine • Powered by <b>Growth99</b></p>
        <p style="font-size: 1rem; margin-top: 0.5rem; opacity: 0.8;">
            Analyze website performance, identify Core Web Vitals issues, and discover optimization opportunities across your most important pages.
        </p>
    </div>
""", unsafe_allow_html=True)

# Domain Input Section
st.markdown("### ⚡ Core Web Vitals & PageSpeed Analyzer")
target_domain = st.text_input(
    "Target Website Domain", 
    placeholder="e.g., mysite.com or https://mysite.com",
    label_visibility="collapsed"
)

# Slight spacer before the button for visual breathing room
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
run_audit = st.button("Run Performance Audit", use_container_width=False, type="primary")

# --- API KEY FETCH ---
API_KEY = st.secrets.get("PAGESPEED_API_KEY", "")

# --- CORE LOGIC FUNCTIONS ---

def find_sitemap_url(domain):
    paths = ["/sitemap_index.xml", "/sitemap.xml", "/post-sitemap.xml"]
    clean_domain = domain.strip().rstrip("/")
    if not clean_domain.startswith("http"):
        clean_domain = "https://" + clean_domain
        
    for p in paths:
        try:
            res = requests.get(clean_domain + p, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                return clean_domain + p
        except:
            continue
    return None

def get_urls_from_sitemap(sitemap_url):
    urls = []
    allowed_sitemaps = ["page-sitemap", "portfolio-sitemap"]
    forbidden_ext = [".webp", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".pdf", ".zip"]
    
    try:
        res = requests.get(sitemap_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code != 200:
            return []
        
        root = ET.fromstring(res.content)
        namespace = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
        loc_query = './/ns:loc' if namespace else './/loc'
        
        for loc_elem in root.findall(loc_query, namespace):
            loc = loc_elem.text.strip()
            if ".xml" in loc:
                if any(word in loc.lower() for word in allowed_sitemaps):
                    urls.extend(get_urls_from_sitemap(loc))
            else:
                is_image = any(loc.lower().endswith(ext) for ext in forbidden_ext)
                if not is_image and "/wp-content/uploads/" not in loc.lower() and "/blog" not in loc.lower():
                    urls.append(loc)
    except Exception as e:
        pass
    return list(set(urls))

def safe_get_metric(audits_dict, key_name):
    return audits_dict.get(key_name, {}).get('numericValue', 0)

def fetch_vitals(url, api_key):
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={requests.utils.quote(url)}&key={api_key}&strategy=mobile&category=performance"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.get(api_url, timeout=40)
            if res.status_code == 429:
                time.sleep(5)  
                continue
            if res.status_code != 200:
                return None
                
            data = res.json()
            audits = data['lighthouseResult']['audits']
                
            score = round(data['lighthouseResult']['categories']['performance']['score'] * 100)
            lcp = round(safe_get_metric(audits, 'largest-contentful-paint') / 1000, 2)
            fcp = round(safe_get_metric(audits, 'first-contentful-paint') / 1000, 2)
            ttfb = round(safe_get_metric(audits, 'server-response-time') / 1000, 2)
            cls = round(safe
