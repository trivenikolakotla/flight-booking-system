import json
import os
import mysql.connector
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DB = dict(host="localhost", port=3306, user="root", password="triveni@123", database="flight_booking_db")

def get_conn():
    return mysql.connector.connect(**DB)

# Simple in-memory session store: token -> {user_id, role, name, email}
sessions = {}

def get_session(headers):
    token = headers.get("X-Token", "")
    return sessions.get(token)

def make_token(user_id):
    import time, hashlib
    raw = f"{user_id}-{time.time()}"
    return hashlib.md5(raw.encode()).hexdigest()

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  [{self.command}] {self.path}")

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Token")

    def send_json(self, data, code=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.cors()
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, filename, ctype="text/html"):
        fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        if not os.path.exists(fpath):
            self.send_json({"error": "File not found"}, 404); return
        with open(fpath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.cors()
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        sess = get_session(self.headers)
        try:
            if path in ["/", "/index.html"]:          self.serve_file("login.html")
            elif path == "/dashboard.html":            self.serve_file("dashboard.html")
            elif path == "/api/flights":               self.get_flights()
            elif path == "/api/airlines":              self.get_airlines()
            elif path == "/api/customers":             self.get_customers(sess)
            elif path == "/api/bookings":              self.get_bookings(sess)
            elif path == "/api/stats":                 self.get_stats(sess)
            elif path == "/api/me":                    self.send_json({"success": True, "data": sess} if sess else {"success": False})
            else:                                      self.send_json({"error": "Not found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        sess = get_session(self.headers)
        try:
            if   path == "/api/login":          self.login(body)
            elif path == "/api/register":       self.register(body)
            elif path == "/api/logout":         self.logout()
            elif path == "/api/book":           self.add_booking(body, sess)
            elif path == "/api/cancel":         self.cancel_booking(body, sess)
            elif path == "/api/add_flight":     self.add_flight(body, sess)
            elif path == "/api/edit_flight":    self.edit_flight(body, sess)
            elif path == "/api/delete_flight":  self.delete_flight(body, sess)
            elif path == "/api/add_airline":    self.add_airline(body, sess)
            elif path == "/api/edit_airline":   self.edit_airline(body, sess)
            elif path == "/api/delete_airline": self.delete_airline(body, sess)
            elif path == "/api/sql":            self.run_sql(body, sess)
            else:                               self.send_json({"error": "Not found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── AUTH ──────────────────────────────────────────────────────
    def login(self, body):
        email = body.get("email","").strip()
        pwd   = body.get("password","").strip()
        if not email or not pwd:
            return self.send_json({"success": False, "error": "Email and password required"})
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, pwd))
        user = cur.fetchone(); conn.close()
        if not user:
            return self.send_json({"success": False, "error": "Invalid email or password"})
        token = make_token(user["user_id"])
        sessions[token] = {"user_id": user["user_id"], "role": user["role"],
                           "name": user["name"], "email": user["email"]}
        self.send_json({"success": True, "token": token, "role": user["role"],
                        "name": user["name"], "user_id": user["user_id"]})

    def register(self, body):
        name  = body.get("name","").strip()
        email = body.get("email","").strip()
        pwd   = body.get("password","").strip()
        if not name or not email or not pwd:
            return self.send_json({"success": False, "error": "All fields required"})
        conn = get_conn(); cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name,email,password,role) VALUES (%s,%s,%s,'user')", (name,email,pwd))
            uid = cur.lastrowid
            cur.execute("INSERT INTO customers (user_id,name,email) VALUES (%s,%s,%s)", (uid,name,email))
            conn.commit()
            self.send_json({"success": True, "message": "Account created! Please login."})
        except mysql.connector.IntegrityError:
            self.send_json({"success": False, "error": "Email already registered"})
        finally:
            conn.close()

    def logout(self):
        token = self.headers.get("X-Token","")
        sessions.pop(token, None)
        self.send_json({"success": True})

    def require_admin(self, sess):
        if not sess or sess.get("role") != "admin":
            self.send_json({"success": False, "error": "Admin access required"}, 403)
            return False
        return True

    def require_login(self, sess):
        if not sess:
            self.send_json({"success": False, "error": "Please login first"}, 401)
            return False
        return True

    # ── FLIGHTS ───────────────────────────────────────────────────
    def get_flights(self):
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT f.flight_id, a.name AS airline, a.code, a.logo_color,
                   f.departure, f.arrival, f.departure_time, f.arrival_time,
                   f.status, f.total_seats, f.available_seats, f.price
            FROM flights f JOIN airlines a ON f.airline_id = a.airline_id
            ORDER BY f.departure_time
        """)
        self.send_json({"success": True, "data": cur.fetchall()})
        conn.close()

    def add_flight(self, body, sess):
        if not self.require_admin(sess): return
        req = ["airline_id","departure","arrival","departure_time","arrival_time","price"]
        for f in req:
            if not body.get(f): return self.send_json({"success": False, "error": f"{f} is required"})
        conn = get_conn(); cur = conn.cursor()
        seats = int(body.get("total_seats", 180))
        cur.execute("""INSERT INTO flights
            (airline_id,departure,arrival,departure_time,arrival_time,total_seats,available_seats,price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (body["airline_id"], body["departure"], body["arrival"],
             body["departure_time"], body["arrival_time"], seats, seats, body["price"]))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": "Flight added successfully"})

    def edit_flight(self, body, sess):
        if not self.require_admin(sess): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""UPDATE flights SET airline_id=%s, departure=%s, arrival=%s,
            departure_time=%s, arrival_time=%s, status=%s, price=%s WHERE flight_id=%s""",
            (body["airline_id"], body["departure"], body["arrival"],
             body["departure_time"], body["arrival_time"], body["status"],
             body["price"], body["flight_id"]))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": "Flight updated"})

    def delete_flight(self, body, sess):
        if not self.require_admin(sess): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM flights WHERE flight_id=%s", (body["flight_id"],))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": "Flight deleted"})

    # ── AIRLINES ──────────────────────────────────────────────────
    def get_airlines(self):
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.*, COUNT(f.flight_id) AS total_flights
            FROM airlines a LEFT JOIN flights f ON a.airline_id = f.airline_id
            GROUP BY a.airline_id ORDER BY a.name
        """)
        self.send_json({"success": True, "data": cur.fetchall()})
        conn.close()

    def add_airline(self, body, sess):
        if not self.require_admin(sess): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("INSERT INTO airlines (name,country,code,logo_color) VALUES (%s,%s,%s,%s)",
            (body["name"], body["country"], body["code"], body.get("logo_color","#1a237e")))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": "Airline added"})

    def edit_airline(self, body, sess):
        if not self.require_admin(sess): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE airlines SET name=%s, country=%s, code=%s, logo_color=%s WHERE airline_id=%s",
            (body["name"], body["country"], body["code"], body.get("logo_color","#1a237e"), body["airline_id"]))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": "Airline updated"})

    def delete_airline(self, body, sess):
        if not self.require_admin(sess): return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM airlines WHERE airline_id=%s", (body["airline_id"],))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": "Airline deleted"})

    # ── BOOKINGS ──────────────────────────────────────────────────
    def get_bookings(self, sess):
        if not self.require_login(sess): return
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        if sess["role"] == "admin":
            cur.execute("""
                SELECT b.booking_id, c.name AS customer, c.email, c.phone,
                       a.name AS airline, f.departure, f.arrival,
                       f.departure_time, b.seats, b.total_price, b.status, b.booked_at
                FROM bookings b
                JOIN customers c ON b.customer_id = c.customer_id
                JOIN flights f   ON b.flight_id   = f.flight_id
                JOIN airlines a  ON f.airline_id  = a.airline_id
                ORDER BY b.booked_at DESC
            """)
        else:
            cur.execute("""
                SELECT b.booking_id, c.name AS customer, c.email,
                       a.name AS airline, f.departure, f.arrival,
                       f.departure_time, b.seats, b.total_price, b.status, b.booked_at
                FROM bookings b
                JOIN customers c ON b.customer_id = c.customer_id
                JOIN flights f   ON b.flight_id   = f.flight_id
                JOIN airlines a  ON f.airline_id  = a.airline_id
                WHERE c.user_id = %s
                ORDER BY b.booked_at DESC
            """, (sess["user_id"],))
        self.send_json({"success": True, "data": cur.fetchall()})
        conn.close()

    def get_customers(self, sess):
        if not self.require_admin(sess): return
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.*, COUNT(b.booking_id) AS total_bookings
            FROM customers c LEFT JOIN bookings b ON c.customer_id = b.customer_id
            GROUP BY c.customer_id ORDER BY c.name
        """)
        self.send_json({"success": True, "data": cur.fetchall()})
        conn.close()

    def add_booking(self, body, sess):
        if not self.require_login(sess): return
        flight_id = body.get("flight_id")
        seats     = int(body.get("seats", 1))
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT available_seats, price FROM flights WHERE flight_id=%s", (flight_id,))
        row = cur.fetchone()
        if not row:
            conn.close(); return self.send_json({"success": False, "error": "Flight not found"})
        if row["available_seats"] < seats:
            conn.close(); return self.send_json({"success": False, "error": "Not enough seats"})
        cur.execute("SELECT customer_id FROM customers WHERE user_id=%s", (sess["user_id"],))
        cust = cur.fetchone()
        if not cust:
            cur2 = conn.cursor()
            cur2.execute("INSERT INTO customers (user_id,name,email) VALUES (%s,%s,%s)",
                         (sess["user_id"], sess["name"], sess["email"]))
            cid = cur2.lastrowid
        else:
            cid = cust["customer_id"]
        total = float(row["price"]) * seats
        cur2 = conn.cursor()
        cur2.execute("INSERT INTO bookings (flight_id,customer_id,seats,total_price) VALUES (%s,%s,%s,%s)",
                     (flight_id, cid, seats, total))
        cur2.execute("UPDATE flights SET available_seats=available_seats-%s WHERE flight_id=%s", (seats, flight_id))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": f"Booking confirmed! Total: ₹{total:,.0f}"})

    def cancel_booking(self, body, sess):
        if not self.require_login(sess): return
        bid = body.get("booking_id")
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        if sess["role"] == "admin":
            cur.execute("SELECT * FROM bookings WHERE booking_id=%s AND status='Confirmed'", (bid,))
        else:
            cur.execute("""SELECT b.* FROM bookings b
                JOIN customers c ON b.customer_id=c.customer_id
                WHERE b.booking_id=%s AND b.status='Confirmed' AND c.user_id=%s""",
                (bid, sess["user_id"]))
        b = cur.fetchone()
        if not b:
            conn.close(); return self.send_json({"success": False, "error": "Booking not found or not yours"})
        cur2 = conn.cursor()
        cur2.execute("UPDATE bookings SET status='Cancelled' WHERE booking_id=%s", (bid,))
        cur2.execute("UPDATE flights SET available_seats=available_seats+%s WHERE flight_id=%s",
                     (b["seats"], b["flight_id"]))
        conn.commit(); conn.close()
        self.send_json({"success": True, "message": "Booking cancelled successfully"})

    # ── STATS ─────────────────────────────────────────────────────
    def get_stats(self, sess):
        if not self.require_login(sess): return
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS v FROM flights")
        flights = cur.fetchone()["v"]
        cur.execute("SELECT COUNT(*) AS v FROM bookings WHERE status='Confirmed'")
        bookings = cur.fetchone()["v"]
        cur.execute("SELECT COUNT(*) AS v FROM customers")
        customers = cur.fetchone()["v"]
        cur.execute("SELECT COUNT(*) AS v FROM airlines")
        airlines = cur.fetchone()["v"]
        cur.execute("SELECT COALESCE(SUM(total_price),0) AS v FROM bookings WHERE status='Confirmed'")
        revenue = cur.fetchone()["v"]
        conn.close()
        self.send_json({"success": True, "data": {
            "flights": flights, "bookings": bookings,
            "customers": customers, "airlines": airlines,
            "revenue": float(revenue)
        }})

    # ── SQL RUNNER (admin only) ────────────────────────────────────
    def run_sql(self, body, sess):
        if not self.require_admin(sess): return
        query = body.get("query","").strip()
        if not query:
            return self.send_json({"success": False, "error": "Query is empty"})
        conn = get_conn(); cur = conn.cursor(dictionary=True)
        try:
            cur.execute(query)
            q_upper = query.upper().lstrip()
            if q_upper.startswith("SELECT") or q_upper.startswith("SHOW") or q_upper.startswith("DESCRIBE"):
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description] if cur.description else []
                self.send_json({"success": True, "columns": cols, "rows": rows, "count": len(rows)})
            else:
                conn.commit()
                self.send_json({"success": True, "message": f"Query OK. Rows affected: {cur.rowcount}"})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})
        finally:
            conn.close()

if __name__ == "__main__":
    import webbrowser
    print("=" * 52)
    print("  SkyBook Pro — Flight Booking System")
    print("  http://localhost:8080")
    print("  Admin:  admin@skybook.com / admin123")
    print("  User:   ravi@skybook.com  / user123")
    print("  Press Ctrl+C to stop")
    print("=" * 52)
    webbrowser.open("http://localhost:8080")
    HTTPServer(("", 8080), Handler).serve_forever()
