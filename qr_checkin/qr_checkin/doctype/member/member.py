# Copyright (c) 2025, Njoroge Francis and contributors
# For license information, please see license.tx
import frappe
from frappe.model.document import Document


class Member(Document):

	def validate(self):
		# check if member id is unique
		if self.member_id:

			existing_member = frappe.get_all(
				"Member",
				filters={"member_id": self.member_id, "name": ["!=", self.name]},
				fields=["name"]
			)
			if existing_member:
				frappe.throw(f"Member ID {self.member_id} already exists for another member.")

	pass
