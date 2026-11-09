import os
from datetime import date

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
STATUSES = ["New", "Contacted", "Interested", "Converted", "Lost"]
SOURCES = ["Website", "LinkedIn", "Referral", "Email", "Phone", "Event", "Other"]

st.set_page_config(page_title="AI CRM Lead Assistant", page_icon="", layout="wide")


def api_request(method, path, **kwargs):
    """Make all frontend data requests through FastAPI."""
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=30, **kwargs)
        if response.ok:
            return response.json()
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        st.error(f"API error ({response.status_code}): {detail}")
    except requests.RequestException as exc:
        st.error(f"Cannot reach the backend at {API_URL}. Start FastAPI first. Details: {exc}")
    return None


def fetch_leads():
    """Return the leads stored in MySQL, or None if the backend/database call failed."""
    return api_request("GET", "/leads/")


def render_dashboard():
    st.title("CRM Dashboard")
    with st.spinner("Loading statistics from MySQL..."):
        stats = api_request("GET", "/dashboard/stats")
    if not stats:
        st.info("Dashboard data will appear when the backend is running and connected to MySQL.")
        return

    counts = stats["status_counts"]
    if stats["total_leads"] == 0:
        st.info("The CRM database has no leads yet. Add one in Manage Leads, or import "
                "database/sample.sql manually in MySQL (see README).")
    metrics = [
        ("Total Leads", stats["total_leads"]),
        ("New Leads", counts.get("New", 0)),
        ("Contacted", counts.get("Contacted", 0)),
        ("Interested", counts.get("Interested", 0)),
        ("Converted", counts.get("Converted", 0)),
        ("Lost", counts.get("Lost", 0)),
        ("Conversion Rate", f'{stats["conversion_rate"]}%'),
    ]
    cols = st.columns(7)
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    left, right = st.columns(2)
    with left:
        st.subheader("Lead distribution by status")
        status_df = pd.DataFrame(
            [{"Status": k, "Leads": v} for k, v in counts.items()]
        )
        if status_df["Leads"].sum():
            st.plotly_chart(px.pie(status_df, names="Status", values="Leads", hole=0.35),
                            width="stretch")
        else:
            st.info("No leads available yet.")
    with right:
        st.subheader("Leads by source")
        source_df = pd.DataFrame(
            [{"Source": k, "Leads": v} for k, v in stats["source_counts"].items()]
        )
        if not source_df.empty:
            st.plotly_chart(px.bar(source_df, x="Source", y="Leads", text="Leads"),
                            width="stretch")
        else:
            st.info("No lead-source data available.")


def render_manage_leads():
    st.title("Manage Leads")
    with st.expander("Add a new lead", expanded=False):
        with st.form("add_lead_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Customer name *")
            email = c2.text_input("Email address *")
            company = c1.text_input("Company")
            source = c2.selectbox("Lead source", SOURCES)
            status = c1.selectbox("Status", STATUSES)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create lead", type="primary")
            if submitted:
                if not name.strip() or not email.strip():
                    st.error("Name and email are required.")
                else:
                    result = api_request("POST", "/leads/", json={
                        "name": name, "email": email, "company": company,
                        "lead_source": source, "status": status, "notes": notes,
                    })
                    if result:
                        st.toast(f'Lead "{result["name"]}" created.', icon="")
                        st.rerun()

    st.subheader("Search and filter")
    f1, f2, f3 = st.columns(3)
    search = f1.text_input("Search name, email, or company")
    status_filter = f2.selectbox("Status", ["All"] + STATUSES)
    source_filter = f3.selectbox("Lead source", ["All"] + SOURCES)
    params = {}
    if search.strip():
        params["search"] = search.strip()
    if status_filter != "All":
        params["status"] = status_filter
    if source_filter != "All":
        params["lead_source"] = source_filter
    with st.spinner("Loading leads from MySQL..."):
        if params:
            leads = api_request("GET", "/leads/search/", params=params)
        else:
            leads = fetch_leads()
    if leads is None:
        st.warning("Leads could not be loaded. Fix the error above and refresh.")
        return

    st.subheader(f"Leads ({len(leads)})")
    if leads:
        display = pd.DataFrame(leads)
        display = display[["id", "name", "email", "company", "lead_source",
                           "status", "created_at"]]
        st.dataframe(display, width="stretch", hide_index=True)
    else:
        st.info("No leads match the current search and filters.")

    st.divider()
    st.subheader("Edit or delete a lead")
    all_leads = fetch_leads()
    if not all_leads:
        if all_leads is not None:
            st.info("Create a lead before editing or deleting.")
        return
    labels = {f'{x["id"]} — {x["name"]} ({x["email"]})': x for x in all_leads}
    selected_label = st.selectbox("Choose a lead", list(labels.keys()), key="manage_selected")
    selected = labels[selected_label]

    with st.form("edit_lead_form"):
        a, b = st.columns(2)
        edit_name = a.text_input("Name", value=selected["name"], key=f'edit_name_{selected["id"]}')
        edit_email = b.text_input("Email", value=selected["email"], key=f'edit_email_{selected["id"]}')
        edit_company = a.text_input("Company", value=selected.get("company", ""), key=f'edit_company_{selected["id"]}')
        source_options = SOURCES if selected["lead_source"] in SOURCES else SOURCES + [selected["lead_source"]]
        edit_source = b.selectbox("Source", source_options,
                                  index=source_options.index(selected["lead_source"]),
                                  key=f'edit_source_{selected["id"]}')
        edit_status = a.selectbox("Status", STATUSES, index=STATUSES.index(selected["status"]),
                                  key=f'edit_status_{selected["id"]}')
        edit_notes = st.text_area("Notes", value=selected.get("notes") or "",
                                  key=f'edit_notes_{selected["id"]}')
        save = st.form_submit_button("Save changes", type="primary")
        if save:
            result = api_request("PUT", f'/leads/{selected["id"]}', json={
                "name": edit_name, "email": edit_email, "company": edit_company,
                "lead_source": edit_source, "status": edit_status, "notes": edit_notes,
            })
            if result:
                st.toast("Lead updated successfully.", icon="")
                st.rerun()

    confirm_delete = st.checkbox(f'I understand that lead "{selected["name"]}" will be permanently deleted.',
                              key=f'confirm_delete_{selected["id"]}')
    if st.button("Delete selected lead", disabled=not confirm_delete):
        result = api_request("DELETE", f'/leads/{selected["id"]}')
        if result:
            st.toast(result["message"], icon="")
            st.rerun()


def render_ai_assistant():
    st.title("AI Lead Assistant")
    leads = fetch_leads()
    if not leads:
        if leads is not None:
            st.info("Add leads before using the AI assistant.")
        return
    labels = {f'{x["id"]} — {x["name"]} ({x["company"]})': x for x in leads}
    selected = labels[st.selectbox("Select a lead", list(labels.keys()))]
    with st.expander("Selected lead details", expanded=True):
        st.write(f'**Company:** {selected["company"]}  |  **Source:** {selected["lead_source"]}')
        st.write(f'**Status:** {selected["status"]}')
        st.write(selected.get("notes") or "No notes added.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✨ Generate AI Lead Summary", width="stretch"):
            with st.spinner("Analyzing lead details..."):
                result = api_request("POST", f'/ai/lead-summary/{selected["id"]}')
            if result:
                st.session_state[f'lead_summary_{selected["id"]}'] = result["result"]
    with c2:
        if st.button("Generate Follow-up Suggestion", width="stretch"):
            with st.spinner("Preparing follow-up recommendation..."):
                result = api_request("POST", f'/ai/follow-up/{selected["id"]}')
            if result:
                st.session_state[f'follow_up_{selected["id"]}'] = result["result"]
    summary = st.session_state.get(f'lead_summary_{selected["id"]}')
    follow_up = st.session_state.get(f'follow_up_{selected["id"]}')
    if summary:
        st.subheader("AI Lead Summary")
        st.markdown(summary)
    if follow_up:
        st.subheader("AI Follow-up Suggestion")
        st.markdown(follow_up)


def render_chat():
    st.title("Ask CRM AI")
    st.caption("Ask questions about the records currently stored in your CRM.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    question = st.chat_input("Example: Which leads are interested?")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Checking CRM data and asking the AI..."):
                result = api_request("POST", "/ai/chat", json={"question": question})
            answer = result["result"] if result else "I couldn't get an answer. Check the error above and try again."
            st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
    if st.button("Clear chat history"):
        st.session_state.chat_history = []
        st.rerun()


def render_insights():
    st.title("CRM Insights")
    st.write("Generate recommendations from the current CRM database records and aggregated statistics.")
    if st.button("Generate Overall CRM Insights", type="primary"):
        with st.spinner("Analyzing CRM performance..."):
            result = api_request("GET", "/ai/insights")
        if result:
            st.session_state["crm_insights"] = result["result"]
    if st.session_state.get("crm_insights"):
        st.markdown(st.session_state["crm_insights"])


def main():
    st.sidebar.title("AI CRM Assistant")
    st.sidebar.caption("Lead management and AI sales support")
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Manage Leads", "AI Lead Assistant", "Ask CRM AI", "CRM Insights"],
    )
    st.sidebar.divider()
    st.sidebar.caption(f"Backend: {API_URL}")
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.ok:
            st.sidebar.success("MySQL connected")
        else:
            st.sidebar.error(health.json().get("database", "Database unavailable"))
    except (requests.RequestException, ValueError):
        st.sidebar.error("Backend not reachable")
    if st.sidebar.button("Refresh data"):
        st.rerun()

    if page == "Dashboard":
        render_dashboard()
    elif page == "Manage Leads":
        render_manage_leads()
    elif page == "AI Lead Assistant":
        render_ai_assistant()
    elif page == "Ask CRM AI":
        render_chat()
    else:
        render_insights()


if __name__ == "__main__":
    main()
