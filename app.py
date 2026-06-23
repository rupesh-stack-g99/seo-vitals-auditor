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
st.markdown("### ⚡ Core Web Vitals & PageSpeed Analysis")
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

# Safe metric helper extracted globally to fix execution blocks
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
            
            return {
                "URL": url, "HTTP": 200, "Score": score, "LCP (s)": lcp, "CLS": cls, 
                "TBT (ms)": tbt, "INP (ms)": inp, "TTFB (s)": ttfb, "FCP (s)": fcp, 
                "Issues Found": ", ".join(issues) if issues else "Passed Audit"
            }
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(2)
    return None

# --- UI APPLICATION PROCESS FLOW ---
if run_audit:
    if not API_KEY:
        st.error("⚠️ Setup Interruption: Please check or provide a PageSpeed API Key above.")
    elif not target_domain:
        st.error("⚠️ System Alert: Please enter a domain before executing the scan pipeline.")
    else:
        st.markdown("---")
        
        status_col = st.columns(1)[0]
        with status_col:
            with st.spinner("🔍 Crawling system looking for XML sitemap indexes..."):
                sitemap = find_sitemap_url(target_domain)
            
            if not sitemap:
                st.error("❌ Link Discovery Fault: No Sitemap Found (404). Check spelling or try a full URL prefix.")
            else:
                st.markdown(f"**📌 Target Route Discovered:** `{sitemap}`")
                with st.spinner("🧬 Decompressing mapping files and extracting structural target page nodes..."):
                    urls = get_urls_from_sitemap(sitemap)
                    
                if not urls:
                    st.warning("⚠️ Logic Exception: No matching structural target layouts extracted from sitemap filters.")
                else:
                    st.info(f"📋 **Pipeline Initiated:** Found **{len(urls)}** unique URLs to systematically analyze.")
                    
                    results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, url in enumerate(urls):
                        status_text.markdown(f"⚡ **Analyzing Node ({idx+1}/{len(urls)}):** `{url}`")
                        audit_data = fetch_vitals(url, API_KEY)
                        if audit_data:
                            results.append(audit_data)
                        progress_bar.progress((idx + 1) / len(urls))
                        time.sleep(0.5) 
                    
                    status_text.empty()
                    progress_bar.empty()
                    st.success("🎉 **Data Collection Processing Cycle Complete!**")
                    
                    if len(results) > 0:
                        df = pd.DataFrame(results)
                        df.index = df.index + 1
                        
                        # --- BRAND METRIC EXECUTIVE SUMMARY SECTION ---
                        total_scanned = len(df)
                        passed_count = len(df[df["Issues Found"] == "Passed Audit"])
                        issue_count = total_scanned - passed_count
                        
                        st.markdown("### 📊 Executive Audit Summary")
                        metric_col1, metric_col2, metric_col3 = st.columns(3)
                        with metric_col1:
                            st.metric(label="Total Pages Evaluated", value=total_scanned)
                        with metric_col2:
                            st.metric(label="Fully Passed Pages", value=passed_count, delta=f"{round((passed_count/total_scanned)*100)}% Match")
                        with metric_col3:
                            st.metric(label="Pages Flagging Issues", value=issue_count, delta=f"-{issue_count} Optimization Targets", delta_color="inverse")
                        
                        # --- MAIN INTERACTIVE TABLE DISPLAY ---
                        st.markdown("### 📋 Dynamic Audit Log Sheets")
                        st.dataframe(df, use_container_width=True)
                        
                        # Direct Action Download Option Button
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Export Enterprise Audit Data as CSV Sheet", 
                            data=csv, 
                            file_name=f"Growth99_SEO_Audit_{target_domain}.csv", 
                            mime='text/csv',
                            type="secondary"
                        )
                    else:
                        st.error("System Failure: Could not fetch diagnostics for these URLs.")
