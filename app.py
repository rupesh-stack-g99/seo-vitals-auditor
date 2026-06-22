import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from urllib.parse import urlparse

# --- CONFIGURATION & UI SETUP ---
st.set_page_config(page_title="G99 PageSpeed Auditor", page_icon="🚀", layout="wide")

st.title("PageSpeed Auditor")
st.subheader("Powered by Growth99")
st.write("Enter a website domain below to crawl its pages and run a deep Core Web Vitals audit.")

# Securely grab API key from Streamlit Secrets or fallback to sidebar user input
API_KEY = st.secrets.get("PAGESPEED_API_KEY", "")
if not API_KEY:
    API_KEY = st.sidebar.text_input("Enter Google PageSpeed API Key", type="password")

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
            
            # Heavy Traffic Optimization: Auto-Wait if Google throttles requests (Rate Limit Hit)
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
            
            # Flagging Engine 
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
                "Issues Found": ", ".join(issues)
            }
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(2)
            
    return None

# --- UI APPLICATION FLOW ---
target_domain = st.text_input("Enter Domain Name (e.g., mysite.com or https://mysite.com)", "")

if st.button("Run Deep Audit 🔍"):
    if not API_KEY:
        st.error("Please provide a PageSpeed API Key to proceed.")
    elif not target_domain:
        st.error("Please enter a domain.")
    else:
        with st.spinner("Finding sitemap..."):
            sitemap = find_sitemap_url(target_domain)
            
        if not sitemap:
            st.error("❌ No Sitemap Found / 404. Could not fetch pages automatically.")
        else:
            st.success(f"📌 Found Sitemap: {sitemap}")
            with st.spinner("Extracting URLs..."):
                urls = get_urls_from_sitemap(sitemap)
                
            if not urls:
                st.warning("No valid URLs found inside the sitemap matching filters.")
            else:
                st.info(f"📋 Found {len(urls)} URLs to audit. Starting analysis...")
                
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, url in enumerate(urls):
                    status_text.text(f"Auditing ({idx+1}/{len(urls)}): {url}")
                    audit_data = fetch_vitals(url, API_KEY)
                    if audit_data:
                        results.append(audit_data)
                    progress_bar.progress((idx + 1) / len(urls))
                    time.sleep(1) # Pacing delay
                
                status_text.text("✅ Audit Complete!")
                
                if results:
                    df = pd.DataFrame(results)
                    
                    # Fix: Shift index to start from 1 instead of 0
                    df.index = df.index + 1
                    
                    st.subheader("📊 Audit Results")
                    
                    # Fix: Expanded layout enabling native horizontal scrollbar support
                    st.dataframe(df, use_container_width=True)
                    
                    # Allow user to download results directly as CSV
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Results as CSV", data=csv, file_name=f"seo_audit_{target_domain}.csv", mime='text/csv')
                else:
                    st.error("Failed to fetch data for all URLs.")
