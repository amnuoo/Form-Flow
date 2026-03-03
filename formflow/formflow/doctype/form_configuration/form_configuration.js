frappe.ui.form.on('Form Configuration', {

    refresh(frm) {
        load_doctype_fields(frm);
    },

    target_doctype(frm) {
        load_doctype_fields(frm);
    }

});

function load_doctype_fields(frm) {

    if (!frm.doc.target_doctype) return;

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "DocType",
            name: frm.doc.target_doctype
        },
        callback: function(r) {

            if (!r.message) return;

            let fields = r.message.fields
                .filter(df =>
                    !["Section Break", "Column Break"].includes(df.fieldtype)
                )
                .map(df => df.fieldname);

            // Convert Data field into Select temporarily
            frm.fields_dict.form_fields.grid.update_docfield_property(
                "fieldname",
                "fieldtype",
                "Select"
            );

            frm.fields_dict.form_fields.grid.update_docfield_property(
                "fieldname",
                "options",
                fields.join("\n")
            );

            frm.refresh_field("form_fields");
        }
    });
}