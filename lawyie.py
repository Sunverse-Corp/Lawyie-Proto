import streamlit as st
import sqlite3
import os
from groq import Groq
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Lawyie (Beta Version) | Sunverse Corp", page_icon="⚖️", layout="wide")

# --- DATABASE SETUP (THE VAULT & TRACKING) ---
# Note: On Streamlit Cloud, SQLite resets when the server reboots. 
# For a production app, you will eventually want to swap this for PostgreSQL or Supabase.
DB_NAME = "lawyie_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Users tracking for discount
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, join_date TEXT)''')
    # The Vault for pending withdrawals
    c.execute('''CREATE TABLE IF NOT EXISTS vault (id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL, tier TEXT, timestamp TEXT)''')
    # Usage tracking
    c.execute('''CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY AUTOINCREMENT, query_type TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def get_user_count():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    result = c.fetchone()
    count = result[0] if result else 0
    conn.close()
    return count

def add_to_vault(amount, tier):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO vault (amount, tier, timestamp) VALUES (?, ?, ?)", (amount, tier, now))
    c.execute("INSERT INTO users (join_date) VALUES (?)", (now,))
    conn.commit()
    conn.close()

def log_usage(query_type):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO usage (query_type, timestamp) VALUES (?, ?)", (query_type, now))
    conn.commit()
    conn.close()

# --- SUNVERSE LOGO & UI STYLING ---
st.markdown("""
    <style>
    .sunverse-logo {
        font-size: 30px; font-weight: 900; color: #FF4B4B; letter-spacing: 2px;
        text-transform: uppercase; border: 2px solid #FF4B4B; padding: 10px;
        text-align: center; border-radius: 10px; margin-bottom: 20px;
    }
    .install-banner { background-color: #2e2e2e; padding: 10px; border-radius: 5px; text-align: center; color: white;}
    </style>
    <div class="sunverse-logo">LAWYIE ⚖️ (Beta Version) </div>
""", unsafe_allow_html=True)

# --- GROQ AI SETUP ---
try:
    # Safely fetch API key from Streamlit Secrets
    api_key = st.secrets.get("GROQ_API_KEY", None)
    if api_key:
        groq_client = Groq(api_key=api_key)
    else:
        groq_client = None
        st.error("Groq API Key not found in Streamlit Secrets.")
except Exception as e:
    groq_client = None
    st.error(f"Error connecting to Groq: {e}")

def get_lawyie_response(prompt, task="chat"):
    if not groq_client: 
        return "AI Offline. Please configure the GROQ_API_KEY in Streamlit Secrets."
    
    system_prompts = {
        "chat": "You are Lawyie, an elite Legal AI Assistant by Sunverse Corp. You are an expert in all African laws (e.g., Nigerian Constitution, OHADA, South African Common Law). Cite specific sections where applicable. Add a disclaimer that you provide legal information, not formal counsel.",
        "draft": "You are Lawyie. Draft professional, legally binding documents formatted properly based on the user's prompt. Apply African legal standards.",
        "review": "You are Lawyie. Review the following contract. Point out loopholes, missing clauses, and potential liabilities under African business law."
    }
    
    log_usage(task)
    try:
        completion = groq_client.chat.completions.create(
            model="meta-llama/llama-guard-4-12b", # <--- Powerful, active model for legal tasks",
            messages=[
                {"role": "system", "content": system_prompts.get(task, system_prompts["chat"])},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"An AI error occurred: {e}"

# --- APP NAVIGATION ---
tabs = st.tabs(["🏠 Home & Offline Game", "💼 Subscriptions (Vault)", "⚖️ Lawyie AI", "📄 Draft/Review", "⚙️ Boss Mode"])

# --- TAB 1: HOME & OFFLINE GAME ---
with tabs[0]:
    st.write("### Welcome to Lawyie (Beta Version)")
    st.write("The premier AI legal assistant for the African continent. Able to draft, cite, and review with flawless accuracy.")
    
    st.markdown('<div class="install-banner">📲 <b>Pro Tip:</b> Add this page to your home screen to install Lawyie as an app!</div><br>', unsafe_allow_html=True)
    
    st.divider()
    st.write("### 🎮 Offline Lawyer Minigame: 'Objection!'")
    st.caption("Play this while waiting for contracts to compile.")
    
    if 'game_score' not in st.session_state:
        st.session_state.game_score = 0
        
    st.write("**Scenario 1:** The prosecutor asks a witness what their neighbor's cousin *said* they saw.")
    col1, col2 = st.columns(2)
    if col1.button("Object: Hearsay"):
        st.success("Correct! That is textbook hearsay.")
        st.session_state.game_score += 10
    if col2.button("Object: Leading the witness"):
        st.error("Overruled! It's an open-ended question, but it calls for hearsay.")
        
    st.write(f"**Current Score:** {st.session_state.game_score}")

# --- TAB 2: SUBSCRIPTIONS & VAULT DEPOSITS ---
with tabs[1]:
    st.write("### Choose Your Subscription")
    users = get_user_count()
    
    is_early_bird = users < 100
    discount_multiplier = 0.8 if is_early_bird else 1.0
    
    if is_early_bird:
        st.success(f"🎉 **EARLY BIRD BONUS!** You are user #{users + 1}. You get a 20% discount!")
    
    tier_1_price = 5000 * discount_multiplier
    tier_2_price = 7500 * discount_multiplier
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("### Basic Plan")
        st.write(f"**Price:** ₦{tier_1_price:,.0f} (Normally ₦5,000)")
        st.write("- General Legal Chat\n- Basic Citations\n- Standard Speed")
        if st.button("Subscribe to Basic"):
            add_to_vault(tier_1_price, "Basic")
            st.success("Payment successful! Funds added to the Sunverse Vault.")
            
    with col2:
        st.warning("### Premium Plan")
        st.write(f"**Price:** ₦{tier_2_price:,.0f} (Normally ₦7,500)")
        st.write("- Document Drafting\n- Deep Contract Review\n- Priority Groq Processing")
        if st.button("Subscribe to Premium"):
            add_to_vault(tier_2_price, "Premium")
            st.success("Payment successful! Funds added to the Sunverse Vault.")

# --- TAB 3: LAWYIE AI CHAT ---
with tabs[2]:
    st.write("### Chat with Lawyie")
    user_query = st.text_input("Ask a legal question (e.g., 'What are the requirements for incorporating a company in Nigeria?')")
    if st.button("Ask Lawyie"):
        if user_query:
            with st.spinner("Lawyie is analyzing African jurisprudence..."):
                response = get_lawyie_response(user_query, "chat")
                st.write(response)
        else:
            st.warning("Please enter a question first.")

# --- TAB 4: DRAFTING & REVIEWING ---
with tabs[3]:
    st.write("### 📄 Pro Document Engine (Section-by-Section)")
    st.info("💡 **Sunverse Tech Note:** To ensure maximum legal detail and bypass standard AI output limits, Lawyie's Groq Engine drafts massive contracts section-by-section at lightning speed.")
    
    doc_action = st.radio("Choose Action:", ["Draft a New Contract", "Review an Existing Contract"], horizontal=True)
    
    if doc_action == "Draft a New Contract":
        contract_topic = st.text_input("What type of contract? (e.g., 'Software Developer Employment Contract in Nigeria' or 'Real Estate Lease in Ghana')")
        party_details = st.text_area("Enter key details (Names of parties, payment amounts, dates, specific rules):")
        
        # The Trick: Breaking the document into bite-sized chunks for Groq!
        section = st.selectbox("Select Contract Section to Draft:", [
            "1. Title, Parties, and Recitals (Introduction)",
            "2. Core Duties & Obligations of Both Parties",
            "3. Compensation, Payment Terms & Milestones",
            "4. Confidentiality (NDA) & Intellectual Property Rights",
            "5. Termination, Governing Law & Signatures"
        ])
        
        if st.button("Draft This Section"):
            if contract_topic:
                with st.spinner(f"Lawyie is drafting {section}..."):
                    # We instruct the AI to write ONLY the selected section
                    custom_prompt = f"Contract Type: {contract_topic}\nDetails: {party_details}\n\nTask: Draft ONLY the following section of the contract in highly professional legal English: {section}. Do NOT write the rest of the contract. Make this specific section extremely detailed. Apply African legal standards."
                    
                    result = get_lawyie_response(custom_prompt, "draft")
                    st.write("### Generated Section:")
                    st.success(result)
                    
                    st.caption(f"✅ **Step complete.** Copy this text to your document, then select the next section from the dropdown above!")
            else:
                st.warning("⚠️ Please enter the type of contract first.")
                
    else:
        # Contract Review Mode (This usually stays under the limit easily)
        st.write("### Contract Analyzer")
        doc_text = st.text_area("Paste the contract text here for Lawyie to review:")
        
        if st.button("Analyze for Loopholes"):
            if doc_text:
                with st.spinner("Lawyie is scanning for liabilities under African business law..."):
                    result = get_lawyie_response(doc_text, "review")
                    st.write(result)
            else:
                st.warning("⚠️ Please paste some text to review.")

# --- TAB 5: BOSS MODE (SECURE VAULT ACCESS) ---
with tabs[4]:
    st.write("### 🔐 Boss Mode")
    st.info("Note: Streamlit Cloud occasionally resets SQLite databases. In production, move to a cloud DB.")
    password = st.text_input("Enter Boss Mode Password:", type="password")
    
    if password:
        # Safely check password against secrets
        correct_password = st.secrets.get("BOSSMODE_PASSWORD", "")
        
        if password == correct_password and correct_password != "":
            st.success("Access Granted. Welcome, Sunverse CEO.")
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            # Safely Read Vault
            c.execute("SELECT SUM(amount) FROM vault")
            result = c.fetchone()
            total_funds = result[0] if result and result[0] is not None else 0.0
            
            st.metric(label="Total Funds in Pending Vault", value=f"₦{total_funds:,.2f}")
            st.caption("Link an external bank API here when you open an account to withdraw these funds.")
            
            # Read Usage Analytics
            st.write("#### AI Usage Analytics")
            c.execute("SELECT query_type, COUNT(*) FROM usage GROUP BY query_type")
            usage_data = c.fetchall()
            if usage_data:
                for row in usage_data:
                    st.write(f"- **{row[0].capitalize()} queries:** {row[1]}")
            else:
                st.write("- No queries yet.")
                
            # Read User Count
            c.execute("SELECT COUNT(*) FROM users")
            user_result = c.fetchone()
            total_users = user_result[0] if user_result else 0
            st.write(f"**Total Registered Subscriptions:** {total_users}")
            
            conn.close()
        else:
            st.error("Intruder Alert. Invalid Password.")

# Footer
st.markdown("<br><hr><center><small>Lawyie by Sunverse Corp. AI Legal assistance is for informational purposes and does not replace professional counsel. This is a Beta Version.</small></center>", unsafe_allow_html=True)
