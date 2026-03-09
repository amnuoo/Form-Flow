import frappe
from frappe.model.naming import make_autoname


def generate_reference_id(prefix):
    year = frappe.utils.now_datetime().year
    series = f"{prefix}-{year}-.#####"
    return make_autoname(series)


@frappe.whitelist(allow_guest=True)
def get_form_config(form_name):

    form = frappe.get_doc("Form Configuration", {"form_name": form_name})

    if not form.is_active:
        frappe.throw("Form is inactive")

    # LOGIN CHECK
    if form.require_login and frappe.session.user == "Guest":
        frappe.throw("Please login first")

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
def get_doc_by_unique_id(form_name, unique_id):

    form = frappe.get_doc("Form Configuration", {"form_name": form_name})

    if not form.is_active:
        frappe.throw("Form is inactive")

    if form.require_login and frappe.session.user == "Guest":
        frappe.throw("Please login first")

    if not frappe.db.exists(form.target_doctype, unique_id):
        frappe.throw("Invalid Reference ID")

    doc = frappe.get_doc(form.target_doctype, unique_id)

    allowed_fields = [f.fieldname for f in form.form_fields if not f.hidden]

    data = {}

    for field in allowed_fields:
        data[field] = doc.get(field)

    return data


@frappe.whitelist(allow_guest=True)
def submit_form(form_name, data, unique_id=None):

    data = frappe.parse_json(data)

    if unique_id in ("", None, "null", "None"):
        unique_id = None

    form = frappe.get_doc("Form Configuration", {"form_name": form_name})

    if not form.is_active:
        frappe.throw("Form is inactive")

    # LOGIN CHECK
    if form.require_login and frappe.session.user == "Guest":
        frappe.throw("Please login first")

    allowed_fields = [f.fieldname for f in form.form_fields if not f.hidden]

    cleaned_data = {k: v for k, v in data.items() if k in allowed_fields}

    for field in form.form_fields:
        if field.required and not cleaned_data.get(field.fieldname):
            frappe.throw(f"{field.label_override or field.fieldname} is mandatory")

    action_type = ""
    new_id = ""

    if unique_id is None:

        if not form.allow_create:
            frappe.throw("Creation is not allowed")

        doc = frappe.new_doc(form.target_doctype)

        meta = frappe.get_meta(form.target_doctype)

        for key, value in cleaned_data.items():

            df = meta.get_field(key)

            if df and df.fieldtype == "Table":

                for row in value:
                    doc.append(key, row)

            else:
                doc.set(key, value)

        prefix = form.reference_prefix or "REF"

        new_id = generate_reference_id(prefix)

        doc.name = new_id

        if hasattr(doc, "reference_id"):
            doc.reference_id = new_id

        doc.insert(ignore_permissions=True)

        action_type = "Create"

    else:

        if not form.allow_update:
            frappe.throw("Update is not allowed")

        if not frappe.db.exists(form.target_doctype, unique_id):
            frappe.throw("Invalid Reference ID")

        doc = frappe.get_doc(form.target_doctype, unique_id)

        meta = frappe.get_meta(form.target_doctype)

        for key, value in cleaned_data.items():

            df = meta.get_field(key)

            if df and df.fieldtype == "Table":

                doc.set(key, [])

                for row in value:
                    doc.append(key, row)

            else:
                doc.set(key, value)

        doc.save(ignore_permissions=True)

        new_id = unique_id

        action_type = "Update"

    meta = frappe.get_meta(form.target_doctype)

    for field in form.form_fields:

        df = meta.get_field(field.fieldname)

        if df and df.fieldtype == "Attach":

            file_url = cleaned_data.get(field.fieldname)

            if file_url:

                frappe.db.set_value(
                    "File",
                    {"file_url": file_url},
                    {
                        "attached_to_doctype": form.target_doctype,
                        "attached_to_name": doc.name
                    }
                )

    try:

        ip_address = frappe.local.request_ip or "Unknown"

        log_doc = frappe.get_doc({
            "doctype": "Form Submission Log",
            "form": form_name,
            "unique_id": new_id,
            "ip_address": ip_address,
            "action": action_type,
            "timestamp": frappe.utils.now()
        })

        log_doc.insert(ignore_permissions=True)

    except Exception:
        pass

    return {"unique_id": new_id}


@frappe.whitelist(allow_guest=True)
def upload_public_file():

    from frappe.utils.file_manager import save_file

    if "file" not in frappe.request.files:
        frappe.throw("No file attached")

    uploaded_file = frappe.request.files["file"]

    content = uploaded_file.stream.read()

    file_doc = save_file(
        uploaded_file.filename,
        content,
        None,
        None,
        is_private=0
    )

    return {
        "file_url": file_doc.file_url
    }