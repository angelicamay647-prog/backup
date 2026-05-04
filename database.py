"""
DormNorm — Database Layer
All DB modules for the dormitory management system.
Includes: Admin, Renter, Room, Assignment, Payment,
          Maintenance, Utility, Visitor, Facility, Application
"""

import hashlib
import mysql.connector
from mysql.connector import Error


# ─────────────────────────────────────────────────────────────
#  BASE ENGINE
# ─────────────────────────────────────────────────────────────
class DatabaseEngine:
    def __init__(self):
        self.host     = "localhost"
        self.user     = "root"
        self.password = ""
        self.database = "dormitory_db"

    def connect(self):
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                connection_timeout=5,
            )
            return conn
        except Error as e:
            print(f"[DB Connection Error] {e}")
            return None

    @staticmethod
    def _hash(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    @staticmethod
    def _is_hashed(pw: str) -> bool:
        return len(pw) == 64 and all(c in "0123456789abcdef" for c in pw.lower())


# ─────────────────────────────────────────────────────────────
#  ADMIN / STAFF MODULE
# ─────────────────────────────────────────────────────────────
class AdminModule(DatabaseEngine):

    def validate_login(self, username: str, password: str):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            hashed = self._hash(password)
            cur.execute(
                "SELECT * FROM admins WHERE username=%s AND password=%s",
                (username, hashed),
            )
            return cur.fetchone()
        except Exception as e:
            print(f"[AdminModule.validate_login] {e}")
        finally:
            conn.close()
        return None

    def log_login(self, admin_id, full_name, role):
        try:
            self.add_log(admin_id, "LOGIN", f"{full_name} logged in.", actor_role=role)
        except Exception as e:
            print(f"[AdminModule.log_login] {e}")

    def get_all_admins(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT admin_id, username, full_name, role, created_at, last_login "
                "FROM admins ORDER BY admin_id"
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[AdminModule.get_all_admins] {e}")
        finally:
            conn.close()
        return []

    def hash_existing_admin_passwords(self):
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT admin_id, password FROM admins")
            rows = cur.fetchall()
            count = 0
            for row in rows:
                raw = row.get("password") or ""
                if not raw or self._is_hashed(raw):
                    continue
                cur.execute(
                    "UPDATE admins SET password=%s WHERE admin_id=%s",
                    (self._hash(raw), row["admin_id"]),
                )
                count += 1
            conn.commit()
            return count
        except Exception as e:
            print(f"[AdminModule.hash_existing_admin_passwords] {e}")
        finally:
            conn.close()
        return 0

    def add_admin(self, username, password, full_name, role="Admin"):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO admins (username, password, full_name, role) VALUES (%s,%s,%s,%s)",
                (username, self._hash(password), full_name, role),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[AdminModule.add_admin] {e}")
        finally:
            conn.close()
        return False

    def update_admin(self, admin_id, username, full_name, role, password=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            if password:
                cur.execute(
                    "UPDATE admins SET username=%s, full_name=%s, role=%s, password=%s WHERE admin_id=%s",
                    (username, full_name, role, self._hash(password), admin_id),
                )
            else:
                cur.execute(
                    "UPDATE admins SET username=%s, full_name=%s, role=%s WHERE admin_id=%s",
                    (username, full_name, role, admin_id),
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"[AdminModule.update_admin] {e}")
        finally:
            conn.close()
        return False

    def delete_admin(self, admin_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM admins WHERE admin_id=%s", (admin_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[AdminModule.delete_admin] {e}")
        finally:
            conn.close()
        return False

    def add_log(self, admin_id, action_type, action_text, actor_role="Admin"):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO activity_logs (admin_id, action_type, action_text, actor_role) "
                "VALUES (%s,%s,%s,%s)",
                (admin_id, action_type, action_text, actor_role),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[AdminModule.add_log] {e}")
        finally:
            conn.close()
        return False

    def get_activity_logs(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT l.log_id,
                          COALESCE(a.full_name,
                                   CONCAT(r.first_name,' ',r.last_name),
                                   'System') AS admin_name,
                          l.action_type, l.action_text,
                          l.actor_role,  l.log_timestamp
                   FROM activity_logs l
                   LEFT JOIN admins  a ON l.admin_id  = a.admin_id
                   LEFT JOIN renters r ON l.renter_id = r.renter_id
                   ORDER BY l.log_timestamp DESC
                   LIMIT 200"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[AdminModule.get_activity_logs] {e}")
        finally:
            conn.close()
        return []


# ─────────────────────────────────────────────────────────────
#  RENTER MODULE
# ─────────────────────────────────────────────────────────────
class RenterModule(DatabaseEngine):

    def hash_existing_renter_passwords(self):
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT renter_id, password FROM renter_accounts")
            rows = cur.fetchall()
            count = 0
            for row in rows:
                raw = row.get("password") or ""
                if not raw or self._is_hashed(raw):
                    continue
                cur.execute(
                    "UPDATE renter_accounts SET password=%s WHERE renter_id=%s",
                    (self._hash(raw), row["renter_id"]),
                )
                count += 1
            conn.commit()
            return count
        except Exception as e:
            print(f"[RenterModule.hash_existing_renter_passwords] {e}")
        finally:
            conn.close()
        return 0

    def get_all_renters(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM renters ORDER BY last_name, first_name")
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.get_all_renters] {e}")
        finally:
            conn.close()
        return []

    def get_renter_by_id(self, renter_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM renters WHERE renter_id=%s", (renter_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[RenterModule.get_renter_by_id] {e}")
        finally:
            conn.close()
        return None

    def add_renter(
        self,
        first_name, middle_name, last_name, occupation_type,
        institution_employer, gender, contact_number, email,
        id_type, id_number, address,
        emergency_contact_name, emergency_contact_number,
        renter_status="Active",
    ):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO renters (
                    first_name, middle_name, last_name, occupation_type,
                    institution_employer, gender, contact_number, email,
                    id_type, id_number, address,
                    emergency_contact_name, emergency_contact_number, renter_status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    first_name, middle_name, last_name, occupation_type,
                    institution_employer, gender, contact_number, email,
                    id_type, id_number, address,
                    emergency_contact_name, emergency_contact_number, renter_status,
                ),
            )
            renter_id = cur.lastrowid
            # FIX: The DB trigger trg_renter_account_on_insert already creates the
            # renter_accounts row with the hashed default password.
            # We use INSERT IGNORE as a safety net only — it won't crash if trigger ran.
            username   = f"renter{renter_id}"
            default_pw = self._hash("dorm123")
            cur.execute(
                "INSERT IGNORE INTO renter_accounts (renter_id, username, password) VALUES (%s,%s,%s)",
                (renter_id, username, default_pw),
            )
            conn.commit()
            return renter_id
        except Exception as e:
            conn.rollback()
            print(f"[RenterModule.add_renter] {e}")
        finally:
            conn.close()
        return None

    def update_renter(self, renter_id, **fields):
        if not fields:
            return False
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            set_clause = ", ".join(f"{k}=%s" for k in fields)
            values = list(fields.values()) + [renter_id]
            cur.execute(f"UPDATE renters SET {set_clause} WHERE renter_id=%s", values)
            conn.commit()
            return True
        except Exception as e:
            print(f"[RenterModule.update_renter] {e}")
        finally:
            conn.close()
        return False

    def delete_renter(self, renter_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM renters WHERE renter_id=%s", (renter_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[RenterModule.delete_renter] {e}")
        finally:
            conn.close()
        return False

    def get_stats(self):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT COUNT(*) AS total FROM assignments WHERE status='Active'")
            total_active = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM rooms WHERE status='Available'")
            vacant_rooms = cur.fetchone()["total"]
            return {"renters": total_active, "vacant": vacant_rooms}
        except Exception as e:
            print(f"[RenterModule.get_stats] {e}")
        finally:
            conn.close()
        return None

    def search_renters(self, keyword):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            like = f"%{keyword}%"
            cur.execute(
                """SELECT * FROM renters
                   WHERE first_name LIKE %s OR last_name LIKE %s
                      OR contact_number LIKE %s OR email LIKE %s
                   ORDER BY last_name""",
                (like, like, like, like),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.search_renters] {e}")
        finally:
            conn.close()
        return []

    def validate_renter_login(self, username: str, password: str):
        """Returns renter info dict if login is valid, else None."""
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            hashed = self._hash(password)
            cur.execute(
                """SELECT ra.account_id, ra.renter_id, ra.username,
                          r.first_name, r.last_name, r.renter_status
                   FROM renter_accounts ra
                   JOIN renters r ON ra.renter_id = r.renter_id
                   WHERE ra.username=%s AND ra.password=%s
                     AND ra.account_status='Active'
                     AND r.renter_status='Active'""",
                (username, hashed),
            )
            return cur.fetchone()
        except Exception as e:
            print(f"[RenterModule.validate_renter_login] {e}")
        finally:
            conn.close()
        return None

    def get_renter_payments(self, renter_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT p.*, CONCAT(r.first_name,' ',r.last_name) AS renter_name
                   FROM payments p
                   JOIN renters r ON p.renter_id = r.renter_id
                   WHERE p.renter_id=%s ORDER BY p.payment_date DESC""",
                (renter_id,),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.get_renter_payments] {e}")
        finally:
            conn.close()
        return []

    def get_renter_maintenance(self, renter_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT mr.*, rm.room_number,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name
                   FROM maintenance_requests mr
                   JOIN rooms rm ON mr.room_id = rm.room_id
                   JOIN renters r ON mr.renter_id = r.renter_id
                   WHERE mr.renter_id=%s ORDER BY mr.request_date DESC""",
                (renter_id,),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.get_renter_maintenance] {e}")
        finally:
            conn.close()
        return []

    def get_renter_assignment(self, renter_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT a.*, rm.room_number, rm.floor_level, rm.monthly_rate, rm.description
                   FROM assignments a
                   JOIN rooms rm ON a.room_id = rm.room_id
                   WHERE a.renter_id=%s AND a.status='Active'
                   LIMIT 1""",
                (renter_id,),
            )
            return cur.fetchone()
        except Exception as e:
            print(f"[RenterModule.get_renter_assignment] {e}")
        finally:
            conn.close()
        return None


# ─────────────────────────────────────────────────────────────
#  ROOM MODULE
# ─────────────────────────────────────────────────────────────
class RoomModule(DatabaseEngine):

    def get_all_rooms(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM rooms ORDER BY room_number")
            return cur.fetchall()
        except Exception as e:
            print(f"[RoomModule.get_all_rooms] {e}")
        finally:
            conn.close()
        return []

    def get_room_by_id(self, room_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[RoomModule.get_room_by_id] {e}")
        finally:
            conn.close()
        return None

    def add_room(self, room_number, floor_level, monthly_rate, capacity,
                 status="Available", description="", photo_path=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO rooms
                       (room_number, floor_level, monthly_rate, capacity, status, description, photo_path)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (room_number, floor_level, monthly_rate, capacity, status, description, photo_path),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.add_room] {e}")
        finally:
            conn.close()
        return False

    def update_room(self, room_id, room_number, floor_level, monthly_rate,
                    capacity, status, description, photo_path=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE rooms
                   SET room_number=%s, floor_level=%s, monthly_rate=%s,
                       capacity=%s, status=%s, description=%s, photo_path=%s
                   WHERE room_id=%s""",
                (room_number, floor_level, monthly_rate, capacity,
                 status, description, photo_path, room_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.update_room] {e}")
        finally:
            conn.close()
        return False

    def update_room_photo(self, room_id, photo_path):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("UPDATE rooms SET photo_path=%s WHERE room_id=%s", (photo_path, room_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.update_room_photo] {e}")
        finally:
            conn.close()
        return False

    def delete_room(self, room_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM rooms WHERE room_id=%s", (room_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.delete_room] {e}")
        finally:
            conn.close()
        return False

    def get_amenities(self, room_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM room_amenities WHERE room_id=%s", (room_id,))
            return cur.fetchall()
        except Exception as e:
            print(f"[RoomModule.get_amenities] {e}")
        finally:
            conn.close()
        return []

    def add_amenity(self, room_id, amenity_name, quantity=1, item_condition="Good"):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO room_amenities (room_id, amenity_name, quantity, item_condition) VALUES (%s,%s,%s,%s)",
                (room_id, amenity_name, quantity, item_condition),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.add_amenity] {e}")
        finally:
            conn.close()
        return False

    def delete_amenity(self, amenity_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM room_amenities WHERE amenity_id=%s", (amenity_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.delete_amenity] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  ASSIGNMENT MODULE
# ─────────────────────────────────────────────────────────────
class AssignmentModule(DatabaseEngine):

    def get_all_assignments(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT a.assignment_id,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name,
                          rm.room_number, a.bed_assignment,
                          a.check_in_date, a.check_out_date,
                          a.status, a.agreed_rate, a.security_deposit,
                          a.contract_term, a.notes
                   FROM assignments a
                   JOIN renters r  ON a.renter_id = r.renter_id
                   JOIN rooms   rm ON a.room_id   = rm.room_id
                   ORDER BY a.assignment_id"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[AssignmentModule.get_all_assignments] {e}")
        finally:
            conn.close()
        return []


# ─────────────────────────────────────────────────────────────
#  PAYMENT MODULE
# ─────────────────────────────────────────────────────────────
class PaymentModule(DatabaseEngine):

    def get_all_payments(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT p.*,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name
                   FROM payments p
                   JOIN renters r ON p.renter_id = r.renter_id
                   ORDER BY p.payment_date DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[PaymentModule.get_all_payments] {e}")
        finally:
            conn.close()
        return []

    def add_payment(
        self, invoice_number, renter_id, amount, balance_amount,
        payment_method, billing_month, payment_date, status,
        reference_number=None, remarks=None, processed_by=None,
    ):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO payments (
                    invoice_number, renter_id, amount, balance_amount,
                    payment_method, billing_month, payment_date, status,
                    reference_number, remarks, processed_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    invoice_number, renter_id, amount, balance_amount,
                    payment_method, billing_month, payment_date, status,
                    reference_number, remarks, processed_by,
                ),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[PaymentModule.add_payment] {e}")
        finally:
            conn.close()
        return False

    def update_payment_status(self, payment_id, status):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("UPDATE payments SET status=%s WHERE payment_id=%s", (status, payment_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[PaymentModule.update_payment_status] {e}")
        finally:
            conn.close()
        return False

    def delete_payment(self, payment_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM payments WHERE payment_id=%s", (payment_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[PaymentModule.delete_payment] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  MAINTENANCE MODULE
# ─────────────────────────────────────────────────────────────
class MaintenanceModule(DatabaseEngine):

    def get_all_requests(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT mr.request_id, rm.room_number,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name,
                          mr.description, mr.priority, mr.status,
                          mr.request_date, mr.resolved_date, mr.resolution_notes
                   FROM maintenance_requests mr
                   JOIN rooms   rm ON mr.room_id   = rm.room_id
                   JOIN renters r  ON mr.renter_id = r.renter_id
                   ORDER BY
                       FIELD(mr.priority,'High','Medium','Low'),
                       mr.request_date DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[MaintenanceModule.get_all_requests] {e}")
        finally:
            conn.close()
        return []

    def add_request(self, room_id, renter_id, description, priority="Medium"):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO maintenance_requests (room_id, renter_id, description, priority) "
                "VALUES (%s,%s,%s,%s)",
                (room_id, renter_id, description, priority),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[MaintenanceModule.add_request] {e}")
        finally:
            conn.close()
        return False

    def update_status(self, request_id, status, resolution_notes="", resolved_date=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE maintenance_requests
                   SET status=%s, resolution_notes=%s, resolved_date=%s
                   WHERE request_id=%s""",
                (status, resolution_notes, resolved_date, request_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[MaintenanceModule.update_status] {e}")
        finally:
            conn.close()
        return False

    def delete_request(self, request_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM maintenance_requests WHERE request_id=%s", (request_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[MaintenanceModule.delete_request] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  UTILITY BILLS MODULE
# ─────────────────────────────────────────────────────────────
class UtilityModule(DatabaseEngine):

    def get_all_bills(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT ub.*, rm.room_number
                   FROM utility_bills ub
                   JOIN rooms rm ON ub.room_id = rm.room_id
                   ORDER BY ub.billing_date DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[UtilityModule.get_all_bills] {e}")
        finally:
            conn.close()
        return []

    def add_bill(self, room_id, bill_type, previous_reading, current_reading,
                 consumption, amount, amount_per_person,
                 billing_month, billing_date, due_date):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO utility_bills
                    (room_id, bill_type, previous_reading, current_reading,
                     consumption, amount, amount_per_person,
                     billing_month, billing_date, due_date)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (room_id, bill_type, previous_reading, current_reading,
                 consumption, amount, amount_per_person,
                 billing_month, billing_date, due_date),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[UtilityModule.add_bill] {e}")
        finally:
            conn.close()
        return False

    def mark_paid(self, bill_id, payment_date, reference_no=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE utility_bills SET status='Paid', payment_date=%s, reference_no=%s WHERE bill_id=%s",
                (payment_date, reference_no, bill_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[UtilityModule.mark_paid] {e}")
        finally:
            conn.close()
        return False

    def delete_bill(self, bill_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM utility_bills WHERE bill_id=%s", (bill_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[UtilityModule.delete_bill] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  VISITOR MODULE
# ─────────────────────────────────────────────────────────────
class VisitorModule(DatabaseEngine):

    def get_all_visitors(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT vl.visitor_id, vl.visitor_name, vl.relationship,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name,
                          vl.time_in, vl.time_out
                   FROM visitor_logs vl
                   JOIN renters r ON vl.renter_id = r.renter_id
                   ORDER BY vl.time_in DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[VisitorModule.get_all_visitors] {e}")
        finally:
            conn.close()
        return []

    def log_visitor_in(self, renter_id, visitor_name, relationship):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO visitor_logs (renter_id, visitor_name, relationship) VALUES (%s,%s,%s)",
                (renter_id, visitor_name, relationship),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[VisitorModule.log_visitor_in] {e}")
        finally:
            conn.close()
        return False

    def log_visitor_out(self, visitor_id, time_out):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE visitor_logs SET time_out=%s WHERE visitor_id=%s", (time_out, visitor_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[VisitorModule.log_visitor_out] {e}")
        finally:
            conn.close()
        return False

    def delete_visitor_log(self, visitor_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM visitor_logs WHERE visitor_id=%s", (visitor_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[VisitorModule.delete_visitor_log] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  FACILITY MODULE
# ─────────────────────────────────────────────────────────────
class FacilityModule(DatabaseEngine):

    def get_all_facilities(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM facility_overview ORDER BY floor_level, facility_type")
            return cur.fetchall()
        except Exception as e:
            print(f"[FacilityModule.get_all_facilities] {e}")
        finally:
            conn.close()
        return []

    def add_facility(self, floor_level, facility_type, count):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO facility_overview (floor_level, facility_type, count) VALUES (%s,%s,%s)",
                (floor_level, facility_type, count),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[FacilityModule.add_facility] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  APPLICATION MODULE  ← NEW: rental applications from public
# ─────────────────────────────────────────────────────────────
class ApplicationModule(DatabaseEngine):
    """
    Handles the rental_applications table.
    Public applicants submit here; admin reviews and approves.
    Approval creates a renters row + renter_accounts login.
    """

    def setup_table(self):
        """Create rental_applications table if it doesn't exist yet."""
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """CREATE TABLE IF NOT EXISTS rental_applications (
                    application_id   INT AUTO_INCREMENT PRIMARY KEY,
                    first_name       VARCHAR(100) NOT NULL,
                    last_name        VARCHAR(100) NOT NULL,
                    gender           VARCHAR(20)  DEFAULT 'Other',
                    occupation_type  VARCHAR(50)  DEFAULT 'Student',
                    institution      VARCHAR(200),
                    contact_number   VARCHAR(30),
                    email            VARCHAR(150),
                    address          TEXT,
                    emergency_name   VARCHAR(150),
                    emergency_number VARCHAR(30),
                    preferred_room   VARCHAR(100),
                    message          TEXT,
                    status           VARCHAR(20)  DEFAULT 'Pending',
                    submitted_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at      DATETIME,
                    reviewed_by      INT,
                    rejection_reason TEXT
                )"""
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ApplicationModule.setup_table] {e}")
        finally:
            conn.close()
        return False

    def submit_application(
        self, first_name, last_name, gender, occupation_type,
        institution, contact_number, email, address,
        emergency_name, emergency_number, preferred_room, message,
    ):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO rental_applications (
                    first_name, last_name, gender, occupation_type,
                    institution, contact_number, email, address,
                    emergency_name, emergency_number, preferred_room, message
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    first_name, last_name, gender, occupation_type,
                    institution, contact_number, email, address,
                    emergency_name, emergency_number, preferred_room, message,
                ),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ApplicationModule.submit_application] {e}")
        finally:
            conn.close()
        return False

    def get_all_applications(self, status_filter=None):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            if status_filter:
                cur.execute(
                    "SELECT * FROM rental_applications WHERE status=%s ORDER BY submitted_at DESC",
                    (status_filter,),
                )
            else:
                cur.execute("SELECT * FROM rental_applications ORDER BY submitted_at DESC")
            return cur.fetchall()
        except Exception as e:
            print(f"[ApplicationModule.get_all_applications] {e}")
        finally:
            conn.close()
        return []

    def get_pending_count(self):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM rental_applications WHERE status='Pending'"
            )
            row = cur.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"[ApplicationModule.get_pending_count] {e}")
        finally:
            conn.close()
        return 0

    def approve_application(self, application_id, admin_id):
        """
        Approve an application:
        1. Fetch application data
        2. Insert into renters with status=Active
        3. Create renter_accounts login (username = first+last lower, pw = dorm123)
        4. Mark application as Approved
        Returns (True, username, password) or (False, error_message, '')
        """
        conn = self.connect()
        if not conn:
            return False, "No DB connection", ""
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM rental_applications WHERE application_id=%s", (application_id,)
            )
            app = cur.fetchone()
            if not app:
                return False, "Application not found", ""

            # Build a unique username
            base_username = (
                (app["first_name"][:3] + app["last_name"][:4]).lower().replace(" ", "")
            )
            # Check for duplicates
            cur2 = conn.cursor()
            cur2.execute(
                "SELECT COUNT(*) FROM renter_accounts WHERE username LIKE %s",
                (f"{base_username}%",),
            )
            count = cur2.fetchone()[0]
            username = base_username if count == 0 else f"{base_username}{count + 1}"
            default_pw = "dorm123"

            # Insert renter
            cur.execute(
                """INSERT INTO renters (
                    first_name, last_name, gender, occupation_type,
                    institution_employer, contact_number, email, address,
                    emergency_contact_name, emergency_contact_number,
                    renter_status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Active')""",
                (
                    app["first_name"], app["last_name"], app["gender"],
                    app["occupation_type"], app["institution"],
                    app["contact_number"], app["email"], app["address"],
                    app["emergency_name"], app["emergency_number"],
                ),
            )
            renter_id = cur.lastrowid

            # Create renter account
            cur.execute(
                "INSERT INTO renter_accounts (renter_id, username, password) VALUES (%s,%s,%s)",
                (renter_id, username, self._hash(default_pw)),
            )

            # Mark application approved
            cur.execute(
                """UPDATE rental_applications
                   SET status='Approved', reviewed_at=NOW(), reviewed_by=%s
                   WHERE application_id=%s""",
                (admin_id, application_id),
            )
            conn.commit()
            return True, username, default_pw
        except Exception as e:
            conn.rollback()
            print(f"[ApplicationModule.approve_application] {e}")
            return False, str(e), ""
        finally:
            conn.close()

    def reject_application(self, application_id, admin_id, reason=""):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE rental_applications
                   SET status='Rejected', reviewed_at=NOW(),
                       reviewed_by=%s, rejection_reason=%s
                   WHERE application_id=%s""",
                (admin_id, reason, application_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ApplicationModule.reject_application] {e}")
        finally:
            conn.close()
        return False

    def delete_application(self, application_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM rental_applications WHERE application_id=%s", (application_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ApplicationModule.delete_application] {e}")
        finally:
            conn.close()
        return False




# ─────────────────────────────────────────────────────────────
#  PAYROLL MODULE  (staff salary tracking)
# ─────────────────────────────────────────────────────────────
class PayrollModule(DatabaseEngine):

    def setup_table(self):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS `staff_payroll` (
                    `payroll_id`     INT AUTO_INCREMENT PRIMARY KEY,
                    `admin_id`       INT NOT NULL,
                    `period_month`   VARCHAR(20) NOT NULL,
                    `basic_salary`   DECIMAL(10,2) DEFAULT 0.00,
                    `allowances`     DECIMAL(10,2) DEFAULT 0.00,
                    `deductions`     DECIMAL(10,2) DEFAULT 0.00,
                    `net_pay`        DECIMAL(10,2) DEFAULT 0.00,
                    `payment_date`   DATE DEFAULT NULL,
                    `payment_method` VARCHAR(30) DEFAULT 'Cash',
                    `notes`          TEXT DEFAULT NULL,
                    `created_at`     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    KEY `admin_id` (`admin_id`),
                    CONSTRAINT `payroll_ibfk_1`
                        FOREIGN KEY (`admin_id`) REFERENCES `admins` (`admin_id`) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"[PayrollModule.setup_table] {e}")
        finally:
            conn.close()
        return False

    def get_payroll_for_admin(self, admin_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM staff_payroll WHERE admin_id=%s ORDER BY created_at DESC",
                (admin_id,)
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[PayrollModule.get_payroll_for_admin] {e}")
        finally:
            conn.close()
        return []

    def get_all_payroll(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT sp.*, a.full_name, a.role
                FROM staff_payroll sp
                JOIN admins a ON sp.admin_id = a.admin_id
                ORDER BY sp.created_at DESC
            """)
            return cur.fetchall()
        except Exception as e:
            print(f"[PayrollModule.get_all_payroll] {e}")
        finally:
            conn.close()
        return []

    def add_payroll(self, admin_id, period_month, basic_salary,
                    allowances=0, deductions=0, payment_date=None,
                    payment_method="Cash", notes=""):
        conn = self.connect()
        if not conn:
            return False
        try:
            net_pay = float(basic_salary) + float(allowances) - float(deductions)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO staff_payroll
                    (admin_id, period_month, basic_salary, allowances, deductions,
                     net_pay, payment_date, payment_method, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (admin_id, period_month, basic_salary, allowances, deductions,
                  net_pay, payment_date, payment_method, notes))
            conn.commit()
            return True
        except Exception as e:
            print(f"[PayrollModule.add_payroll] {e}")
        finally:
            conn.close()
        return False

    def delete_payroll(self, payroll_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM staff_payroll WHERE payroll_id=%s", (payroll_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[PayrollModule.delete_payroll] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  PROFILE MODULE  (edit profile for all roles)
# ─────────────────────────────────────────────────────────────
class ProfileModule(DatabaseEngine):

    def get_admin_profile(self, admin_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM admins WHERE admin_id=%s", (admin_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[ProfileModule.get_admin_profile] {e}")
        finally:
            conn.close()
        return None

    def update_admin_profile(self, admin_id, full_name=None, email=None,
                             contact_number=None, profile_pic_path=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            fields = {}
            if full_name is not None:
                fields['full_name'] = full_name
            if email is not None:
                fields['email'] = email
            if contact_number is not None:
                fields['contact_number'] = contact_number
            if profile_pic_path is not None:
                fields['profile_pic_path'] = profile_pic_path
            if not fields:
                return True
            set_clause = ", ".join(f"`{k}`=%s" for k in fields)
            values = list(fields.values()) + [admin_id]
            cur.execute(f"UPDATE admins SET {set_clause} WHERE admin_id=%s", values)
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.update_admin_profile] {e}")
        finally:
            conn.close()
        return False

    def change_admin_password(self, admin_id, old_password, new_password):
        """Returns True on success, 'wrong_password' if old pw is wrong."""
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            old_hashed = self._hash(old_password)
            cur.execute("SELECT admin_id FROM admins WHERE admin_id=%s AND password=%s",
                        (admin_id, old_hashed))
            if not cur.fetchone():
                return 'wrong_password'
            cur.execute("UPDATE admins SET password=%s WHERE admin_id=%s",
                        (self._hash(new_password), admin_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.change_admin_password] {e}")
        finally:
            conn.close()
        return False

    def get_renter_profile(self, renter_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT r.*, ra.username, ra.account_status, ra.last_login
                FROM renters r
                LEFT JOIN renter_accounts ra ON r.renter_id = ra.renter_id
                WHERE r.renter_id=%s
            """, (renter_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[ProfileModule.get_renter_profile] {e}")
        finally:
            conn.close()
        return None

    def update_renter_profile(self, renter_id, contact_number=None,
                               email=None, address=None,
                               emergency_contact_name=None,
                               emergency_contact_number=None,
                               profile_pic_path=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            # Build only the fields that are explicitly passed (not None means intentional update)
            fields = {}
            if contact_number is not None:
                fields['contact_number'] = contact_number
            if email is not None:
                fields['email'] = email
            if address is not None:
                fields['address'] = address
            if emergency_contact_name is not None:
                fields['emergency_contact_name'] = emergency_contact_name
            if emergency_contact_number is not None:
                fields['emergency_contact_number'] = emergency_contact_number
            if profile_pic_path is not None:
                fields['profile_pic_path'] = profile_pic_path
            if not fields:
                return True  # nothing to update
            set_clause = ", ".join(f"`{k}`=%s" for k in fields)
            values = list(fields.values()) + [renter_id]
            cur.execute(f"UPDATE renters SET {set_clause} WHERE renter_id=%s", values)
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.update_renter_profile] {e}")
        finally:
            conn.close()
        return False

    def change_renter_password(self, renter_id, old_password, new_password):
        """Returns True on success, 'wrong_password' if old pw is wrong."""
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            old_hashed = self._hash(old_password)
            cur.execute(
                "SELECT account_id FROM renter_accounts WHERE renter_id=%s AND password=%s",
                (renter_id, old_hashed)
            )
            if not cur.fetchone():
                return 'wrong_password'
            cur.execute(
                "UPDATE renter_accounts SET password=%s WHERE renter_id=%s",
                (self._hash(new_password), renter_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.change_renter_password] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  SELF-TEST
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("─── DormNorm DB Self-Test ───")

    # Run password migration to ensure all passwords are hashed
    admin_mod = AdminModule()
    hashed_a = admin_mod.hash_existing_admin_passwords()
    print(f"[MIGRATION] Admin passwords hashed: {hashed_a}")

    renter_mod = RenterModule()
    hashed_r = renter_mod.hash_existing_renter_passwords()
    print(f"[MIGRATION] Renter passwords hashed: {hashed_r}")

    # Test admin login
    result = admin_mod.validate_login("gel_admin", "gel123")
    if result:
        print(f"[OK] Admin login works — {result['full_name']} ({result['role']})")
    else:
        print("[FAIL] Admin login failed. Check username/password.")

    # Test renter login
    renter_result = renter_mod.validate_renter_login("renter1", "dorm123")
    if renter_result:
        print(f"[OK] Renter login works — {renter_result['first_name']} {renter_result['last_name']}")
    else:
        print("[FAIL] Renter login failed. Password hash mismatch or DB not updated.")

    # Room count
    room_mod = RoomModule()
    rooms = room_mod.get_all_rooms()
    print(f"[OK] {len(rooms)} rooms found.")

    # Application table
    app_mod = ApplicationModule()
    app_mod.setup_table()
    pending = app_mod.get_pending_count()
    print(f"[OK] {pending} pending rental application(s).")

    # Payroll table
    pay_mod = PayrollModule()
    pay_mod.setup_table()
    print("[OK] staff_payroll table ready.")

    print("─── Self-test complete ───")