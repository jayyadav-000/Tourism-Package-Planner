from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from typing import Any

from flask import (
    Flask, abort, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DATABASE = INSTANCE_DIR / "tourism.db"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "tourism-planner-local-demo-2026"),
    DATABASE=str(DATABASE),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('customer','admin')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS destinations (
    destination_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    short_description TEXT NOT NULL,
    best_season TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS packages (
    package_id INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    duration_days INTEGER NOT NULL CHECK(duration_days > 0),
    price_per_person REAL NOT NULL CHECK(price_per_person >= 0),
    max_travelers INTEGER NOT NULL DEFAULT 12 CHECK(max_travelers > 0),
    available_slots INTEGER NOT NULL DEFAULT 12 CHECK(available_slots >= 0),
    summary TEXT NOT NULL,
    highlights TEXT NOT NULL,
    includes_text TEXT NOT NULL,
    is_featured INTEGER NOT NULL DEFAULT 0 CHECK(is_featured IN (0,1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(destination_id) REFERENCES destinations(destination_id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_ref TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    package_id INTEGER NOT NULL,
    travel_date TEXT NOT NULL,
    travelers INTEGER NOT NULL CHECK(travelers > 0),
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    status TEXT NOT NULL DEFAULT 'Confirmed' CHECK(status IN ('Confirmed','Cancelled','Completed')),
    special_request TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY(package_id) REFERENCES packages(package_id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL UNIQUE,
    amount REAL NOT NULL CHECK(amount >= 0),
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'Pending' CHECK(payment_status IN ('Pending','Paid','Refunded')),
    transaction_ref TEXT,
    paid_at TEXT,
    FOREIGN KEY(booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    package_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, package_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(package_id) REFERENCES packages(package_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_packages_destination ON packages(destination_id);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_package ON bookings(package_id);
CREATE INDEX IF NOT EXISTS idx_bookings_travel_date ON bookings(travel_date);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)

    if db.execute("SELECT COUNT(*) FROM destinations").fetchone()[0] == 0:
        destinations = [
            ("Manali", "Himachal Pradesh", "India", "Snow-capped peaks, pine forests and relaxed mountain cafés.", "October to June"),
            ("Jaipur", "Rajasthan", "India", "Royal forts, colorful bazaars and timeless Rajasthani culture.", "October to March"),
            ("Goa", "Goa", "India", "Golden beaches, coastal food and laid-back sunset evenings.", "November to February"),
            ("Rishikesh", "Uttarakhand", "India", "Ganga-side serenity, yoga retreats and adventure experiences.", "September to April"),
            ("Srinagar", "Jammu & Kashmir", "India", "Dal Lake, gardens and breathtaking Himalayan scenery.", "April to October"),
            ("Darjeeling", "West Bengal", "India", "Tea gardens, toy train rides and views of the Kanchenjunga.", "March to May; October to December"),
            ("Udaipur", "Rajasthan", "India", "Romantic lakes, palaces and beautiful heritage streets.", "September to March"),
            ("Varanasi", "Uttar Pradesh", "India", "Ancient ghats, spiritual traditions and unforgettable river views.", "October to March"),
        ]
        db.executemany(
            "INSERT INTO destinations(name,state,country,short_description,best_season) VALUES(?,?,?,?,?)",
            destinations,
        )

        package_rows = [
            ("Mountain Escape: Manali", "Adventure", 5, 12999, 12, 12, "A refreshing mountain holiday with scenic drives, local food and time to explore Old Manali.", "Solang Valley|Hadimba Temple|Mall Road|Atal Tunnel viewpoint", "Hotel stay|Breakfast|Local transfers|Sightseeing", 1, 1),
            ("Royal Jaipur Weekend", "Heritage", 3, 8499, 15, 15, "Discover Jaipur's royal architecture, vibrant markets and delicious Rajasthani cuisine.", "Amber Fort|Hawa Mahal|City Palace|Local bazaar walk", "Hotel stay|Breakfast|Airport or station pickup|Guided city tour", 1, 1),
            ("Goa Beach & Beyond", "Beach", 4, 10999, 16, 16, "A relaxed coastal break balancing beach time, Portuguese-era streets and local experiences.", "Calangute Beach|Fort Aguada|Fontainhas|Sunset point", "Hotel stay|Breakfast|North Goa sightseeing|Welcome drink", 1, 1),
            ("Rishikesh Adventure Trail", "Adventure", 3, 6999, 12, 12, "A compact getaway with river views, a guided rafting experience and peaceful evenings.", "River rafting|Ram Jhula|Ganga Aarti|Beatles Ashram area", "Camp stay|Breakfast and dinner|Rafting (seasonal)|Local transfers", 0, 1),
            ("Kashmir Valley Experience", "Nature", 6, 18999, 10, 10, "Enjoy the landscapes of Kashmir with a houseboat stay and relaxed valley sightseeing.", "Dal Lake|Mughal Gardens|Gulmarg day trip|Houseboat evening", "Hotel and houseboat stay|Breakfast|Shikara ride|Sightseeing transfers", 1, 1),
            ("Darjeeling Tea Trails", "Nature", 4, 11999, 10, 10, "Slow down in the hills with tea gardens, heritage railways and mountain viewpoints.", "Tiger Hill|Tea garden visit|Batasia Loop|Darjeeling toy train area", "Hotel stay|Breakfast|Local sightseeing|Station transfers", 0, 1),
            ("Udaipur Lakeside Heritage", "Heritage", 3, 9299, 12, 12, "Explore lakefront promenades, historic palaces and the old lanes of the City of Lakes.", "City Palace|Lake Pichola|Saheliyon-ki-Bari|Bagore Ki Haveli", "Hotel stay|Breakfast|Boat ride|Guided heritage walk", 0, 1),
            ("Varanasi Spiritual Journey", "Culture", 3, 7799, 14, 14, "Experience the timeless ghats, morning boat ride and cultural lanes of Varanasi.", "Dashashwamedh Ghat|Sunrise boat ride|Sarnath|Evening Ganga Aarti", "Hotel stay|Breakfast|Boat ride|Local guide", 0, 1),
        ]
        package_destinations = {
            "Mountain Escape: Manali": "Manali",
            "Royal Jaipur Weekend": "Jaipur",
            "Goa Beach & Beyond": "Goa",
            "Rishikesh Adventure Trail": "Rishikesh",
            "Kashmir Valley Experience": "Srinagar",
            "Darjeeling Tea Trails": "Darjeeling",
            "Udaipur Lakeside Heritage": "Udaipur",
            "Varanasi Spiritual Journey": "Varanasi",
        }
        for row in package_rows:
            title, category, days, price, max_people, slots, summary, highlights, includes, featured, active = row
            city = package_destinations[title]
            dest = db.execute("SELECT destination_id FROM destinations WHERE name=?", (city,)).fetchone()
            if dest is None:
                dest = db.execute("SELECT destination_id FROM destinations WHERE name='Manali'").fetchone()
            db.execute(
                """INSERT INTO packages(destination_id,title,category,duration_days,price_per_person,max_travelers,
                   available_slots,summary,highlights,includes_text,is_featured,is_active)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (dest[0], title, category, days, price, max_people, slots, summary, highlights, includes, featured, active),
            )

    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO users(full_name,email,password_hash,phone,role) VALUES(?,?,?,?,?)",
            ("Tourism Admin", "admin@tourism.com", generate_password_hash("Admin123!"), "9999999999", "admin"),
        )
        db.execute(
            "INSERT INTO users(full_name,email,password_hash,phone,role) VALUES(?,?,?,?,?)",
            ("Demo Customer", "demo@tourism.com", generate_password_hash("Demo123!"), "9876543210", "customer"),
        )
    db.commit()
    db.close()


@app.before_request
def ensure_database() -> None:
    # Keep first launch simple: create the database automatically when it is missing.
    if not Path(app.config["DATABASE"]).exists():
        init_db()


@app.context_processor
def inject_globals() -> dict[str, Any]:
    return {"current_year": datetime.now().year, "today_iso": date.today().isoformat()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in with the admin account.", "info")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT user_id,full_name,email,phone,role FROM users WHERE user_id=?", (user_id,)).fetchone()


@app.route("/")
def home():
    db = get_db()
    featured = db.execute(
        """SELECT p.*, d.name AS destination_name, d.state FROM packages p
           JOIN destinations d ON d.destination_id=p.destination_id
           WHERE p.is_active=1 ORDER BY p.is_featured DESC, p.package_id LIMIT 4"""
    ).fetchall()
    destinations = db.execute(
        """SELECT d.*, COUNT(p.package_id) AS package_count FROM destinations d
           LEFT JOIN packages p ON p.destination_id=d.destination_id AND p.is_active=1
           GROUP BY d.destination_id ORDER BY package_count DESC, d.name LIMIT 6"""
    ).fetchall()
    return render_template("index.html", featured=featured, destinations=destinations)


@app.route("/packages")
def packages():
    db = get_db()
    search = request.args.get("q", "").strip()
    destination_id = request.args.get("destination", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "recommended").strip()
    query = """SELECT p.*, d.name AS destination_name, d.state FROM packages p
               JOIN destinations d ON d.destination_id=p.destination_id WHERE p.is_active=1"""
    params: list[Any] = []
    if search:
        query += " AND (p.title LIKE ? OR p.summary LIKE ? OR d.name LIKE ? OR d.state LIKE ?)"
        params += [f"%{search}%"] * 4
    if destination_id.isdigit():
        query += " AND d.destination_id=?"
        params.append(int(destination_id))
    if category:
        query += " AND p.category=?"
        params.append(category)
    order_by = {
        "price_low": "p.price_per_person ASC",
        "price_high": "p.price_per_person DESC",
        "duration": "p.duration_days ASC",
        "recommended": "p.is_featured DESC, p.package_id ASC",
    }.get(sort, "p.is_featured DESC, p.package_id ASC")
    items = db.execute(query + f" ORDER BY {order_by}", params).fetchall()
    destinations = db.execute("SELECT destination_id,name FROM destinations ORDER BY name").fetchall()
    categories = db.execute("SELECT DISTINCT category FROM packages WHERE is_active=1 ORDER BY category").fetchall()
    return render_template("packages.html", packages=items, destinations=destinations,
                           categories=categories, q=search, selected_destination=destination_id,
                           selected_category=category, selected_sort=sort)


@app.route("/package/<int:package_id>")
def package_detail(package_id: int):
    item = get_db().execute(
        """SELECT p.*,d.name AS destination_name,d.state,d.short_description AS destination_description,
           d.best_season FROM packages p JOIN destinations d ON d.destination_id=p.destination_id
           WHERE p.package_id=? AND p.is_active=1""", (package_id,)
    ).fetchone()
    if item is None:
        abort(404)
    return render_template("package_detail.html", package=item)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "error")
        else:
            try:
                cur = get_db().execute(
                    "INSERT INTO users(full_name,email,password_hash,phone) VALUES(?,?,?,?)",
                    (name, email, generate_password_hash(password), phone),
                )
                get_db().commit()
                session.update(user_id=cur.lastrowid, role="customer", full_name=name)
                flash("Your account is ready. Happy planning!", "success")
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                flash("That email is already registered. Please sign in instead.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["user_id"], role=user["role"], full_name=user["full_name"])
            flash(f"Welcome back, {user['full_name'].split()[0]}!", "success")
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("admin_dashboard") if user["role"] == "admin" else url_for("home"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))


@app.route("/book/<int:package_id>", methods=["POST"])
@login_required
def book_package(package_id: int):
    db = get_db()
    item = db.execute("SELECT * FROM packages WHERE package_id=? AND is_active=1", (package_id,)).fetchone()
    if item is None:
        abort(404)
    try:
        travel_date = date.fromisoformat(request.form.get("travel_date", ""))
        travelers = int(request.form.get("travelers", "1"))
    except (ValueError, TypeError):
        flash("Please choose a valid travel date and number of travelers.", "error")
        return redirect(url_for("package_detail", package_id=package_id))
    if travel_date < date.today():
        flash("Travel date must be today or a future date.", "error")
        return redirect(url_for("package_detail", package_id=package_id))
    if travelers < 1 or travelers > item["max_travelers"]:
        flash(f"Choose between 1 and {item['max_travelers']} travelers.", "error")
        return redirect(url_for("package_detail", package_id=package_id))
    if travelers > item["available_slots"]:
        flash("Not enough seats are currently available for this package.", "error")
        return redirect(url_for("package_detail", package_id=package_id))

    total = round(item["price_per_person"] * travelers, 2)
    booking_ref = "TPP-" + secrets.token_hex(3).upper()
    method = request.form.get("payment_method", "Pay at office")
    if method not in {"Pay at office", "UPI (demo)", "Card (demo)"}:
        method = "Pay at office"
    try:
        # A single transaction keeps booking, seat count and payment record consistent.
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "UPDATE packages SET available_slots=available_slots-? WHERE package_id=? AND available_slots>=?",
            (travelers, package_id, travelers),
        )
        if db.execute("SELECT changes()").fetchone()[0] != 1:
            db.rollback()
            flash("Those seats were just taken. Please try another traveler count.", "error")
            return redirect(url_for("package_detail", package_id=package_id))
        cur = db.execute(
            """INSERT INTO bookings(booking_ref,user_id,package_id,travel_date,travelers,total_amount,special_request)
               VALUES(?,?,?,?,?,?,?)""",
            (booking_ref, session["user_id"], package_id, travel_date.isoformat(), travelers, total,
             request.form.get("special_request", "").strip()[:500]),
        )
        db.execute(
            "INSERT INTO payments(booking_id,amount,payment_method,payment_status) VALUES(?,?,?,'Pending')",
            (cur.lastrowid, total, method),
        )
        db.commit()
    except sqlite3.Error:
        db.rollback()
        flash("Booking could not be completed. Please try again.", "error")
        return redirect(url_for("package_detail", package_id=package_id))
    return redirect(url_for("booking_success", booking_ref=booking_ref))


@app.route("/booking-success/<booking_ref>")
@login_required
def booking_success(booking_ref: str):
    booking = get_db().execute(
        """SELECT b.*,p.title,p.duration_days,d.name AS destination_name,pay.payment_method,pay.payment_status
           FROM bookings b JOIN packages p ON p.package_id=b.package_id
           JOIN destinations d ON d.destination_id=p.destination_id
           LEFT JOIN payments pay ON pay.booking_id=b.booking_id
           WHERE b.booking_ref=? AND b.user_id=?""", (booking_ref, session["user_id"])
    ).fetchone()
    if booking is None:
        abort(404)
    return render_template("booking_success.html", booking=booking)


@app.route("/my-bookings")
@login_required
def my_bookings():
    items = get_db().execute(
        """SELECT b.*,p.title,p.duration_days,d.name AS destination_name,
           pay.payment_method,pay.payment_status FROM bookings b
           JOIN packages p ON p.package_id=b.package_id
           JOIN destinations d ON d.destination_id=p.destination_id
           LEFT JOIN payments pay ON pay.booking_id=b.booking_id
           WHERE b.user_id=? ORDER BY b.created_at DESC""", (session["user_id"],)
    ).fetchall()
    return render_template("my_bookings.html", bookings=items)


@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id: int):
    db = get_db()
    booking = db.execute(
        "SELECT * FROM bookings WHERE booking_id=? AND user_id=?", (booking_id, session["user_id"])
    ).fetchone()
    if booking is None:
        abort(404)
    if booking["status"] != "Confirmed" or booking["travel_date"] < date.today().isoformat():
        flash("This booking can no longer be cancelled online.", "error")
    else:
        db.execute("UPDATE bookings SET status='Cancelled' WHERE booking_id=?", (booking_id,))
        db.execute("UPDATE packages SET available_slots=available_slots+? WHERE package_id=?",
                   (booking["travelers"], booking["package_id"]))
        db.execute("UPDATE payments SET payment_status='Refunded' WHERE booking_id=? AND payment_status='Paid'",
                   (booking_id,))
        db.commit()
        flash("Booking cancelled. Seat availability has been restored.", "success")
    return redirect(url_for("my_bookings"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        "packages": db.execute("SELECT COUNT(*) FROM packages WHERE is_active=1").fetchone()[0],
        "customers": db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
        "bookings": db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        "revenue": db.execute("SELECT COALESCE(SUM(total_amount),0) FROM bookings WHERE status!='Cancelled'").fetchone()[0],
    }
    recent = db.execute(
        """SELECT b.*,u.full_name,p.title,d.name AS destination_name FROM bookings b
           JOIN users u ON u.user_id=b.user_id JOIN packages p ON p.package_id=b.package_id
           JOIN destinations d ON d.destination_id=p.destination_id ORDER BY b.created_at DESC LIMIT 8"""
    ).fetchall()
    package_list = db.execute(
        """SELECT p.*,d.name AS destination_name FROM packages p JOIN destinations d
           ON d.destination_id=p.destination_id ORDER BY p.package_id DESC"""
    ).fetchall()
    all_destinations = db.execute("SELECT destination_id,name,state FROM destinations ORDER BY name").fetchall()
    return render_template("admin.html", stats=stats, recent=recent, packages=package_list, all_destinations=all_destinations)


@app.route("/admin/package", methods=["POST"])
@admin_required
def admin_add_package():
    fields = package_form_values()
    if not fields:
        return redirect(url_for("admin_dashboard"))
    try:
        get_db().execute(
            """INSERT INTO packages(destination_id,title,category,duration_days,price_per_person,max_travelers,
               available_slots,summary,highlights,includes_text,is_featured,is_active)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,1)""", fields
        )
        get_db().commit()
        flash("New package added successfully.", "success")
    except sqlite3.Error as exc:
        flash(f"Package could not be added: {exc}", "error")
    return redirect(url_for("admin_dashboard"))


def package_form_values():
    try:
        destination_id = int(request.form.get("destination_id", ""))
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        days = int(request.form.get("duration_days", ""))
        price = float(request.form.get("price_per_person", ""))
        slots = int(request.form.get("available_slots", ""))
        summary = request.form.get("summary", "").strip()
        highlights = request.form.get("highlights", "").strip()
        includes = request.form.get("includes_text", "").strip()
        featured = 1 if request.form.get("is_featured") == "on" else 0
        exists = get_db().execute("SELECT 1 FROM destinations WHERE destination_id=?", (destination_id,)).fetchone()
        if not exists or not title or not category or not summary or days < 1 or price < 0 or slots < 0:
            raise ValueError
        return (destination_id, title, category, days, price, max(slots, 1), slots,
                summary, highlights, includes, featured)
    except (ValueError, TypeError):
        flash("Please complete the package form with valid values.", "error")
        return None


@app.route("/admin/package/<int:package_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_package(package_id: int):
    db = get_db()
    item = db.execute("SELECT is_active FROM packages WHERE package_id=?", (package_id,)).fetchone()
    if item is None:
        abort(404)
    db.execute("UPDATE packages SET is_active=? WHERE package_id=?", (0 if item[0] else 1, package_id))
    db.commit()
    flash("Package visibility updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/booking/<int:booking_id>/status", methods=["POST"])
@admin_required
def admin_booking_status(booking_id: int):
    status = request.form.get("status", "")
    if status not in {"Confirmed", "Completed", "Cancelled"}:
        abort(400)
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
    if booking is None:
        abort(404)
    if booking["status"] != status:
        if status == "Cancelled" and booking["status"] != "Cancelled":
            db.execute("UPDATE packages SET available_slots=available_slots+? WHERE package_id=?",
                       (booking["travelers"], booking["package_id"]))
        elif booking["status"] == "Cancelled" and status != "Cancelled":
            package = db.execute("SELECT available_slots FROM packages WHERE package_id=?", (booking["package_id"],)).fetchone()
            if package[0] < booking["travelers"]:
                flash("Not enough slots to reactivate this booking.", "error")
                return redirect(url_for("admin_dashboard"))
            db.execute("UPDATE packages SET available_slots=available_slots-? WHERE package_id=?",
                       (booking["travelers"], booking["package_id"]))
        db.execute("UPDATE bookings SET status=? WHERE booking_id=?", (status, booking_id))
        db.commit()
        flash("Booking status updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you are looking for could not be found."), 404


if __name__ == "__main__":
    init_db()
    
    app.run(debug=True)
