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
