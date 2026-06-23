import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from urllib.parse import urlparse

# --- CONFIGURATION & UI SETUP ---
st.set_page_config(
    page_title="PageSpeed Auditor", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
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
""", unsafe_gradient=True, unsafe_allow_html=True)

# --- SIDEBAR INTERFACE ---
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/000000/rocket.png", width=80)
    st.title("Control Panel")
    st.markdown("---")
    
    # Securely grab API key from Streamlit Secrets or sidebar fallback
    API_KEY = st.secrets.get("PAGESPEED_API_KEY", "")
    if not API_KEY:
        API_KEY = st.text_input("🔑 PageSpeed API Key", type="password", help="Provide your Google PageSpeed Insights API key.")
    else:
        st.success("🔒 System API Key Connected Active")
        
    st.markdown("---")
    st.markdown("### 📋 Audit Rule Filters")
    st.caption("• Crawls Page / Portfolio / Blog Index maps\n• Skips static image assets (.webp, .jpg)\n• Skips individual article deep links")

# --- MAIN WORKSPACE ---
# Brand Hero Banner Block
st.markdown("""
    <div class="brand-header">
        <h1>SITEVITALS PRO</h1>
        <p>Advanced Core Web Vitals & Technical SEO Crawl Engine • Powered by <b>Growth99</b></p>
    </div>
""", unsafe_allow_html=True)

# Domain Input Section Wrapped inside a clean layout container
with st.container():
    st.markdown("### 🔍 Initiate Deep Domain Analysis")
    col_input, col_btn = st.columns([4, 1])
    
    with col_input:
        target_domain = st.text_input(
            "Target Website Domain", 
            placeholder="e.g., mysite.com or https://mysite.com",
            label_visibility="collapsed"
        )
    with col_btn:
        # Pushing the button down slightly to align horizontally with the input bar
        st.markdown("<div style='margin-top: 1px;'></div>", unsafe_allow_html=True)
        run_audit = st.button("Run Deep Audit", use_container_width=True, type="primary")

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
    allowed_sitemaps = ["page-sitemap", "portfolio-sitemap", "blog-sitemap"]
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
                is_main_blog = loc.lower().endswith("/blog") or loc.lower().endswith("/blog/")
                if not is_image and "/wp-content/uploads/" not in loc.lower() and ("/blog/" not in loc.lower() or is_main_blog):
                    urls.append(loc)
    except Exception as e:
        pass
    return list(set(urls))

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
            
            def get_val(key):
                return audits.get(key, {}).get('numericValue', 0)
                
            score = round(data['lighthouseResult']['categories']['performance']['score'] * 100)
            lcp = round(get_val('largest-contentful-paint') / 1000, 2)
            fcp = round(get_val('first-contentful-paint') / 1000, 2)
            ttfb = round(get_val('server-response-time') / 1000, 2)
            cls = round(get_val('cumulative-layout-shift'), 3)
            tbt = round(get_val('total-blocking-time'))
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
        st.error("⚠️ Setup Interruption: Please check or provide a PageSpeed API Key in the Left Control Panel.")
    elif not target_domain:
        st.error("⚠️ System Alert: Please enter a domain before executing the scan pipeline.")
    else:
        st.markdown("---")
        
        # Real-time Visual status steps
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
                    
                    if results:
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
                        st.error("System Failure: Unable to fetch core web speed diagnostics across selected URL patterns.")
