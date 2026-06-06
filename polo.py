import asyncio
import aiohttp
import m3u8
import urllib.request
import time
import pandas as pd
import streamlit as st

# Configure the Streamlit page layout - Fixed: "wide" is now correctly wrapped in quotes
st.set_page_config(page_title="Stream Vault", page_icon="🔒", layout="wide")

# 🔒 HIDDEN SOURCE URL - Users cannot see this in the browser UI
HIDDEN_IPTV_URL = "https://iptv-org.github.io/iptv/categories/sports.m3u"

CONCURRENT_LIMIT = 40  
TIMEOUT_SECONDS = 5    

async def test_single_link(session, semaphore, channel_name, url, progress_queue):
    async with semaphore:
        result = {"Channel Name": channel_name, "URL": url, "Status": "OFFLINE"}
        try:
            async with session.head(url, timeout=TIMEOUT_SECONDS, allow_redirects=True) as response:
                if response.status == 200:
                    result["Status"] = "ONLINE"
                elif response.status in [404, 405, 501]:
                    async with session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True) as get_response:
                        if get_response.status == 200:
                            result["Status"] = "ONLINE"
        except Exception:
            pass
        await progress_queue.put(result)
        return result

async def run_tester_engine(progress_bar, status_text):
    try:
        req = urllib.request.Request(
            HIDDEN_IPTV_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        playlist_data = urllib.request.urlopen(req).read().decode('utf-8')
        playlist = m3u8.loads(playlist_data)
    except Exception as e:
        st.error(f"Error fetching data repository safely.")
        return None

    tracks = playlist.tracks
    total_tracks = len(tracks)
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    progress_queue = asyncio.Queue()
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [test_single_link(session, semaphore, t.title if t.title else t.uri, t.uri, progress_queue) for t in tracks]
        worker_pool = asyncio.gather(*tasks)
        
        results = []
        while len(results) < total_tracks:
            res = await progress_queue.get()
            results.append(res)
            progress_bar.progress(len(results) / total_tracks)
            status_text.text(f"Syncing dashboard components... ({len(results)}/{total_tracks})")
            
        await worker_pool
        return results

def generate_clean_m3u(dataframe):
    m3u_lines = ["#EXTM3U"]
    for _, row in dataframe.iterrows():
        if row["Status"] == "ONLINE":
            m3u_lines.append(f'#EXTINF:-1,{row["Channel Name"]}')
            m3u_lines.append(row["URL"])
    return "\n".join(m3u_lines)

# --- Clean, Locked UI Layout ---
st.title("🔒 Secure Media Stream Hub")
st.markdown("Click below to generate and sync your optimized live sports playlist.")

if st.button("Generate & Verify Playlist Connectors", type="primary"):
    ui_status = st.empty()
    ui_progress = st.empty()
    ui_status.text("Connecting to secure stream bank...")
    ui_progress.progress(0.0)
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        task = loop.create_task(run_tester_engine(ui_progress, ui_status))
        all_results = loop.run_until_complete(asyncio.gather(task))[0]
    else:
        all_results = loop.run_until_complete(run_tester_engine(ui_progress, ui_status))
    
    if all_results:
        ui_status.success("Sync complete! Your playlist file is compiled and ready.")
        df = pd.DataFrame(all_results)
        clean_m3u_data = generate_clean_m3u(df)
        
        st.download_button(
            label="📥 Download Cleaned M3U Playlist",
            data=clean_m3u_data,
            file_name="sports_package.m3u",
            mime="audio/x-mpegurl",
            use_container_width=True
        )
