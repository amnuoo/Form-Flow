import frappe
import random
import string

def generate_unique_id(doctype, fieldname, prefix="REF"):
    while True:
        random_part = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
        unique_id = f"{prefix}-{random_part}"

        if not frappe.db.exists(doctype, {fieldname: unique_id}):
            return unique_id
