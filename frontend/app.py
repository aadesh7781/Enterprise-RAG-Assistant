
import html
import time
from copy import deepcopy
from pathlib import Path

import streamlit as st
from streamlit_cookies_controller import CookieController

from services.api_client import APIClient


# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Nexus AI | Enterprise Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

FRONTEND_DIR = Path(__file__).resolve().parent
CSS_PATH = FRONTEND_DIR / "styles" / "main.css"

api = APIClient()

COOKIE_NAME = "nexus_access_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7

cookie_controller = CookieController(
    key="nexus_cookie_controller"
)


# ==========================================
# LOAD CUSTOM CSS
# ==========================================

def load_css():
    if CSS_PATH.exists():
        css = CSS_PATH.read_text(encoding="utf-8")
        st.html(f"<style>{css}</style>")


load_css()


# ==========================================
# SESSION STATE
# ==========================================

DEFAULTS = {
    "access_token": None,
    "current_user": None,
    "active_page": "Chat",
    "conversation_id": None,
    "messages": [],
    "chat_error": None,
    "conversation_error": None,
    "conversation_cache": None,
    "conversation_load_ms": None,
    "chat_request_ms": None,
    "document_cache": None,
    "document_error": None,
    "login_restoration_checked": False,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = deepcopy(value)


# ==========================================
# RESTORE LOGIN AFTER BROWSER REFRESH
# ==========================================

def restore_login():

    if st.session_state.access_token:
        return

    if st.session_state.login_restoration_checked:
        return

    try:
        with st.spinner("Restoring your session..."):

            cookies = cookie_controller.getAll()

            time.sleep(1)

            saved_token = cookie_controller.get(COOKIE_NAME)

            if not saved_token and isinstance(cookies, dict):
                saved_token = cookies.get(COOKIE_NAME)

            if not saved_token:
                st.session_state.login_restoration_checked = True
                return

            user = api.get_current_user(saved_token)

            st.session_state.access_token = saved_token
            st.session_state.current_user = user
            st.session_state.login_restoration_checked = True

    except RuntimeError:
        cookie_controller.remove(COOKIE_NAME)
        st.session_state.login_restoration_checked = True


restore_login()


# ==========================================
# AUTHENTICATION HELPERS
# ==========================================

def sign_out():

    try:
        cookie_controller.remove(COOKIE_NAME)
        time.sleep(0.5)
    except Exception:
        pass

    for key, value in DEFAULTS.items():
        st.session_state[key] = deepcopy(value)

    st.rerun()


def user_roles():
    user = st.session_state.current_user or {}
    return set(user.get("roles", []))


def is_super_admin():
    return "SUPER_ADMIN" in user_roles()


def is_department_admin():
    return "DEPARTMENT_ADMIN" in user_roles()


def is_admin():
    return is_super_admin() or is_department_admin()


# ==========================================
# CONVERSATION LIST CACHE
# ==========================================

def get_conversation_list(force_refresh=False):

    if (
        st.session_state.conversation_cache is not None
        and not force_refresh
    ):
        return st.session_state.conversation_cache

    token = st.session_state.access_token

    try:
        conversations = api.get_conversations(token) or []

        st.session_state.conversation_cache = conversations
        st.session_state.conversation_error = None

        return conversations

    except RuntimeError as exc:
        st.session_state.conversation_error = str(exc)
        return []


def invalidate_conversation_cache():
    st.session_state.conversation_cache = None


# ==========================================
# START NEW CONVERSATION
# ==========================================

def start_new_conversation():

    st.session_state.conversation_id = None
    st.session_state.messages = []
    st.session_state.chat_error = None
    st.session_state.chat_request_ms = None
    st.session_state.conversation_load_ms = None
    st.session_state.active_page = "Chat"


# ==========================================
# LOAD EXISTING CONVERSATION
# ==========================================

def load_conversation(conversation_id):

    token = st.session_state.access_token
    started_at = time.perf_counter()

    try:
        with st.spinner("Loading conversation..."):

            data = api.get_conversation(
                token,
                conversation_id,
            )

        elapsed_ms = (
            time.perf_counter() - started_at
        ) * 1000

        if not isinstance(data, dict):
            raise RuntimeError(
                "The conversation endpoint returned an unexpected response."
            )

        messages_data = data.get("messages", [])
        messages = []

        for item in messages_data:

            role = item.get("role", "assistant")

            if role not in ("user", "assistant"):
                continue

            messages.append({
                "role": role,
                "content": item.get("content", ""),
                "sources": [],
            })

        st.session_state.conversation_id = str(conversation_id)
        st.session_state.messages = messages
        st.session_state.conversation_load_ms = elapsed_ms
        st.session_state.chat_request_ms = None
        st.session_state.chat_error = None
        st.session_state.active_page = "Chat"

    except (RuntimeError, AttributeError, TypeError, ValueError) as exc:
        st.session_state.chat_error = (
            f"Could not load conversation: {exc}"
        )


# ==========================================
# LOGIN PAGE
# ==========================================

def render_login():

    _, center, _ = st.columns([1, 1.3, 1])

    with center:

        st.html("""
        <div class="login-header">
            <div class="login-logo">🧠</div>
            <h1 class="login-brand">NEXUS AI</h1>
            <p class="login-subtitle">
                Enterprise Knowledge Assistant
            </p>
            <h2 class="login-welcome">Welcome back</h2>
            <p class="login-description">
                Sign in with your company credentials
            </p>
        </div>
        """)

        with st.form("login_form"):

            email = st.text_input(
                "Company email",
                placeholder="employee@company.com",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            submitted = st.form_submit_button(
                "Sign in to Nexus AI",
                type="primary",
                use_container_width=True,
            )

            if submitted:

                if not email.strip() or not password:
                    st.error("Please enter your email and password.")

                else:
                    try:
                        with st.spinner("Authenticating..."):

                            login_response = api.login(
                                email.strip(),
                                password,
                            )

                            token = login_response["access_token"]
                            user = api.get_current_user(token)

                            cookie_controller.set(
                                COOKIE_NAME,
                                token,
                                max_age=COOKIE_MAX_AGE,
                            )

                            time.sleep(1)

                            st.session_state.access_token = token
                            st.session_state.current_user = user
                            st.session_state.login_restoration_checked = True

                            start_new_conversation()
                            invalidate_conversation_cache()

                        st.rerun()

                    except (RuntimeError, KeyError, TypeError) as exc:
                        st.error(f"Login failed: {exc}")

        st.html("""
        <div class="login-footer">
            <span class="footer-dot"></span>
            Secure enterprise access · Authorized users only
        </div>
        """)


# ==========================================
# SIDEBAR
# ==========================================

def render_sidebar():

    user = st.session_state.current_user or {}

    full_name = html.escape(
        user.get("full_name") or "Employee"
    )

    email = html.escape(
        user.get("email") or ""
    )

    with st.sidebar:

        st.html("""
        <div class="sidebar-brand">
            <div class="brand-icon">🧠</div>
            <div>
                <div class="brand-title">NEXUS AI</div>
                <div class="brand-subtitle">
                    Enterprise Knowledge Assistant
                </div>
            </div>
        </div>
        """)

        if st.button(
            "＋  New conversation",
            use_container_width=True,
            type="primary",
        ):
            start_new_conversation()
            st.rerun()

        st.html(
            '<div class="sidebar-label">WORKSPACE</div>'
        )

        navigation = {
            "💬  Conversations": "Chat",
            "📁  Knowledge Base": "Knowledge Base",
        }

        if is_admin():
            navigation["👥  User Management"] = "User Management"

        for label, page in navigation.items():

            if st.button(
                label,
                use_container_width=True,
                key=f"navigation_{page}",
                type=(
                    "primary"
                    if st.session_state.active_page == page
                    else "secondary"
                ),
            ):
                st.session_state.active_page = page
                st.rerun()

        st.html(
            '<div class="sidebar-label">RECENT CONVERSATIONS</div>'
        )

        conversations = get_conversation_list()

        if st.session_state.conversation_error:
            st.caption(
                "Conversation history could not be loaded."
            )

        elif not conversations:
            st.caption("No previous conversations.")

        else:
            for conversation in conversations[:15]:

                conversation_id = str(conversation["id"])

                title = (
                    conversation.get("title")
                    or "New conversation"
                )

                display_title = (
                    title[:29] + "..."
                    if len(title) > 32
                    else title
                )

                is_selected = (
                    conversation_id
                    == st.session_state.conversation_id
                )

                if st.button(
                    f"◦  {display_title}",
                    key=f"conversation_{conversation_id}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    load_conversation(conversation_id)
                    st.rerun()

        if st.button(
            "↻ Refresh conversations",
            use_container_width=True,
        ):
            invalidate_conversation_cache()
            st.rerun()

        st.html(
            '<div class="sidebar-profile-divider"></div>'
        )

        st.html(f"""
        <div class="sidebar-user">
            <div class="avatar">👤</div>
            <div class="sidebar-user-details">
                <div class="sidebar-user-name">{full_name}</div>
                <div class="sidebar-user-email">{email}</div>
            </div>
        </div>
        """)

        if st.button(
            "Sign out",
            use_container_width=True,
        ):
            sign_out()


# ==========================================
# PAGE HEADER
# ==========================================

def render_header(page):

    safe_page = html.escape(page.upper())

    st.html(f"""
    <div class="topbar">
        <div class="breadcrumb">
            ENTERPRISE WORKSPACE
            &nbsp; / &nbsp;
            {safe_page}
        </div>
        <div class="status-pill">
            <span class="status-dot"></span>
            AUTHENTICATED
        </div>
    </div>
    """)


# ==========================================
# DISPLAY SOURCE REFERENCES
# ==========================================

def render_sources(sources):

    if not sources:
        return

    with st.expander(
        f"View source references ({len(sources)})",
        expanded=False,
    ):

        for source in sources:

            source_number = source.get("source_number", "?")
            document_id = source.get("document_id", "Unknown")
            chunk_index = source.get("chunk_index", "Unknown")
            file_type = source.get("file_type", "Unknown")

            st.markdown(f"**Source {source_number}**")

            st.caption(f"Document ID: `{document_id}`")
            st.caption(f"Chunk index: `{chunk_index}`")
            st.caption(f"File type: {file_type}")

            st.divider()


# ==========================================
# DISPLAY CHAT MESSAGES
# ==========================================

def render_messages():

    for message in st.session_state.messages:

        role = message.get("role", "assistant")
        content = message.get("content", "")

        if role not in ("user", "assistant"):
            continue

        with st.chat_message(role):

            st.markdown(content)

            if role == "assistant":
                render_sources(message.get("sources", []))


# ==========================================
# HANDLE CHAT SUBMISSION
# ==========================================

def handle_chat_submission(question):

    token = st.session_state.access_token
    conversation_id = st.session_state.conversation_id

    st.session_state.chat_error = None

    st.session_state.messages.append({
        "role": "user",
        "content": question,
        "sources": [],
    })

    started_at = time.perf_counter()

    try:
        with st.spinner(
            "Nexus AI is searching your authorized documents..."
        ):

            response = api.send_message(
                token=token,
                question=question,
                conversation_id=conversation_id,
                top_k=5,
            )

        elapsed_ms = (
            time.perf_counter() - started_at
        ) * 1000

        if not isinstance(response, dict):
            raise RuntimeError(
                "The chat endpoint returned an unexpected response."
            )

        if "conversation_id" not in response:
            raise RuntimeError(
                "The chat response did not include a conversation ID."
            )

        if "answer" not in response:
            raise RuntimeError(
                "The chat response did not include an answer."
            )

        st.session_state.conversation_id = str(
            response["conversation_id"]
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": response["answer"],
            "sources": response.get("sources", []),
        })

        st.session_state.chat_request_ms = elapsed_ms

        invalidate_conversation_cache()

    except (RuntimeError, KeyError, TypeError, ValueError) as exc:

        st.session_state.chat_error = str(exc)

        st.session_state.chat_request_ms = (
            time.perf_counter() - started_at
        ) * 1000


# ==========================================
# CHAT WORKSPACE
# ==========================================

def render_chat():

    render_header("Chat")

    if st.session_state.chat_error:
        st.error(
            f"Chat operation failed: {st.session_state.chat_error}"
        )

    if not st.session_state.messages:

        st.html("""
        <div class="welcome-section">
            <div class="eyebrow">
                ENTERPRISE KNOWLEDGE ASSISTANT
            </div>
            <div class="welcome-title">
                How can I help you today?
            </div>
            <div class="welcome-description">
                Ask questions about your company's authorized
                documents, policies and procedures.
                Answers are grounded in your enterprise knowledge base.
            </div>
        </div>
        """)

        st.markdown("#### Suggested questions")

        col1, col2 = st.columns(2)

        suggestions = [
            (
                "HR & Leave Policies",
                "How many annual leave days do employees receive?",
            ),
            (
                "Finance & Expenses",
                "What documents are needed for reimbursement?",
            ),
            (
                "IT & Engineering",
                "How can I replace a damaged company laptop?",
            ),
            (
                "Company Procedures",
                "Who should approve an internal company request?",
            ),
        ]

        for index, (title, prompt) in enumerate(suggestions):

            column = col1 if index % 2 == 0 else col2

            with column:

                st.html(f"""
                <div class="suggestion-card">
                    <div class="suggestion-title">
                        {html.escape(title)}
                    </div>
                    <div class="suggestion-description">
                        {html.escape(prompt)}
                    </div>
                </div>
                """)

                if st.button(
                    "Ask this question",
                    key=f"suggestion_{index}",
                    use_container_width=True,
                ):
                    handle_chat_submission(prompt)
                    st.rerun()

    else:
        render_messages()

    question = st.chat_input(
        "Ask your enterprise assistant..."
    )

    if question and question.strip():
        handle_chat_submission(question.strip())
        st.rerun()

    if st.session_state.chat_request_ms is not None:
        st.caption(
            f"Last chat request: "
            f"{st.session_state.chat_request_ms:.0f} ms"
        )

    if st.session_state.conversation_load_ms is not None:
        st.caption(
            f"Conversation loaded in "
            f"{st.session_state.conversation_load_ms:.0f} ms"
        )

    st.html("""
    <div class="chat-disclaimer">
        AI-generated responses may contain errors.
        Verify important information against source documents.
    </div>
    """)


# ==========================================
# KNOWLEDGE BASE
# ==========================================

def render_knowledge_base():

    render_header("Knowledge Base")

    token = st.session_state.access_token

    roles = user_roles()
    can_manage = is_admin()
    super_admin = "SUPER_ADMIN" in roles

    st.markdown("### Document library")

    st.caption(
        "Browse documents available to your account."
    )

    department_filter = None

    if super_admin:
        department_filter = st.text_input(
            "Filter by department ID (optional)",
            placeholder="Enter department UUID",
        ).strip() or None

    # DOCUMENT UPLOAD

    if can_manage:

        with st.expander(
            "Upload a document",
            expanded=False,
        ):

            uploaded_file = st.file_uploader(
                "Select a document",
                type=["pdf", "docx", "txt"],
            )

            target_department = None

            if super_admin:
                target_department = st.text_input(
                    "Department ID",
                    key="upload_department_id",
                    placeholder="Required for Super Admin",
                ).strip()

            if st.button(
                "Upload document",
                type="primary",
                disabled=uploaded_file is None,
            ):

                if super_admin and not target_department:
                    st.error("Enter a department ID.")

                else:
                    try:
                        with st.spinner("Uploading document..."):

                            result = api.upload_document(
                                token=token,
                                file_name=uploaded_file.name,
                                file_bytes=uploaded_file.getvalue(),
                                department_id=target_department,
                            )

                        st.success(
                            f"Uploaded {result['filename']}. "
                            f"Status: {result['status']}"
                        )

                        st.rerun()

                    except RuntimeError as exc:
                        st.error(str(exc))

    # REFRESH DOCUMENTS

    if st.button("↻ Refresh documents"):
        st.session_state.document_cache = None
        st.rerun()

    # FETCH DOCUMENTS

    try:
        documents = api.get_documents(
            token,
            department_id=department_filter,
        ) or []

        st.session_state.document_error = None

    except RuntimeError as exc:
        documents = []
        st.session_state.document_error = str(exc)

    if st.session_state.document_error:
        st.error(st.session_state.document_error)
        return

    if not documents:
        st.info("No authorized documents found.")
        return

    # DOCUMENT METRICS

    completed = sum(
        1 for document in documents
        if document.get("status") == "COMPLETED"
    )

    pending = sum(
        1 for document in documents
        if document.get("status") in ("PENDING", "PROCESSING")
    )

    failed = sum(
        1 for document in documents
        if document.get("status") == "FAILED"
    )

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric("Total documents", len(documents))
    metric2.metric("Completed", completed)
    metric3.metric("Pending / Failed", pending + failed)

    st.divider()

    # DOCUMENT LIST

    for document in documents:

        document_id = document["id"]
        filename = document.get("filename", "Unnamed document")
        file_type = document.get("file_type", "Unknown")
        file_size = document.get("file_size", 0)
        document_status = document.get("status", "UNKNOWN")
        department_id = document.get("department_id", "Unassigned")

        with st.container(border=True):

            left, right = st.columns([4, 1])

            with left:

                st.markdown(f"**{filename}**")

                st.caption(
                    f"{file_type} · {file_size / 1024:.1f} KB"
                )

                st.caption(f"Department: {department_id}")
                st.caption(f"Document ID: `{document_id}`")

            with right:

                st.markdown(f"**{document_status}**")

                if can_manage:

                    if document_status == "PROCESSING":

                        st.button(
                            "Processing",
                            key=f"delete_disabled_{document_id}",
                            disabled=True,
                        )

                    else:

                        confirm = st.checkbox(
                            "Confirm delete",
                            key=f"confirm_delete_{document_id}",
                        )

                        if st.button(
                            "Delete",
                            key=f"delete_{document_id}",
                            disabled=not confirm,
                        ):

                            try:
                                api.delete_document(
                                    token,
                                    document_id,
                                )

                                st.success(f"Deleted {filename}")
                                st.rerun()

                            except RuntimeError as exc:
                                st.error(str(exc))


# ==========================================
# USER MANAGEMENT HELPERS
# ==========================================

ROLE_OPTIONS = [
    "EMPLOYEE",
    "DEPARTMENT_ADMIN",
    "SUPER_ADMIN",
]


def get_user_display_name(user):
    return (
        user.get("full_name")
        or user.get("email")
        or "Unnamed user"
    )


def fetch_management_users():

    token = st.session_state.access_token

    if is_super_admin():
        return api.get_all_users(token) or []

    if is_department_admin():
        return api.get_department_users(token) or []

    raise RuntimeError(
        "Your account does not have permission to view user management."
    )


# ==========================================
# USER MANAGEMENT
# ==========================================

def render_user_management():

    render_header("User Management")

    if not is_admin():
        st.error("You are not authorized to access this page.")
        return

    token = st.session_state.access_token
    super_admin = is_super_admin()

    st.markdown("### User administration")

    if super_admin:
        st.caption(
            "Manage user accounts, department assignments and roles."
        )
    else:
        st.caption(
            "View users assigned to your department."
        )

    # LOAD DEPARTMENTS FOR SUPER ADMIN

    departments = []

    if super_admin:

        try:
            departments = api.get_departments(token) or []
        except RuntimeError as exc:
            st.error(f"Could not load departments: {exc}")
            return

    department_lookup = {
        str(department["id"]): department["name"]
        for department in departments
    }

    # CREATE USER - SUPER ADMIN ONLY

    if super_admin:

        with st.expander(
            "＋ Create user",
            expanded=False,
        ):

            department_options = {
                f"{department['name']} ({department['id']})":
                    str(department["id"])
                for department in departments
            }

            with st.form("create_user_form"):

                new_full_name = st.text_input(
                    "Full name",
                    max_chars=150,
                    placeholder="Enter full name",
                )

                new_email = st.text_input(
                    "Email address",
                    placeholder="employee@company.com",
                )

                new_password = st.text_input(
                    "Temporary password",
                    type="password",
                    help="Must contain at least 12 characters.",
                )

                new_role = st.selectbox(
                    "Initial role",
                    ROLE_OPTIONS,
                )

                selected_department_label = st.selectbox(
                    "Department",
                    options=["Select a department"] + list(
                        department_options.keys()
                    ),
                    disabled=(new_role == "SUPER_ADMIN"),
                )

                create_submitted = st.form_submit_button(
                    "Create user",
                    type="primary",
                    use_container_width=True,
                )

            if create_submitted:

                if not new_full_name.strip():
                    st.error("Enter the user's full name.")

                elif len(new_full_name.strip()) < 2:
                    st.error("Full name must contain at least 2 characters.")

                elif not new_email.strip():
                    st.error("Enter an email address.")

                elif len(new_password) < 12:
                    st.error("Password must contain at least 12 characters.")

                elif (
                    new_role != "SUPER_ADMIN"
                    and selected_department_label == "Select a department"
                ):
                    st.error(
                        "A department is required for this role."
                    )

                else:

                    department_id = None

                    if (
                        new_role != "SUPER_ADMIN"
                        and selected_department_label in department_options
                    ):
                        department_id = department_options[
                            selected_department_label
                        ]

                    try:
                        with st.spinner("Creating user..."):

                            api.create_user(
                                token=token,
                                email=new_email.strip(),
                                full_name=new_full_name.strip(),
                                password=new_password,
                                role_name=new_role,
                                department_id=department_id,
                            )

                        st.success(
                            f"User {new_email.strip()} created successfully."
                        )

                        st.rerun()

                    except RuntimeError as exc:
                        st.error(f"Could not create user: {exc}")

    # USER LIST

    st.divider()

    heading_col, refresh_col = st.columns([4, 1])

    with heading_col:
        st.markdown("### Users")

    with refresh_col:
        refresh_users = st.button(
            "↻ Refresh",
            use_container_width=True,
        )

    try:
        with st.spinner("Loading users..."):
            users = fetch_management_users()

    except RuntimeError as exc:
        st.error(f"Could not load users: {exc}")
        return

    if not users:
        st.info("No users found.")
        return

    # USER SUMMARY

    total_users = len(users)

    department_admin_count = sum(
        1 for user in users
        if "DEPARTMENT_ADMIN" in user.get("roles", [])
    )

    employee_count = sum(
        1 for user in users
        if "EMPLOYEE" in user.get("roles", [])
    )

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric("Users", total_users)
    metric2.metric("Employees", employee_count)
    metric3.metric("Department admins", department_admin_count)

    st.divider()

    # USER RECORDS

    for user in users:

        user_id = str(user.get("id") or user.get("user_id"))
        full_name = get_user_display_name(user)
        email = user.get("email", "No email")
        roles = user.get("roles", []) or []
        department_id = user.get("department_id")

        department_name = (
            department_lookup.get(str(department_id), str(department_id))
            if department_id
            else "Unassigned"
        )

        role_label = ", ".join(roles) if roles else "No roles assigned"

        with st.container(border=True):

            top_left, top_right = st.columns([4, 1])

            with top_left:
                st.markdown(f"**{full_name}**")
                st.caption(email)

            with top_right:
                st.caption(" · ".join(roles) if roles else "No roles")

            info_col1, info_col2 = st.columns(2)

            with info_col1:
                st.caption(f"Department: {department_name}")

            with info_col2:
                st.caption(f"User ID: `{user_id}`")

            if super_admin:

                with st.expander("Manage user"):

                    # ASSIGN ROLE

                    st.markdown("**Assign a role**")

                    available_roles = [
                        role
                        for role in ROLE_OPTIONS
                        if role not in roles
                    ]

                    if available_roles:

                        role_to_add = st.selectbox(
                            "Role to assign",
                            available_roles,
                            key=f"add_role_select_{user_id}",
                        )

                        if st.button(
                            "Assign role",
                            key=f"add_role_button_{user_id}",
                        ):

                            try:
                                api.assign_user_role(
                                    token,
                                    user_id,
                                    role_to_add,
                                )

                                st.success(
                                    f"Assigned {role_to_add} to {email}."
                                )

                                st.rerun()

                            except RuntimeError as exc:
                                st.error(str(exc))

                    else:
                        st.caption("This user already has all available roles.")

                    st.divider()

                    # REMOVE ROLE

                    st.markdown("**Remove a role**")

                    if roles:

                        role_to_remove = st.selectbox(
                            "Role to remove",
                            roles,
                            key=f"remove_role_select_{user_id}",
                        )

                        if st.button(
                            "Remove role",
                            key=f"remove_role_button_{user_id}",
                        ):

                            try:
                                api.remove_user_role(
                                    token,
                                    user_id,
                                    role_to_remove,
                                )

                                st.success(
                                    f"Removed {role_to_remove} from {email}."
                                )

                                st.rerun()

                            except RuntimeError as exc:
                                st.error(str(exc))

                    else:
                        st.caption("This user has no assigned roles.")

                    st.divider()

                    # CHANGE DEPARTMENT

                    st.markdown("**Change department**")

                    if departments:

                        department_options = {
                            f"{department['name']} ({department['id']})":
                                str(department["id"])
                            for department in departments
                        }

                        current_department_label = next(
                            (
                                label
                                for label, value in department_options.items()
                                if value == str(department_id)
                            ),
                            None,
                        )

                        department_labels = list(department_options.keys())

                        default_index = (
                            department_labels.index(current_department_label)
                            if current_department_label in department_labels
                            else 0
                        )

                        new_department_label = st.selectbox(
                            "New department",
                            department_labels,
                            index=default_index,
                            key=f"department_select_{user_id}",
                        )

                        if st.button(
                            "Update department",
                            key=f"department_button_{user_id}",
                        ):

                            new_department_id = department_options[
                                new_department_label
                            ]

                            if new_department_id == str(department_id):
                                st.info("This user is already assigned to that department.")

                            else:
                                try:
                                    api.assign_user_department(
                                        token,
                                        user_id,
                                        new_department_id,
                                    )

                                    st.success(
                                        f"Updated department for {email}."
                                    )

                                    st.rerun()

                                except RuntimeError as exc:
                                    st.error(str(exc))

                    else:
                        st.info("No departments are available.")

            else:
                st.caption(
                    "Department Admin access is read-only in this section."
                )


# ==========================================
# APPLICATION ROUTER
# ==========================================

def main():

    if st.session_state.access_token is None:
        render_login()
        return

    # Do not allow a non-admin to open User Management
    # by manually changing the active page in session state.
    if (
        st.session_state.active_page == "User Management"
        and not is_admin()
    ):
        st.session_state.active_page = "Chat"

    render_sidebar()

    active_page = st.session_state.active_page

    if active_page == "Chat":
        render_chat()

    elif active_page == "Knowledge Base":
        render_knowledge_base()

    elif active_page == "User Management":
        render_user_management()

    else:
        st.session_state.active_page = "Chat"
        st.rerun()


if __name__ == "__main__":
    main()
