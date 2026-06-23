import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION & UI SETUP ---
st.set_page_config(
    page_title="PageSpeed Auditor | Growth99", 
    page_icon="🔍", 
    layout="wide"
)

# Custom Premium & Dynamic Cross-Theme Styling
st.markdown("""
    <style>
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
        section[data-testid="stSidebar"] .stMarkdown {
            padding-right: 12px;
        }
        .sidebar-section {
            margin-bottom: 1.75rem; 
            line-height: 1.6;
        }
        .sidebar-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.4rem !important;
            display: flex;
            align-items: center;
        }
        .sidebar-desc {
            font-size: 0.9rem;
            color: var(--secondary-text-color);
            margin-left: 1.6rem;
        }
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
        div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
            background-color: transparent !important;
        }
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
        <div class="sidebar-desc">Directly analyzes performance metrics concurrently via the Google PageSpeed API.</div>
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
    
    # LOGIC UPGRADE: Increased retries and extended timeouts (up to 45 seconds per request) to prevent network drops
    max_retries = 4
    for attempt in range(max_retries):
        try:
            # Gradually increase timeouts per retry attempt (30s, 35s, 40s, 45s)
            current_timeout = 30 + (attempt * 5)
            res = requests.get(api_url, timeout=current_timeout)
            
            if res.status_code == 429:
                time.sleep(6 * (attempt + 1))  # Exponential backoff on rate limits
                continue
            if res.status_code != 200:
                time.sleep(2)
                continue
                
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
                "TTFB (s)": ttfb, 
                "FCP (s)": fcp, 
                "Issues Found": ", ".join(issues) if issues else "Passed Audit"
            }
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(3) # Wait briefly before triggering the next retry attempt
    return None

def style_score_colors(val):
    if isinstance(val, (int, float)):
        if val >= 90: return 'color: #2ed573; font-weight: bold;'
        elif val >= 50: return 'color: #ffa502; font-weight: bold;'
        else: return 'color: #ff4757; font-weight: bold;'
    return ''

# --- UI APPLICATION PROCESS FLOW ---
if run_audit:
    if not API_KEY:
        st.error("⚠️ Setup Interruption: Please check or provide your PAGESPEED_API_KEY inside secrets.")
    elif not target_domain:
        st.error("⚠️ System Alert: Please enter a domain before executing the scan pipeline.")
    else:
        st.session_state["audit_results"] = None
        st.session_state["active_domain"] = None
        st.session_state["elapsed_time_string"] = None
        st.session_state["initial_pipeline_count"] = None
        st.markdown("---")
        
        status_col = st.columns(1)[0]
        with status_col:
            with st.spinner("🔍 Crawling system looking for XML sitemap indexes..."):
                sitemap = find_sitemap_url(target_domain)
            
            if not sitemap:
                st.error("❌ Link Discovery Fault: No Sitemap Found (404). Check spelling or try a full URL prefix.")
            else:
                with st.spinner("🧬 Decompressing mapping files and extracting structural target page nodes..."):
                    urls = get_urls_from_sitemap(sitemap)
                    
                if not urls:
                    st.warning("⚠️ Logic Exception: No matching structural target layouts extracted from sitemap filters.")
                else:
                    MAX_PAGES = 400
                    if len(urls) > MAX_PAGES:
                        st.warning(f"⚠️ Large Website Detected! Found {len(urls)} pages. Capping crawl network grid limits to {MAX_PAGES} lines.")
                        urls = urls[:MAX_PAGES]
                    else:
                        st.info(f"📋 **Pipeline Initiated:** Found **{len(urls)}** unique URLs to systematically analyze.")
                    
                    st.session_state["initial_pipeline_count"] = len(urls)
                    
                    start_time = time.time()
                    results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    st.markdown("### 📊 Live Diagnostic Streaming")
                    live_table_placeholder = st.empty()
                    
                    total_urls = len(urls)
                    processed_count = 0
                    
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        future_to_url = {executor.submit(fetch_vitals, url, API_KEY): url for url in urls}
                        
                        for future in as_completed(future_to_url):
                            url = future_to_url[future]
                            processed_count += 1
                            
                            live_elapsed = time.time() - start_time
                            status_text.markdown(f"⚡ **Analyzing Node ({processed_count}/{total_urls})** | ⏱️ *{round(live_elapsed, 1)}s elapsed*:<br>`{url}`", unsafe_allow_html=True)
                            
                            try:
                                audit_data = future.result()
                                if not audit_data:
                                    audit_data = {
                                        "URL": url, 
                                        "Status": "🔴 API Timeout/Error",
                                        "Score": 0, 
                                        "LCP (s)": 0.0, 
                                        "CLS": 0.0, 
                                        "TBT (ms)": 0, 
                                        "INP (ms)": 0, 
                                        "TTFB (s)": 0.0, 
                                        "FCP (s)": 0.0, 
                                        "Issues Found": "API Request Failed or Timed Out"
                                    }
                                
                                results.append(audit_data)
                                
                                current_stream_df = pd.DataFrame(results)
                                current_stream_df.index = current_stream_df.index + 1
                                
                                column_order = ["URL", "Status", "Score", "LCP (s)", "CLS", "TBT (ms)", "INP (ms)", "TTFB (s)", "FCP (s)", "Issues Found"]
                                existing_cols = [c for c in column_order if c in current_stream_df.columns]
                                current_stream_df = current_stream_df[existing_cols]
                                
                                try:
                                    styled_stream = current_stream_df.style.map(style_score_colors, subset=['Score'])
                                except AttributeError:
                                    styled_stream = current_stream_df.style.applymap(style_score_colors, subset=['Score'])
                                    
                                live_table_placeholder.dataframe(
                                    styled_stream,
                                    use_container_width=True,
                                    column_config={
                                        "URL": st.column_config.TextColumn("Audited URL Target"),
                                        "Status": st.column_config.TextColumn("Status"),
                                        "Score": st.column_config.ProgressColumn("Performance Score", format="%d", min_value=0, max_value=100)
                                    }
                                )
                            except Exception as exc:
                                pass
                            progress_bar.progress(processed_count / total_urls)
                    
                    end_time = time.time()
                    total_duration = end_time - start_time
                    if total_duration >= 60:
                        mins = int(total_duration // 60)
                        secs = int(total_duration % 60)
                        st.session_state["elapsed_time_string"] = f"{mins}m {secs}s"
                    else:
                        st.session_state["elapsed_time_string"] = f"{round(total_duration, 1)}s"
                        
                    status_text.empty()
                    progress_bar.empty()
                    live_table_placeholder.empty() 
                    
                    if len(results) > 0:
                        st.session_state["audit_results"] = results
                        st.session_state["active_domain"] = target_domain
                        st.success("🎉 **Data Collection Processing Cycle Complete!**")
                    else:
                        st.error("System Failure: Could not fetch diagnostics for these URLs.")

# --- PERSISTENT DATA RENDERING BLOCK ---
if st.session_state.get("audit_results"):
    df = pd.DataFrame(st.session_state["audit_results"])
    df.index = df.index + 1
    current_domain = st.session_state.get("active_domain", "Domain")
    duration_metric = st.session_state.get("elapsed_time_string", "N/A")
    initial_total = st.session_state.get("initial_pipeline_count", len(df))
    
    failed_skipped_count = len(df[df["Status"] == "🔴 API Timeout/Error"])
    total_scanned = len(df) - failed_skipped_count
    passed_count = len(df[df["Issues Found"] == "Passed Audit"])
    issue_count = total_scanned - passed_count
    
    low_score_count = len(df[(df["Score"] < 90) & (df["Status"] != "🔴 API Timeout/Error")])
    
    st.markdown("### 📊 Audit Summary")
    
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    with m_col1:
        st.metric(label="Total Pages Evaluated", value=total_scanned)
    with m_col2:
        st.metric(label="Fully Passed Pages", value=passed_count, delta=f"{round((passed_count/total_scanned)*100) if total_scanned > 0 else 0}% Match")
    with m_col3:
        st.metric(label="Pages Flagging Issues", value=issue_count, delta=f"-{issue_count} Optimization Targets", delta_color="inverse")
    with m_col4:
        st.metric(label="Low Performance (<90)", value=low_score_count, delta="Action Needed" if low_score_count > 0 else None, delta_color="inverse")
    with m_col5:
        st.metric(label="Failed / Skipped Pages", value=failed_skipped_count, delta=f"Out of {initial_total} total urls" if failed_skipped_count > 0 else None, delta_color="inverse" if failed_skipped_count > 0 else "off")
    with m_col6:
        st.metric(label="Time Taken to Complete", value=duration_metric)
    
    st.markdown("### 📋 Dynamic Audit Log Sheets")
    
    column_order = ["URL", "Status", "Score", "LCP (s)", "CLS", "TBT (ms)", "INP (ms)", "TTFB (s)", "FCP (s)", "Issues Found"]
    existing_columns = [col for col in column_order if col in df.columns]
    df = df[existing_columns]

    try:
        styled_df = df.style.map(style_score_colors, subset=['Score'])
    except AttributeError:
        styled_df = df.style.applymap(style_score_colors, subset=['Score'])

    st.dataframe(
        styled_df, 
        use_container_width=True,
        column_config={
            "URL": st.column_config.TextColumn("Audited URL Target", help="Full original path monitored"),
            "Status": st.column_config.TextColumn("Status", help="Performance status categorization group"),
            "Score": st.column_config.ProgressColumn("Performance Score", format="%d", min_value=0, max_value=100)
        }
    )
    
    export_df = df.copy()
    if "Status" in export_df.columns:
        export_df["Status"] = export_df["Status"].astype(str).str.replace("🟢 ", "", regex=False)\
                                                 .str.replace("🟠 ", "", regex=False)\
                                                 .str.replace("🔴 ", "", regex=False)
    
    csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Export Audit Data as CSV Sheet", 
        data=csv_data, 
        file_name=f"Growth99_SEO_Audit_{current_domain}.csv", 
        mime='text/csv',
        type="secondary"
    )
