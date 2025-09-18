app_name = "sdrt"
app_title = "Sdrt"
app_publisher = "sdrt"
app_description = "gestion de sdrt"
app_email = "ouchgoutmohamed@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "sdrt",
# 		"logo": "/assets/sdrt/logo.png",
# 		"title": "Sdrt",
# 		"route": "/sdrt",
# 		"has_permission": "sdrt.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sdrt/css/sdrt.css"
# app_include_js = "/assets/sdrt/js/sdrt.js"

# include js, css files in header of web template
# web_include_css = "/assets/sdrt/css/sdrt.css"
# web_include_js = "/assets/sdrt/js/sdrt.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sdrt/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	# Inject custom logic overriding default "Get Items" button behaviour for Purchase Order
	"Purchase Order": "sdrt/custom/purchase_order.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sdrt/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sdrt.utils.jinja_methods",
# 	"filters": "sdrt.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "sdrt.install.before_install"
# after_install = "sdrt.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "sdrt.uninstall.before_uninstall"
# after_uninstall = "sdrt.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "sdrt.utils.before_app_install"
# after_app_install = "sdrt.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sdrt.utils.before_app_uninstall"
# after_app_uninstall = "sdrt.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sdrt.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	# Ensure estimation stays consistent when saving Material Request
	"Material Request": {
		"validate": "sdrt.sdrt.custom.material_request.validate",
	}
	,
	"Purchase Order": {
		"validate": "sdrt.sdrt.custom.validate_purchase_order_item",
		"on_submit": "sdrt.sdrt.custom.engage_budgets_for_po",
		"on_cancel": "sdrt.sdrt.custom.rollback_budgets_for_po"
	},
	"SDR Budget": {
		"before_insert": "sdrt.sdrt.custom.update_sdr_budget_available",
		"validate": "sdrt.sdrt.custom.update_sdr_budget_available"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sdrt.tasks.all"
# 	],
# 	"daily": [
# 		"sdrt.tasks.daily"
# 	],
# 	"hourly": [
# 		"sdrt.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sdrt.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sdrt.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "sdrt.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sdrt.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sdrt.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sdrt.utils.before_request"]
# after_request = ["sdrt.utils.after_request"]

# Job Events
# ----------
# before_job = ["sdrt.utils.before_job"]
# after_job = ["sdrt.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sdrt.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

