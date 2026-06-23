import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from urllib.parse import urlparse

# --- CONFIGURATION & UI SETUP ---
st.set_page_config(
    page_title="PageSpeed Auditor | Growth99", 
    page_icon="🚀", 
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

# --- MAIN WORKSPACE ---
# Brand Hero Banner Block
st.markdown("""
    <div class="brand-header">
        <h1>PageSpeed Auditor</h1>
        <p>Advanced Core Web Vitals Crawl Engine • Powered by <b>Growth99</b></p>
    </div>
""", unsafe_allow_html=True)

# --- API KEY STATUS & HOW IT WORKS GUIDE ---
API_KEY = st.secrets.get("PAGESPEED_API_KEY", "")
if not API_KEY:
    API_KEY = st.text_input("🔑 Enter PageSpeed API Key", type="password", help="Provide your Google PageSpeed Insights API key.")

# Professional "How it works" Guideline Display
st.markdown("""
    <div style="background-color: #1e293b; padding: 1.25rem; border-radius: 8px; border-left: 5px solid #3b82f6; margin-bottom: 1.5rem;">
        <h4 style="margin-top: 0; color: #f8fafc;">⚙️ How the Audit Engine Works</h4>
        <ul style="margin-bottom: 0; color: #cbd5e1; font-size: 0.95rem; padding-left: 1.2rem;">
            <li><b>Automated Discovery:</b> Finds and decompresses your website's primary XML sitemap layouts.</li>
            <li><b>Target Mapping:</b> Extracts high-value page, service, and portfolio links.</li>
            <li><b>Smart Filtering:</b> Automatically ignores media files (.webp, .png, .pdf) & Blogs to protect your API limits.</li>
            <li><b>Real-time Core Vitals Diagnostics:</b> Directly analyzes performance, LCP, CLS, TBT, and responsiveness metrics via the Google PageSpeed API.</li>
        </ul>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# Domain Input Section (Button moved below the URL Input box)
st.markdown("### 🔍 Initiate Deep Domain Analysis")
target_domain = st.text_input(
    "Target Website Domain", 
    placeholder="e.g., mysite.com or https://mysite.com",
    label_visibility="collapsed"
)

# Slight spacer before the button for visual breathing room
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
run_audit = st.button("Run Deep Audit", use_container_width=False, type="primary")

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
