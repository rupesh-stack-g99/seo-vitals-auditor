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

# Custom Premium & Dynamic Cross-Theme Styling
st.markdown("""
    <style>
        /* Premium Banner Header - Universal dark gradient holds crisp contrast in any theme */
        .brand-header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 2.5rem;
            border-radius: 12px;
            color: white !important;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.12);
        }
        .brand-header h1 {
            color: white !important;
            font-size: 2.8rem !important;
            font-weight: 800 !important;
            margin-bottom: 0.4rem !important;
        }
        .brand-header p {
            color: rgba(255, 255, 255, 0.95) !important;
            font-size: 1.1rem;
            margin: 0;
        }

        /* Clean up Sidebar visual spacing */
        section[data-testid="stSidebar"] .stMarkdown {
            padding-right: 12px;
        }
        
        /* Premium Adaptive Sidebar Content Layout */
        .sidebar-section {
            margin-bottom: 1.75rem; 
            line-height: 1.6;
        }
        
        /* Adapts automatically: White in Dark mode / Dark Charcoal in Light mode */
        .sidebar-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.4rem !important;
            display: flex;
            align-items: center;
        }
        
        /* Automatically switches to legible muted grays based on theme background */
        .sidebar-desc {
            font-size: 0.9rem;
            color: var(--secondary-text-color);
            margin-left: 1.6rem;
        }
        
        /* Dynamic inline micro-badges (.webp, .png) that look perfect on light or dark sidebars */
        .format-badge {
            background-color: rgba(46, 213, 115, 0.15);
            color: #2ed573 !important;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
        }
        
        /* Remove default borders around the form block container */
        div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
            background-color: transparent !important;
        }
        
        /* Fix text headers to gracefully match theme states */
        h3 {
            color: var(--text-color) !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- COLLAPSIBLE LEFT SIDEBAR PANEL ---
with st.sidebar:
    st.markdown("### How the Audit Engine Works")
    st.markdown("---")
    
    st.markdown("""
    <div class="sidebar-section">
        <div class="sidebar-title">⚙️ Automated Discovery</div>
        <div class="sidebar-desc">Finds and decompresses your website's primary XML sitemap layouts.</div>
    </div>
    
    <div class="sidebar-section">
        <div class="sidebar-title">🎯 Target Mapping</div>
        <div class="sidebar-desc">Extracts high-value page, service, and portfolio links.</div>
    </div>
    
    <div class="sidebar-section">
        <div class="sidebar-title">🛡️ Smart Filtering</div>
        <div class="sidebar-desc">
            Automatically ignores media files 
            (<span class="format-badge">.webp</span>, 
            <span class="format-badge">.png</span>, 
            <span class="format-badge">.pdf</span>) & Blogs to protect your API limits.
        </div>
    </div>
    
    <div class="sidebar-section">
        <div class="sidebar-title">📊 Real-time Core Vitals Diagnostics</div>
        <div class="sidebar-desc">Directly analyzes performance, LCP, CLS, TBT, and responsiveness metrics via the Google PageSpeed API.</div>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN WORKSPACE ---
st.markdown("""
    <div class="brand-header">
        <h1>PageSpeed Auditor</h1>
        <p>Advanced Core Web Vitals Crawl Engine • Powered by <b>Growth99</b></p>
        <p style="font-size: 0.95rem; margin-top: 0.6rem; opacity: 0.85; max-width: 800px; margin-left: auto; margin-right: auto;">
            Analyze website performance, identify Core Web Vitals issues, and discover optimization opportunities across your most important pages.
        </p>
    </div>
""", unsafe_allow_html=True)

st.markdown("### 🔍 Initiate Deep Domain Analysis")

with st.form(key="audit_input_form"):
    input_col, button_col = st.columns([0.85, 0.15], vertical_alignment="bottom")
    
    with input_col:
        target_domain = st.text_input(
            "Target Website Domain",
            placeholder="e.g., mysite.com or https://mysite.com",
            label_visibility="collapsed"
        )
        
    with button_col:
        run_audit = st.form_submit_button(
            label="Run Deep Audit", 
            use_container_width=True,
            type="primary"
        )

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
            cls = round(safe_get_metric(audits, 'cumulative-layout-shift'), 3)
            tbt = round(safe_get_metric(audits, 'total-blocking-time'))
            inp = round(audits.get('interaction-to-next-paint', {}).get('numericValue', 0))
            
            issues = []
            if score < 90: issues.append(f"Score Low ({score}%)")
            if lcp > 2.5:  issues.append(f"LCP High ({lcp}s)")
            if cls > 0.1:  issues.append(f"CLS Poor ({cls})")
            if tbt > 200:  issues.append(f"TBT High ({tbt}ms)")
            if inp > 200:  issues.append(f"INP High ({inp}ms)")
            if ttfb > 0.8: issues.append(f"TTFB Slow ({ttfb}s)")
            if fcp > 1.8:  issues.append(f"FCP High ({fcp}s)")
            
            # Dynamically determine the health status emoji dot
            if score >= 90:
                status_dot = "🟢 Good"
            elif score >= 50:
                status_dot = "🟠 Average"
            else:
                status_dot = "🔴 Issue"

            return {
                "URL": url, 
                "Status": status_dot,
                "Score": score, 
                "LCP (s)": lcp, 
                "CLS": cls, 
                "TBT (ms)": tbt, 
                "INP (ms)": inp,
