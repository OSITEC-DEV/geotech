def migrate(cr, version):
    """Delete stale ir.ui.view records for product.template that were written
    when analytic_distribution was temporarily in lims product_views.xml.
    They will be recreated cleanly from the current XML files."""
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE key IN (
            'lims.product_template_form_view_inherit2'
        )
    """)
