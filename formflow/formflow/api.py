import frappe
from .utils import generate_unique_id


@frappe.whitelist(allow_guest=True)
def get_form_config(form_name):

    form = frappe.get_doc(
        "Form Configuration",
        {"form_name": form_name}
    )

    if not form.is_active:
        frappe.throw("Form is inactive")

    if form.require_login and frappe.session.user == "Guest":
        frappe.throw("Login required to access this form")

    return form

@frappe.whitelist(allow_guest=True)
def submit_form(form_name, data, unique_id=None):

    data = frappe.parse_json(data)

    form = frappe.get_doc(
        "Form Configuration",
        {"form_name": form_name}
    )

    if not form.is_active:
        frappe.throw("Form inactive")

    if form.require_login and frappe.session.user == "Guest":
        frappe.throw("Login required")

    if not frappe.db.exists("DocType", form.target_doctype):
        frappe.throw("Target DocType does not exist")
