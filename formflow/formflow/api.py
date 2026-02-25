import frappe
from .utils import generate_unique_id


@frappe.whitelist(allow_guest=True)
def get_form_config(form_name):

    form = frappe.get_doc(
        "Form Configuration",
        {"form_name": form_name}
    )

    if not form.is_active:
        frappe.local.response.http_status_code = 403
        frappe.response["message"] = "Form is inactive"
        return

    if form.require_login and frappe.session.user == "Guest":
        frappe.local.response.http_status_code = 401
        frappe.response["message"] = "Login required to access this form"
        return

    return form


@frappe.whitelist(allow_guest=True)
def submit_form(form_name, data, unique_id=None):

    data = frappe.parse_json(data)

    form = frappe.get_doc(
        "Form Configuration",
        {"form_name": form_name}
    )

    # Check active
    if not form.is_active:
        frappe.local.response.http_status_code = 403
        frappe.response["message"] = "Form is inactive"
        return

    # Check login
    if form.require_login and frappe.session.user == "Guest":
        frappe.local.response.http_status_code = 401
        frappe.response["message"] = "Login required"
        return

    # Check target doctype exists
    if not frappe.db.exists("DocType", form.target_doctype):
        frappe.local.response.http_status_code = 404
        frappe.response["message"] = "Target DocType does not exist"
        return

    # Allowed fields only
    allowed_fields = [
        f.fieldname for f in form.form_fields if not f.hidden
    ]

    cleaned_data = {}
    for key in data:
        if key in allowed_fields:
            cleaned_data[key] = data[key]

    # Required field validation
    for field in form.form_fields:
        if field.required and not cleaned_data.get(field.fieldname):
            frappe.local.response.http_status_code = 400
            frappe.response["message"] = f"{field.fieldname} is mandatory"
            return

    if not unique_id:

        if not form.allow_create:
            frappe.local.response.http_status_code = 403
            frappe.response["message"] = "Creation not allowed"
            return

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
            frappe.local.response.http_status_code = 403
            frappe.response["message"] = "Updation not allowed"
            return

        doc_name = frappe.db.get_value(
            form.target_doctype,
            {form.unique_id_field: unique_id}
        )

        if not doc_name:
            frappe.local.response.http_status_code = 404
            frappe.response["message"] = "Invalid Reference ID"
            return

        doc = frappe.get_doc(form.target_doctype, doc_name)
        doc.update(cleaned_data)
        doc.save(ignore_permissions=True)

        new_id = unique_id
        action = "Update"

    # Log submission
    log_submission(form.name, new_id, action)

    return {
        "message": {
            "status": "Success",
            "unique_id": new_id
        }
    }


@frappe.whitelist(allow_guest=True)
def get_doc_by_unique_id(form_name, unique_id):

    form = frappe.get_doc(
        "Form Configuration",
        {"form_name": form_name}
    )

    if not form.allow_update:
        frappe.local.response.http_status_code = 403
        frappe.response["message"] = "Updation not allowed"
        return

    doc_name = frappe.db.get_value(
        form.target_doctype,
        {form.unique_id_field: unique_id}
    )

    if not doc_name:
        frappe.local.response.http_status_code = 404
        frappe.response["message"] = "Invalid Reference ID"
        return

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