"""Dependency-free checks for the SQLite data model."""
import sqlite3
import unittest
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parents[1] / "schema.sql").read_text()


class TourismSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    def tearDown(self):
        self.db.close()

    def test_expected_tables_exist(self):
        names = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"users", "destinations", "packages", "bookings", "payments", "reviews"}.issubset(names))

    def test_package_requires_valid_destination(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""INSERT INTO packages(destination_id,title,category,duration_days,price_per_person,
                summary,highlights,includes_text) VALUES(999,'Invalid package','Nature',3,1000,'x','x','x')""")

    def test_booking_and_payment_relationships(self):
        destination_id = self.db.execute(
            "INSERT INTO destinations(name,state,country,short_description) VALUES('Test Hills','Himachal Pradesh','India','Test')"
        ).lastrowid
        user_id = self.db.execute(
            "INSERT INTO users(full_name,email,password_hash) VALUES('Test Customer','test@example.com','hash')"
        ).lastrowid
        package_id = self.db.execute("""INSERT INTO packages(destination_id,title,category,duration_days,
            price_per_person,summary,highlights,includes_text) VALUES(?, 'Hill Break','Nature',3,5000,'A test trip','Viewpoint','Stay')""", (destination_id,)).lastrowid
        booking_id = self.db.execute("""INSERT INTO bookings(booking_ref,user_id,package_id,travel_date,
            travelers,total_amount) VALUES('TPP-TEST01',?,?, '2027-01-10',2,10000)""", (user_id, package_id)).lastrowid
        self.db.execute("INSERT INTO payments(booking_id,amount,payment_method) VALUES(?,10000,'Pay at office')", (booking_id,))
        row = self.db.execute("""SELECT u.full_name,p.title,d.name,b.total_amount,pay.payment_status
            FROM bookings b JOIN users u ON u.user_id=b.user_id
            JOIN packages p ON p.package_id=b.package_id
            JOIN destinations d ON d.destination_id=p.destination_id
            JOIN payments pay ON pay.booking_id=b.booking_id""").fetchone()
        self.assertEqual(row, ("Test Customer", "Hill Break", "Test Hills", 10000.0, "Pending"))

    def test_only_one_payment_record_per_booking(self):
        user_id = self.db.execute("INSERT INTO users(full_name,email,password_hash) VALUES('A','a@b.com','x')").lastrowid
        dest_id = self.db.execute("INSERT INTO destinations(name,state,short_description) VALUES('Place','State','Desc')").lastrowid
        pkg_id = self.db.execute("""INSERT INTO packages(destination_id,title,category,duration_days,price_per_person,
            summary,highlights,includes_text) VALUES(?, 'Package','Nature',2,10,'s','h','i')""", (dest_id,)).lastrowid
        booking_id = self.db.execute("INSERT INTO bookings(booking_ref,user_id,package_id,travel_date,travelers,total_amount) VALUES('REF1',?,?, '2027-01-10',1,10)", (user_id,pkg_id)).lastrowid
        self.db.execute("INSERT INTO payments(booking_id,amount,payment_method) VALUES(?,10,'Pay at office')", (booking_id,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO payments(booking_id,amount,payment_method) VALUES(?,10,'Card (demo)')", (booking_id,))


if __name__ == "__main__":
    unittest.main(verbosity=2)
