import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import json

# ---------- CONFIG ----------

# Edit this list with your students' names
STUDENTS = [
    "Anthony",
    "Student 2",
    "Student 3",
    "Student 4",
]

STUDENT_LEVELS = {
    # Placeholder for student levels
}

SHEET_NAME = "Sheet1"  # first tab in your Google Sheet


# ---------- GOOGLE SHEETS SETUP ----------

@st.cache_resource
def get_worksheet():
    service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
    worksheet = spreadsheet.worksheet(SHEET_NAME)
    return worksheet


def ensure_headers(ws):
    # Make sure headers exist (id | name | rating | timestamp | status)
    existing = ws.row_values(1)
    expected = ["id", "name", "rating", "timestamp", "status"]
    if existing != expected:
        ws.update("A1:E1", [expected])


# ---------- DATA FUNCTIONS ----------

def add_help_request(name: str, rating: int):
    ws = get_worksheet()
    ensure_headers(ws)

    request_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    row = [request_id, name, int(rating), now, "pending"]
    ws.append_row(row)


def load_requests() -> pd.DataFrame:
    ws = get_worksheet()
    ensure_headers(ws)

    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=["id", "name", "rating", "timestamp", "status"])
    df = pd.DataFrame(records)
    return df


def mark_as_helped(request_id: str):
    ws = get_worksheet()
    records = ws.get_all_records()
    # data starts at row 2 (row 1 = headers)
    for idx, row in enumerate(records, start=2):
        if row.get("id") == request_id:
            # status column is 5 (E)
            ws.update_cell(idx, 5, "helped")
            break


def clear_all():
    ws = get_worksheet()
    ws.resize(rows=1)  # keep header row only


# ---------- UI: LOGIN ----------

def show_login():
    st.title("Login")
    name = st.selectbox("Select your name", ["-- choose --"] + STUDENTS)
    if st.button("Continue"):
        if name == "-- choose --":
            st.error("Please select your name.")
        else:
            st.session_state["user"] = name
            st.session_state["page"] = "student_level"


# ---------- UI: STUDENT LEVEL ----------

def show_student_level():
    st.title("Your Python Level")
    level = st.slider("Choose your Python experience level (1-10)", 1, 10, 5)
    if st.button("Save Level"):
        if "student_levels" not in st.session_state:
            st.session_state["student_levels"] = {}
        st.session_state["student_levels"][st.session_state["user"]] = level
        st.session_state["page"] = "student_view"


# ---------- UI: STUDENT VIEW ----------

def show_student_view():
    st.title("🙋 Request Help")

    name = st.session_state.get("user")
    st.write(f"Logged in as **{name}**")

    if st.button("Request Help"):
        add_help_request(name, rating)
        st.success("Your help request has been submitted ✅")


# ---------- UI: INSTRUCTOR VIEW ----------

def show_instructor_view():
    st.title("🧑‍🏫 Help Request Dashboard")

    df = load_requests()

    if df.empty:
        st.info("No help requests yet.")
        return

    # only pending requests
    df_pending = df[df["status"] == "pending"].copy()

    if df_pending.empty:
        st.success("No pending requests. 🎉")
        return

    # sort: lowest rating first, then oldest timestamp
    df_pending = df_pending.sort_values(["rating", "timestamp"])

    st.subheader("Pending Requests (sorted by priority)")
    st.dataframe(
        df_pending[["name", "rating", "timestamp"]],
        use_container_width=True,
        hide_index=True,
    )

    st.write("Click a button below once you've helped a student:")

    for _, row in df_pending.iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{row['name']}** — rating `{row['rating']}` — {row['timestamp']}")
        with col2:
            if st.button("Helped", key=row["id"]):
                mark_as_helped(row["id"])
                st.experimental_rerun()


    st.divider()
    if st.button("🚨 Clear ALL requests (reset)", type="secondary"):
        clear_all()
        st.experimental_rerun()


# ---------- MAIN APP ----------

def main():
    st.set_page_config(page_title="Class Help Queue", page_icon="🧑‍🏫", layout="centered")

    if "user" not in st.session_state:
        show_login()
    elif st.session_state.get("page") == "student_level":
        show_student_level()
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Student View", "Instructor View"])

        if page == "Student View":
            show_student_view()
        else:
            show_instructor_view()


if __name__ == "__main__":
    main()