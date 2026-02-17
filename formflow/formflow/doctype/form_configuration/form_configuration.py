import frappe
from frappe.model.document import Document

class FormConfiguration(Document):

    def validate(self):
        self.form_name = frappe.scrub(self.form_name)

        if frappe.db.exists(
            "Form Configuration",
            {"form_name": self.form_name, "name": ["!=", self.name]}
        ):
            frappe.throw("Form Name must be unique")
