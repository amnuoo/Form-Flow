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

    allowed_fields = [
        f.fieldname for f in form.form_fields if not f.hidden
    ]

    cleaned_data = {}
    for key in data:
        if key in allowed_fields:
            cleaned_data[key] = data[key]

    for field in form.form_fields:
        if field.required and not cleaned_data.get(field.fieldname):
            frappe.throw(f"{field.fieldname} is mandatory")

    if not unique_id:

        if not form.allow_create:
            frappe.throw("Create not allowed")

        doc = frappe.new_doc(form.target_doctype)
        doc.update(cleaned_data)

        new_id = generate_unique_id(
            form.target_doctype,
            form.unique_id_field
        )

        doc.set(form.unique_id_field, new_id)
        doc.insert(ignore_permissions=True)

        action = "Create"

    else:

        if not form.allow_update:
            frappe.throw("Update not allowed")

        doc_name = frappe.db.get_value(
            form.target_doctype,
            {form.unique_id_field: unique_id}
        )

        if not doc_name:
            frappe.throw("Invalid Reference ID")

        doc = frappe.get_doc(form.target_doctype, doc_name)
        doc.update(cleaned_data)
        doc.save(ignore_permissions=True)

        new_id = unique_id
        action = "Update"

    log_submission(form.name, new_id, action)

    return {
        "message": "Success",
        "unique_id": new_id
    }


@frappe.whitelist(allow_guest=True)
def get_doc_by_unique_id(form_name, unique_id):

    form = frappe.get_doc(
        "Form Configuration",
        {"form_name": form_name}
    )

    if not form.allow_update:
        frappe.throw("Update not allowed")

    doc_name = frappe.db.get_value(
        form.target_doctype,
        {form.unique_id_field: unique_id}
    )

    if not doc_name:
        frappe.throw("Invalid Reference ID")

    doc = frappe.get_doc(form.target_doctype, doc_name)

    return doc


def log_submission(form_name, unique_id, action):

    frappe.get_doc({
        "doctype": "Form Submission Log",
        "form": form_name,
        "unique_id": unique_id,
        "ip_address": frappe.local.request_ip,
        "action": action,
        "timestamp": frappe.utils.now()
    }).insert(ignore_permissions=True)
