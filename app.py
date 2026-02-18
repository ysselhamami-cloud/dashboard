from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Dict, List

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = "ourhelpdesk-dev-secret"

USERS: Dict[str, Dict[str, str]] = {
    "client": {
        "password": "client",
        "role": "client",
        "display_name": "Client User",
        "full_name": "Client User",
        "phone": "+212 60 112233",
        "position": "Accountant",
        "company": "Atlas Manufacturing",
        "email": "client@example.com",
        "avatar": "https://api.dicebear.com/9.x/initials/svg?seed=Client",
    },
    "itdev": {
        "password": "itdev",
        "role": "itdev",
        "display_name": "IT Developer",
        "full_name": "IT Developer",
        "phone": "+212 61 445566",
        "position": "IT Developer",
        "company": "OurHelpdesk IT",
        "email": "itdev@example.com",
        "avatar": "https://api.dicebear.com/9.x/initials/svg?seed=ITDEV",
    },
    "admin": {
        "password": "admin",
        "role": "admin",
        "display_name": "Platform Admin",
        "full_name": "Platform Admin",
        "phone": "+212 62 778899",
        "position": "Administrator",
        "company": "OurHelpdesk",
        "email": "admin@example.com",
        "avatar": "https://api.dicebear.com/9.x/initials/svg?seed=Admin",
    },
}

TICKETS: List[Dict[str, str]] = [
    {
        "id": 1003,
        "creator": "client",
        "title": "Email delay on mobile",
        "description": "Mails arrive 40 min late on mobile app.",
        "status": "Resolved",
        "priority": "Low",
        "category": "Software",
        "assigned_to": "itdev",
        "note": "",
    },
    {
        "id": 1002,
        "creator": "client",
        "title": "New monitor request",
        "description": "Need a second monitor for design tasks.",
        "status": "Open",
        "priority": "Medium",
        "category": "Hardware",
        "assigned_to": "",
        "note": "",
    },
    {
        "id": 1001,
        "creator": "client",
        "title": "VPN access issue",
        "description": "Cannot connect to VPN from home.",
        "status": "In Progress",
        "priority": "High",
        "category": "Network",
        "assigned_to": "itdev",
        "note": "",
    },
]

INTERVENTIONS: List[Dict[str, str]] = [
    {
        "when": "2026-02-18 14:12",
        "author": "itdev",
        "summary": "Reconfigured sync interval and push settings.",
        "status": "Intervention Completed",
        "minutes": "20",
        "ticket_id": 1003,
    }
]

ACTIVITY_LOGS: List[str] = [
    "[2026-02-18 14:01] admin — Assigned ticket #1001 to itdev",
    "[2026-02-18 14:01] itdev — Added intervention note on ticket #1001",
    "[2026-02-18 14:01] client — Created ticket #1002",
]


def current_user() -> Dict[str, str] | None:
    username = session.get("username")
    if not username:
        return None
    profile = USERS.get(username)
    if not profile:
        session.clear()
        return None
    return {"username": username, **profile}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def visible_tickets(user: Dict[str, str]) -> List[Dict[str, str]]:
    if user["role"] == "client":
        return [ticket for ticket in TICKETS if ticket["creator"] == user["username"]]
    if user["role"] == "itdev":
        return [
            ticket
            for ticket in TICKETS
            if ticket.get("assigned_to") == user["username"] or ticket["creator"] == user["username"]
        ]
    return list(TICKETS)


def customer_rows() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for username, profile in USERS.items():
        if profile["role"] == "client":
            rows.append(
                {
                    "username": username,
                    "name": profile["full_name"],
                    "phone": profile["phone"],
                    "position": profile["position"],
                    "company": profile["company"],
                }
            )
    return rows


def summary_counts() -> Dict[str, str]:
    open_count = sum(1 for ticket in TICKETS if ticket["status"] == "Open")
    progress_count = sum(1 for ticket in TICKETS if ticket["status"] == "In Progress")
    resolved_count = sum(1 for ticket in TICKETS if ticket["status"] == "Resolved")
    return {
        "open": str(open_count),
        "progress": str(progress_count),
        "resolved": str(resolved_count),
        "closed": "0",
        "avg_response": "2.7h",
        "avg_resolution": "14.7h",
        "overdue": "1",
    }


def find_ticket(ticket_id: int | None):
    if ticket_id is None:
        return None
    for ticket in TICKETS:
        if ticket["id"] == ticket_id:
            return ticket
    return None


@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(username)

        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            return redirect(request.args.get("next") or url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    selected_id = request.args.get("ticket", type=int)

    tickets = visible_tickets(user)
    selected_ticket = find_ticket(selected_id) if selected_id else (tickets[0] if tickets else None)

    tabs = {
        "client": ["Tickets"],
        "itdev": ["Tickets", "Interventions", "Customers", "My Avatar"],
        "admin": ["Dashboard", "Tickets", "Interventions", "Profile / Settings"],
    }
    sidebar = {
        "client": [("CLIENT", ["Create Ticket", "My Tickets"])],
        "itdev": [("IT/DEV", ["Tickets", "Interventions", "Customers", "Avatar"] )],
        "admin": [
            ("ANALYSE", ["Dashboards"]),
            ("WORK", ["Contacts"]),
            ("SUPPORT", ["Dispatch", "Problems", "Change", "Requests", "Incidents", "Interventions", "Settings"]),
        ],
    }

    selected_customer = USERS.get(selected_ticket["creator"], {}) if selected_ticket else {}

    return render_template(
        "dashboard.html",
        user=user,
        tabs=tabs[user["role"]],
        sidebar_sections=sidebar[user["role"]],
        tickets=tickets,
        selected_ticket=selected_ticket,
        selected_customer=selected_customer,
        interventions=INTERVENTIONS,
        customers=customer_rows(),
        summary=summary_counts(),
        activity_logs=ACTIVITY_LOGS,
        today=datetime.utcnow().strftime("%Y-%m-%d"),
    )


@app.post("/tickets/create")
@roles_required("client", "itdev", "admin")
def create_ticket():
    user = current_user()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "Hardware")
    priority = request.form.get("priority", "Low")

    if not title or not description:
        flash("Title and description are required.", "error")
        return redirect(url_for("dashboard"))

    next_id = max(ticket["id"] for ticket in TICKETS) + 1 if TICKETS else 1001
    TICKETS.insert(
        0,
        {
            "id": next_id,
            "creator": user["username"],
            "title": title,
            "description": description,
            "status": "Open",
            "priority": priority,
            "category": category,
            "assigned_to": "",
            "note": "",
        },
    )
    ACTIVITY_LOGS.insert(0, f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {user['username']} — Created ticket #{next_id}")
    flash(f"Ticket #{next_id} created.", "success")
    return redirect(url_for("dashboard", ticket=next_id))


@app.post("/tickets/<int:ticket_id>/update")
@roles_required("itdev", "admin")
def update_ticket(ticket_id: int):
    user = current_user()
    ticket = find_ticket(ticket_id)
    if not ticket:
        abort(404)

    if user["role"] == "itdev" and ticket.get("assigned_to") != user["username"] and ticket["creator"] != user["username"]:
        abort(403)

    ticket["status"] = request.form.get("status", ticket["status"])
    ticket["priority"] = request.form.get("priority", ticket["priority"])
    ticket["note"] = request.form.get("note", "").strip()

    # Only admin can qualify/assign tickets.
    if user["role"] == "admin":
        ticket["assigned_to"] = request.form.get("assigned_to", ticket.get("assigned_to", ""))

    flash(f"Ticket #{ticket_id} updated.", "success")
    return redirect(url_for("dashboard", ticket=ticket_id))


@app.post("/interventions/add")
@roles_required("itdev", "admin")
def add_intervention():
    user = current_user()
    summary = request.form.get("summary", "").strip()
    status = request.form.get("status", "In Progress")
    minutes = request.form.get("minutes", "")
    ticket_id = request.form.get("ticket_id", type=int)

    ticket = find_ticket(ticket_id)
    if not ticket:
        abort(404)

    if user["role"] == "itdev" and ticket.get("assigned_to") != user["username"] and ticket["creator"] != user["username"]:
        abort(403)

    if not summary:
        flash("Intervention summary is required.", "error")
        return redirect(url_for("dashboard", ticket=ticket_id))

    INTERVENTIONS.insert(
        0,
        {
            "when": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "author": user["username"],
            "summary": summary,
            "status": status,
            "minutes": minutes or "0",
            "ticket_id": ticket_id,
        },
    )
    flash("Intervention added.", "success")
    return redirect(url_for("dashboard", ticket=ticket_id))


@app.post("/profile/update")
@roles_required("admin")
def profile_update():
    user = current_user()
    profile = USERS[user["username"]]
    profile["full_name"] = request.form.get("full_name", profile["full_name"])
    profile["email"] = request.form.get("email", profile["email"])
    new_password = request.form.get("password", "").strip()
    if new_password:
        profile["password"] = new_password
    flash("Profile updated.", "success")
    return redirect(url_for("dashboard"))


@app.post("/profile/avatar")
@roles_required("itdev")
def profile_avatar_update():
    user = current_user()
    avatar = request.form.get("avatar", "").strip()
    if not avatar:
        flash("Avatar URL is required.", "error")
        return redirect(url_for("dashboard"))

    USERS[user["username"]]["avatar"] = avatar
    flash("Avatar updated.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
