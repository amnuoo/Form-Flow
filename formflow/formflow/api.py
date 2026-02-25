import frappe
from .utils import generate_unique_id



@frappe.whitelist(allow_guest=True)
def get_form_config(form_name):

    form = frappe.get_doc("Form Configuration", {"form_name": form_name})

    if not form.is_active:
        frappe.throw("Form is inactive")

    if form.require_login and frappe.session.user == "Guest":
        frappe.throw("Login required to access this form")

    meta = frappe.get_meta(form.target_doctype)

    fields = []

    for f in form.form_fields:
        df = meta.get_field(f.fieldname)
        if not df:
            continue

        field_data = {
            "fieldname": f.fieldname,
            "label": f.label_override or df.label,
            "required": f.required,
            "hidden": f.hidden,
            "read_only": f.read_only,
            "fieldtype": df.fieldtype
        }

        # Child table support
        if df.fieldtype == "Table":
            child_meta = frappe.get_meta(df.options)
            field_data["child_fields"] = [
                {
                    "fieldname": c.fieldname,
                    "label": c.label,
                    "fieldtype": c.fieldtype
                }
                for c in child_meta.fields
                if c.fieldtype not in ["Section Break", "Column Break"]
            ]

        fields.append(field_data)

    return {
        "form_name": form.form_name,
        "form_fields": fields
    }



@frappe.whitelist(allow_guest=True)
def submit_form(form_name, data, unique_id=None):

    data = frappe.parse_json(data)
    form = frappe.get_doc("Form Configuration", {"form_name": form_name})

    if not form.is_active:
        frappe.throw("Form is inactive")

    if form.require_login and frappe.session.user == "Guest":
        frappe.throw("Login required")

    allowed_fields = [f.fieldname for f in form.form_fields if not f.hidden]
    cleaned_data = {k: v for k, v in data.items() if k in allowed_fields}

    for field in form.form_fields:
        if field.required and not cleaned_data.get(field.fieldname):
            frappe.throw(f"{field.fieldname} is mandatory")

  
    if not unique_id:

        if not form.allow_create:
            frappe.throw("creation not allowed")

        doc = frappe.new_doc(form.target_doctype)
        doc.update(cleaned_data)

        new_id = generate_unique_id(
            form.target_doctype,
            form.unique_id_field
        )

        doc.set(form.unique_id_field, new_id)
        doc.insert(ignore_permissions=True)


    else:

        if not form.allow_update:
            frappe.throw("Form update is not allowed")

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

    return {"unique_id": new_id}