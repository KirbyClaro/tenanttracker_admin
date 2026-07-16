import customtkinter as ctk
import tkinter.ttk as ttk
import tkinter as tk
from tkinter import filedialog, messagebox
import time
from datetime import datetime
import sqlite3
import os
import shutil
from PIL import Image
from database import init_db
from tkcalendar import DateEntry

# Initialize database on launch
init_db()

# Ensure the uploads directory exists
os.makedirs("uploads", exist_ok=True)

class TenantTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("TenantTracker Admin")
        self.geometry("1200x750")
        
        self.tabview = ctk.CTkTabview(self, width=1150, height=700)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_tenants = self.tabview.add("Tenant Information")
        self.tab_financials = self.tabview.add("Financials")
        self.tab_summary = self.tabview.add("Monthly Summary")
        self.tab_settings = self.tabview.add("Settings")

        # States
        self.form_visible = False
        self.editing_tenant_id = None
        self.fin_form_visible = False
        self.editing_fin_id = None
        self.exp_editing_id = None

        self.setup_tenant_tab()
        self.setup_financials_tab() 
        self.setup_summary_tab()

    # ==========================================
    # TAB 1: TENANT MANAGEMENT
    # ==========================================
    def setup_tenant_tab(self):
        self.header_frame = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=10)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Tenant Management", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")

        self.toggle_btn = ctk.CTkButton(self.header_frame, text="+ Add New Tenant", command=self.toggle_form, fg_color="#1f538d", hover_color="#14375e")
        self.toggle_btn.pack(side="left", padx=20)

        self.clock_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=14))
        self.clock_label.pack(side="right")
        self.update_clock()

        self.search_frame = ctk.CTkFrame(self.tab_tenants, fg_color="#2b2b2b")
        self.search_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.filter_var = ctk.StringVar(value="Active")
        self.status_filter = ctk.CTkOptionMenu(
            self.search_frame, values=["Active", "Archived", "All"], 
            variable=self.filter_var, command=self.trigger_search, width=120
        )
        self.status_filter.pack(side="left", padx=10, pady=10)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.trigger_search)
        self.search_entry = ctk.CTkEntry(
            self.search_frame, placeholder_text="Search by Name or Room...", 
            textvariable=self.search_var, width=300
        )
        self.search_entry.pack(side="left", padx=(0, 10), pady=10)

        self.reset_cols_btn = ctk.CTkButton(
            self.search_frame, text="Reset Columns", command=self.reset_table_columns, 
            width=120, fg_color="#565b5e", hover_color="#343638"
        )
        self.reset_cols_btn.pack(side="right", padx=10, pady=10)

        self.tenant_content = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.tenant_content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.form_frame = ctk.CTkScrollableFrame(self.tenant_content, width=350, label_text="Tenant Details")

        self.contact_var = ctk.StringVar()
        self.contact_var.trace_add("write", self.validate_contact)
        self.monthly_var = ctk.StringVar()
        self.monthly_var.trace_add("write", lambda *args: self.validate_numeric_var(self.monthly_var))
        self.due_day_var = ctk.StringVar()
        self.due_day_var.trace_add("write", self.validate_due_day)

        self.entries = {}
        self.fields = [
            "Status", "Full Name", "Address", "Room Number", "Date Started",
            "Lease Term", "Move Out Date", "Monthly Due", "Rent Due Day", "Valid ID", "Working/Job",
            "Messenger Link", "Email", "Contact Number"
        ]

        for field in self.fields:
            lbl = ctk.CTkLabel(self.form_frame, text=field)
            lbl.pack(anchor="w", padx=10, pady=(5, 0))

            if field in ["Date Started", "Move Out Date"]:
                ent = DateEntry(self.form_frame, width=45, font=('Segoe UI', 11), background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
                ent.pack(padx=10, pady=(0, 5), ipady=4)
                self.entries[field] = ent
            elif field == "Status":
                ent = ctk.CTkOptionMenu(self.form_frame, values=["Active", "Archived"], width=300)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            elif field == "Contact Number":
                ent = ctk.CTkEntry(self.form_frame, width=300, textvariable=self.contact_var)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            elif field == "Monthly Due":
                ent = ctk.CTkEntry(self.form_frame, width=300, textvariable=self.monthly_var)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            elif field == "Rent Due Day":
                ent = ctk.CTkEntry(self.form_frame, width=300, textvariable=self.due_day_var, placeholder_text="e.g., 5 or 15")
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            elif field == "Valid ID":
                id_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
                id_frame.pack(padx=10, pady=(0, 5), fill="x")
                ent = ctk.CTkEntry(id_frame, width=210, state="readonly", placeholder_text="No file selected")
                ent.pack(side="left")
                upload_btn = ctk.CTkButton(id_frame, text="Upload", width=80, command=self.upload_id_image)
                upload_btn.pack(side="right")
                self.entries[field] = ent
            else:
                ent = ctk.CTkEntry(self.form_frame, width=300)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent

        lbl_notes = ctk.CTkLabel(self.form_frame, text="Remarks / Notes")
        lbl_notes.pack(anchor="w", padx=10, pady=(5, 0))
        self.notes_box = ctk.CTkTextbox(self.form_frame, width=300, height=80)
        self.notes_box.pack(padx=10, pady=(0, 5))

        self.check_vars = {
            "Agreement Signed": ctk.IntVar(),
            "Advance Paid": ctk.IntVar(),
            "Deposit Paid": ctk.IntVar()
        }

        for check_name, var in self.check_vars.items():
            chk = ctk.CTkCheckBox(self.form_frame, text=check_name, variable=var)
            chk.pack(anchor="w", padx=10, pady=5)

        self.save_btn = ctk.CTkButton(self.form_frame, text="Save Tenant", command=self.save_tenant_to_db, fg_color="green", hover_color="darkgreen")
        self.save_btn.pack(pady=20, padx=10, fill="x")

        self.table_frame = ctk.CTkFrame(self.tenant_content)
        self.table_frame.pack(side="right", fill="both", expand=True)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=40, font=('Segoe UI', 11), fieldbackground="#2b2b2b", bordercolor="#343638", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", font=('Segoe UI', 12, 'bold'), relief="flat")
        style.map("Treeview.Heading", background=[('active', '#343638')])

        self.columns = (
            "ID", "Status", "Name", "Address", "Room", "Started", "Term", 
            "Move Out", "Monthly", "Due Day", "Valid ID", "Job", "Messenger", 
            "Email", "Contact", "Notes", "Agreement", "Advance", "Deposit", "Last Edited"
        )
        self.tenant_table = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")
        
        self.tree_scroll_y = ctk.CTkScrollbar(self.table_frame, orientation="vertical", command=self.tenant_table.yview)
        self.tree_scroll_y.pack(side="right", fill="y", pady=(10, 0))
        self.tree_scroll_x = ctk.CTkScrollbar(self.table_frame, orientation="horizontal", command=self.tenant_table.xview)
        self.tree_scroll_x.pack(side="bottom", fill="x", padx=(10, 0))

        self.tenant_table.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)
        for col in self.columns: self.tenant_table.heading(col, text=col)
        self.reset_table_columns()
        self.tenant_table.pack(fill="both", expand=True, padx=(10, 0), pady=(10, 0))

        self.context_menu = tk.Menu(self, tearoff=0, bg="#343638", fg="white", activebackground="#1f538d")
        self.context_menu.add_command(label="Copy Cell Value", command=self.copy_cell)
        self.tenant_table.bind("<Button-3>", self.show_context_menu)

        self.action_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.view_btn = ctk.CTkButton(self.action_frame, text="View Selected", command=self.view_tenant_details, fg_color="#1f538d", hover_color="#14375e")
        self.view_btn.pack(side="left", padx=(0, 10))
        self.edit_btn = ctk.CTkButton(self.action_frame, text="Edit Selected", command=self.load_for_editing, fg_color="#B8860B", hover_color="#8B6508")
        self.edit_btn.pack(side="left", padx=(0, 10))
        self.delete_btn = ctk.CTkButton(self.action_frame, text="Delete Selected", command=self.delete_tenant, fg_color="#8B0000", hover_color="#660000")
        self.delete_btn.pack(side="left")

        self.load_tenants_from_db()

    # ==========================================
    # TAB 2: FINANCIALS 
    # ==========================================
    def setup_financials_tab(self):
        self.fin_header = ctk.CTkFrame(self.tab_financials, fg_color="transparent")
        self.fin_header.pack(fill="x", padx=10, pady=10)

        self.fin_title = ctk.CTkLabel(self.fin_header, text="Financial Tracking", font=ctk.CTkFont(size=24, weight="bold"))
        self.fin_title.pack(side="left")

        self.fin_toggle_btn = ctk.CTkButton(self.fin_header, text="+ Add Transaction", command=self.toggle_fin_form, fg_color="#1f538d", hover_color="#14375e")
        self.fin_toggle_btn.pack(side="left", padx=20)

        self.fin_content = ctk.CTkFrame(self.tab_financials, fg_color="transparent")
        self.fin_content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.fin_form_frame = ctk.CTkFrame(self.fin_content, width=350)

        self.fin_entries = {}
        
        lbl_tenant = ctk.CTkLabel(self.fin_form_frame, text="Tenant Name")
        lbl_tenant.pack(anchor="w", padx=10, pady=(15, 0))
        self.fin_tenant_combo = ctk.CTkComboBox(self.fin_form_frame, width=300, values=self.get_active_tenant_names())
        self.fin_tenant_combo.pack(padx=10, pady=(0, 5))
        self.fin_entries["Tenant Name"] = self.fin_tenant_combo

        lbl_type = ctk.CTkLabel(self.fin_form_frame, text="Transaction Type")
        lbl_type.pack(anchor="w", padx=10, pady=(5, 0))
        self.fin_type_combo = ctk.CTkComboBox(self.fin_form_frame, width=300, values=["Rent", "Water", "Electricity", "Internet", "Maintenance", "Deposit", "Other"])
        self.fin_type_combo.pack(padx=10, pady=(0, 5))
        self.fin_entries["Type"] = self.fin_type_combo

        self.fin_amount_var = ctk.StringVar()
        self.fin_amount_var.trace_add("write", lambda *args: self.validate_numeric_var(self.fin_amount_var))
        lbl_amount = ctk.CTkLabel(self.fin_form_frame, text="Amount Due")
        lbl_amount.pack(anchor="w", padx=10, pady=(5, 0))
        self.fin_amount_entry = ctk.CTkEntry(self.fin_form_frame, width=300, textvariable=self.fin_amount_var)
        self.fin_amount_entry.pack(padx=10, pady=(0, 5))
        self.fin_entries["Amount"] = self.fin_amount_entry

        lbl_due = ctk.CTkLabel(self.fin_form_frame, text="Due Date")
        lbl_due.pack(anchor="w", padx=10, pady=(5, 0))
        self.fin_due_entry = DateEntry(self.fin_form_frame, width=45, font=('Segoe UI', 11), background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
        self.fin_due_entry.pack(padx=10, pady=(0, 5), ipady=4)
        self.fin_entries["Due Date"] = self.fin_due_entry

        lbl_status = ctk.CTkLabel(self.fin_form_frame, text="Status")
        lbl_status.pack(anchor="w", padx=10, pady=(5, 0))
        self.fin_status_combo = ctk.CTkComboBox(self.fin_form_frame, width=300, values=["Pending", "Paid", "Overdue"])
        self.fin_status_combo.pack(padx=10, pady=(0, 15))
        self.fin_entries["Status"] = self.fin_status_combo

        self.fin_save_btn = ctk.CTkButton(self.fin_form_frame, text="Save Transaction", command=self.save_fin_to_db, fg_color="green", hover_color="darkgreen")
        self.fin_save_btn.pack(pady=10, padx=10, fill="x")

        self.fin_table_frame = ctk.CTkFrame(self.fin_content)
        self.fin_table_frame.pack(side="right", fill="both", expand=True)

        self.fin_columns = ("ID", "Tenant Name", "Type", "Amount", "Due Date", "Status")
        self.fin_table = ttk.Treeview(self.fin_table_frame, columns=self.fin_columns, show="headings")
        
        self.fin_scroll_y = ctk.CTkScrollbar(self.fin_table_frame, orientation="vertical", command=self.fin_table.yview)
        self.fin_scroll_y.pack(side="right", fill="y", pady=(10, 0))
        self.fin_table.configure(yscrollcommand=self.fin_scroll_y.set)
        
        for col in self.fin_columns: self.fin_table.heading(col, text=col)
        
        self.fin_table.column("ID", width=50, anchor="center")
        self.fin_table.column("Tenant Name", width=250, anchor="w")
        self.fin_table.column("Type", width=150, anchor="center")
        self.fin_table.column("Amount", width=150, anchor="center")
        self.fin_table.column("Due Date", width=150, anchor="center")
        self.fin_table.column("Status", width=120, anchor="center")
        
        self.fin_table.pack(fill="both", expand=True, padx=(10, 0), pady=(10, 0))

        self.fin_action_frame = ctk.CTkFrame(self.fin_table_frame, fg_color="transparent")
        self.fin_action_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.mark_paid_btn = ctk.CTkButton(self.fin_action_frame, text="Mark as Paid", command=self.mark_fin_paid, fg_color="green", hover_color="darkgreen")
        self.mark_paid_btn.pack(side="left", padx=(0, 10))
        self.edit_fin_btn = ctk.CTkButton(self.fin_action_frame, text="Edit Selected", command=self.load_fin_for_editing, fg_color="#B8860B", hover_color="#8B6508")
        self.edit_fin_btn.pack(side="left", padx=(0, 10))
        self.delete_fin_btn = ctk.CTkButton(self.fin_action_frame, text="Delete Selected", command=self.delete_fin, fg_color="#8B0000", hover_color="#660000")
        self.delete_fin_btn.pack(side="left")

        self.load_fin_from_db()

    # ==========================================
    # TAB 3: MONTHLY SUMMARY & EXPENSES
    # ==========================================
    def setup_summary_tab(self):
        # 1. Top Dashboard (Savings Tracker)
        self.dash_frame = ctk.CTkFrame(self.tab_summary, fg_color="transparent")
        self.dash_frame.pack(fill="x", padx=10, pady=10)
        
        # Month Selector
        self.month_list = [f"{datetime.now().year}-{str(m).zfill(2)}" for m in range(1, 13)]
        self.selected_month = ctk.StringVar(value=datetime.now().strftime('%Y-%m'))
        
        self.header_top = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        self.header_top.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(self.header_top, text="Business Savings Tracker", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkOptionMenu(self.header_top, values=self.month_list, variable=self.selected_month, command=self.refresh_summary_dashboard).pack(side="right", padx=10)
        ctk.CTkLabel(self.header_top, text="Select Month:").pack(side="right")

        # Stat Cards
        self.cards_frame = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        self.cards_frame.pack(fill="x")

        self.lbl_inc = ctk.CTkLabel(self.cards_frame, text="Monthly Income\n₱ 0.00", font=("Segoe UI", 16, "bold"), fg_color="#1f538d", corner_radius=8, width=250, height=80)
        self.lbl_inc.pack(side="left", padx=10, expand=True)

        self.lbl_exp = ctk.CTkLabel(self.cards_frame, text="Monthly Expenses\n₱ 0.00", font=("Segoe UI", 16, "bold"), fg_color="#8B0000", corner_radius=8, width=250, height=80)
        self.lbl_exp.pack(side="left", padx=10, expand=True)

        self.lbl_save_mo = ctk.CTkLabel(self.cards_frame, text="Monthly Savings\n₱ 0.00", font=("Segoe UI", 18, "bold"), fg_color="#006400", corner_radius=8, width=250, height=80)
        self.lbl_save_mo.pack(side="left", padx=10, expand=True)

        self.lbl_save_tot = ctk.CTkLabel(self.cards_frame, text="Total Savings (All-Time)\n₱ 0.00", font=("Segoe UI", 18, "bold"), fg_color="#B8860B", corner_radius=8, width=250, height=80)
        self.lbl_save_tot.pack(side="left", padx=10, expand=True)

        # Separator
        ctk.CTkFrame(self.tab_summary, height=2, fg_color="#565b5e").pack(fill="x", padx=10, pady=10)

        # 2. Main Content (Left Form, Right Table)
        self.sum_content = ctk.CTkFrame(self.tab_summary, fg_color="transparent")
        self.sum_content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # LEFT: Expense Input Form
        self.exp_form_frame = ctk.CTkFrame(self.sum_content, width=350)
        self.exp_form_frame.pack(side="left", fill="y", padx=(0, 10))

        ctk.CTkLabel(self.exp_form_frame, text="Log Overall Expense", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 15))

        self.exp_cat_combo = ctk.CTkComboBox(self.exp_form_frame, width=300, values=[
            "Water Bill", "Electric Bill", "Internet", "Garbage Pickup", 
            "Monthly Maintenance Fee", "Monthly Miscellaneous"
        ])
        ctk.CTkLabel(self.exp_form_frame, text="Expense Category").pack(anchor="w", padx=10)
        self.exp_cat_combo.pack(padx=10, pady=(0, 10))

        self.exp_amt_var = ctk.StringVar()
        self.exp_amt_var.trace_add("write", lambda *args: self.validate_numeric_var(self.exp_amt_var))
        self.exp_amt_entry = ctk.CTkEntry(self.exp_form_frame, width=300, textvariable=self.exp_amt_var)
        ctk.CTkLabel(self.exp_form_frame, text="Amount Due").pack(anchor="w", padx=10)
        self.exp_amt_entry.pack(padx=10, pady=(0, 10))

        self.exp_date_entry = DateEntry(self.exp_form_frame, width=45, font=('Segoe UI', 11), background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
        ctk.CTkLabel(self.exp_form_frame, text="Due Date").pack(anchor="w", padx=10)
        self.exp_date_entry.pack(padx=10, pady=(0, 10), ipady=4)

        self.exp_status_combo = ctk.CTkComboBox(self.exp_form_frame, width=300, values=["Pending", "Paid"])
        ctk.CTkLabel(self.exp_form_frame, text="Payment Status").pack(anchor="w", padx=10)
        self.exp_status_combo.pack(padx=10, pady=(0, 20))

        self.exp_save_btn = ctk.CTkButton(self.exp_form_frame, text="Save Expense", command=self.save_expense_to_db, fg_color="green", hover_color="darkgreen")
        self.exp_save_btn.pack(pady=10, padx=10, fill="x")
        
        self.exp_clear_btn = ctk.CTkButton(self.exp_form_frame, text="Clear Form", command=self.clear_exp_form, fg_color="#565b5e", hover_color="#343638")
        self.exp_clear_btn.pack(pady=5, padx=10, fill="x")

        # RIGHT: Expenses Table
        self.exp_table_frame = ctk.CTkFrame(self.sum_content)
        self.exp_table_frame.pack(side="right", fill="both", expand=True)

        self.exp_cols = ("ID", "Category", "Amount", "Due Date", "Status")
        self.exp_table = ttk.Treeview(self.exp_table_frame, columns=self.exp_cols, show="headings")
        
        self.exp_scroll_y = ctk.CTkScrollbar(self.exp_table_frame, orientation="vertical", command=self.exp_table.yview)
        self.exp_scroll_y.pack(side="right", fill="y", pady=(10, 0))
        self.exp_table.configure(yscrollcommand=self.exp_scroll_y.set)
        
        for col in self.exp_cols: self.exp_table.heading(col, text=col)
        self.exp_table.column("ID", width=40, anchor="center")
        self.exp_table.column("Category", width=250, anchor="w")
        self.exp_table.column("Amount", width=120, anchor="center")
        self.exp_table.column("Due Date", width=120, anchor="center")
        self.exp_table.column("Status", width=100, anchor="center")
        self.exp_table.pack(fill="both", expand=True, padx=(10, 0), pady=(10, 0))

        # Expense Actions
        self.exp_action_frame = ctk.CTkFrame(self.exp_table_frame, fg_color="transparent")
        self.exp_action_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.exp_paid_btn = ctk.CTkButton(self.exp_action_frame, text="Mark as Paid", command=self.mark_expense_paid, fg_color="green", hover_color="darkgreen")
        self.exp_paid_btn.pack(side="left", padx=(0, 10))
        self.exp_edit_btn = ctk.CTkButton(self.exp_action_frame, text="Edit Selected", command=self.load_expense_for_editing, fg_color="#B8860B", hover_color="#8B6508")
        self.exp_edit_btn.pack(side="left", padx=(0, 10))
        self.exp_delete_btn = ctk.CTkButton(self.exp_action_frame, text="Delete Selected", command=self.delete_expense, fg_color="#8B0000", hover_color="#660000")
        self.exp_delete_btn.pack(side="left")

        self.refresh_summary_dashboard()

    # --- Summary & Expense Functions ---
    def refresh_summary_dashboard(self, *args):
        month_str = self.selected_month.get()
        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()

        # 1. Load Expense Table for Selected Month
        for item in self.exp_table.get_children(): self.exp_table.delete(item)
        cursor.execute("SELECT id, category, amount, due_date, status FROM expenses WHERE month_year=?", (month_str,))
        for row in cursor.fetchall():
            self.exp_table.insert("", "end", values=row)

        # 2. Calculate Dashboard Stats (STRICTLY "PAID" TRANSACTIONS ONLY)
        # Monthly Income 
        cursor.execute("SELECT SUM(amount) FROM financials WHERE status='Paid' AND due_date LIKE ?", (f"{month_str}%",))
        mo_income = cursor.fetchone()[0] or 0.0

        # Monthly Expenses (Only counts expenses you have actually Paid)
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE status='Paid' AND month_year=?", (month_str,))
        mo_expenses = cursor.fetchone()[0] or 0.0
        
        # Monthly Savings
        mo_savings = mo_income - mo_expenses

        # Total Savings (All-Time Paid Income - All-Time Paid Expenses)
        cursor.execute("SELECT SUM(amount) FROM financials WHERE status='Paid'")
        total_income = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE status='Paid'")
        total_paid_expenses = cursor.fetchone()[0] or 0.0
        total_savings = total_income - total_paid_expenses

        conn.close()

        # 3. Update the UI Cards
        self.lbl_inc.configure(text=f"Monthly Income (Paid)\n₱ {mo_income:,.2f}")
        self.lbl_exp.configure(text=f"Monthly Expenses (Paid)\n₱ {mo_expenses:,.2f}")
        self.lbl_save_mo.configure(text=f"Monthly Savings\n₱ {mo_savings:,.2f}")
        self.lbl_save_tot.configure(text=f"Total Savings (All-Time)\n₱ {total_savings:,.2f}")

    def clear_exp_form(self):
        self.exp_amt_entry.delete(0, 'end')
        self.exp_date_entry.set_date(time.strftime('%Y-%m-%d'))
        self.exp_status_combo.set("Pending")
        self.exp_editing_id = None
        self.exp_save_btn.configure(text="Save Expense", fg_color="green", hover_color="darkgreen")

    def save_expense_to_db(self):
        cat = self.exp_cat_combo.get()
        amt = self.exp_amt_entry.get()
        date = self.exp_date_entry.get()
        status = self.exp_status_combo.get()
        month_str = self.selected_month.get()

        if not amt: return messagebox.showerror("Error", "Please enter an amount.")

        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        
        if self.exp_editing_id:
            cursor.execute("UPDATE expenses SET category=?, amount=?, due_date=?, status=?, month_year=? WHERE id=?", 
                           (cat, amt, date, status, month_str, self.exp_editing_id))
        else:
            cursor.execute("INSERT INTO expenses (month_year, category, amount, due_date, status) VALUES (?, ?, ?, ?, ?)", 
                           (month_str, cat, amt, date, status))
        
        conn.commit()
        conn.close()

        self.clear_exp_form()
        self.refresh_summary_dashboard()

    def load_expense_for_editing(self):
        selected = self.exp_table.selection()
        if not selected: return
        
        vals = self.exp_table.item(selected[0])['values']
        self.exp_editing_id = vals[0]
        self.exp_cat_combo.set(vals[1])
        self.exp_amt_entry.delete(0, 'end')
        self.exp_amt_entry.insert(0, vals[2])
        self.exp_date_entry.set_date(vals[3])
        self.exp_status_combo.set(vals[4])
        self.exp_save_btn.configure(text="Update Expense", fg_color="#B8860B", hover_color="#8B6508")

    def mark_expense_paid(self):
        selected = self.exp_table.selection()
        if not selected: return
        e_id = self.exp_table.item(selected[0])['values'][0]
        conn = sqlite3.connect('tenant_tracker.db')
        conn.cursor().execute("UPDATE expenses SET status='Paid' WHERE id=?", (e_id,))
        conn.commit()
        conn.close()
        self.refresh_summary_dashboard()

    def delete_expense(self):
        selected = self.exp_table.selection()
        if not selected: return
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this expense?")
        if confirm:
            e_id = self.exp_table.item(selected[0])['values'][0]
            conn = sqlite3.connect('tenant_tracker.db')
            conn.cursor().execute("DELETE FROM expenses WHERE id=?", (e_id,))
            conn.commit()
            conn.close()
            self.refresh_summary_dashboard()


    # ==========================================
    # GLOBAL HELPER FUNCTIONS (Used by Tabs 1 & 2)
    # ==========================================
    def get_active_tenant_names(self):
        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        cursor.execute("SELECT full_name FROM tenants WHERE status='Active'")
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names if names else ["No Active Tenants"]

    def validate_numeric_var(self, str_var):
        cv = str_var.get()
        filtered = ''.join([c for c in cv if c.isdigit() or c == '.'])
        if filtered.count('.') > 1:
            parts = filtered.split('.')
            filtered = parts[0] + '.' + ''.join(parts[1:])
        if cv != filtered: str_var.set(filtered)

    # --- Financial Tab Functions ---
    def toggle_fin_form(self):
        if self.fin_form_visible:
            self.fin_form_frame.pack_forget()
            self.fin_toggle_btn.configure(text="+ Add Transaction", fg_color="#1f538d", hover_color="#14375e")
            self.fin_form_visible = False
            if self.editing_fin_id: self.clear_fin_form()
        else:
            self.fin_tenant_combo.configure(values=self.get_active_tenant_names())
            self.fin_form_frame.pack(side="left", fill="y", padx=(0, 10), before=self.fin_table_frame)
            self.fin_toggle_btn.configure(text="- Close Form", fg_color="#8B0000", hover_color="#660000")
            self.fin_form_visible = True

    def load_fin_from_db(self):
        for item in self.fin_table.get_children(): self.fin_table.delete(item)
        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, tenant_name, type, amount, due_date, status FROM financials")
        for row in cursor.fetchall():
            self.fin_table.insert("", "end", values=row)
        conn.close()

    def clear_fin_form(self):
        self.fin_amount_entry.delete(0, 'end')
        self.fin_due_entry.set_date(time.strftime('%Y-%m-%d'))
        self.fin_status_combo.set("Pending")
        self.editing_fin_id = None
        self.fin_save_btn.configure(text="Save Transaction", fg_color="green", hover_color="darkgreen")

    def save_fin_to_db(self):
        t_name = self.fin_tenant_combo.get()
        t_type = self.fin_type_combo.get()
        t_amount = self.fin_amount_entry.get()
        t_due = self.fin_due_entry.get()
        t_status = self.fin_status_combo.get()

        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        if self.editing_fin_id:
            cursor.execute("UPDATE financials SET tenant_name=?, type=?, amount=?, due_date=?, status=? WHERE id=?", 
                           (t_name, t_type, t_amount, t_due, t_status, self.editing_fin_id))
        else:
            cursor.execute("INSERT INTO financials (tenant_name, type, amount, due_date, status) VALUES (?, ?, ?, ?, ?)", 
                           (t_name, t_type, t_amount, t_due, t_status))
        conn.commit()
        conn.close()

        self.clear_fin_form()
        self.load_fin_from_db()
        self.toggle_fin_form()
        self.refresh_summary_dashboard() 

    def load_fin_for_editing(self):
        selected = self.fin_table.selection()
        if not selected: return
        
        vals = self.fin_table.item(selected[0])['values']
        if not self.fin_form_visible: self.toggle_fin_form()
        
        self.editing_fin_id = vals[0]
        self.fin_save_btn.configure(text="Update Transaction", fg_color="#B8860B", hover_color="#8B6508")
        
        self.fin_tenant_combo.set(vals[1])
        self.fin_type_combo.set(vals[2])
        self.fin_amount_entry.delete(0, 'end')
        self.fin_amount_entry.insert(0, vals[3])
        self.fin_due_entry.set_date(vals[4])
        self.fin_status_combo.set(vals[5])

    def delete_fin(self):
        selected = self.fin_table.selection()
        if not selected: return
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this transaction?")
        if confirm:
            f_id = self.fin_table.item(selected[0])['values'][0]
            conn = sqlite3.connect('tenant_tracker.db')
            conn.cursor().execute("DELETE FROM financials WHERE id=?", (f_id,))
            conn.commit()
            conn.close()
            self.load_fin_from_db()
            self.refresh_summary_dashboard() 

    def mark_fin_paid(self):
        selected = self.fin_table.selection()
        if not selected: return
        f_id = self.fin_table.item(selected[0])['values'][0]
        conn = sqlite3.connect('tenant_tracker.db')
        conn.cursor().execute("UPDATE financials SET status='Paid' WHERE id=?", (f_id,))
        conn.commit()
        conn.close()
        self.load_fin_from_db()
        self.refresh_summary_dashboard() 

    # --- Tenant Tab Functions ---
    def update_clock(self):
        current_time = time.strftime('%I:%M:%S %p | %B %d, %Y')
        self.clock_label.configure(text=current_time)
        self.after(1000, self.update_clock)

    def trigger_search(self, *args):
        self.load_tenants_from_db()

    def validate_contact(self, *args):
        cv = self.contact_var.get()
        no_letters = ''.join(filter(str.isdigit, cv))
        if cv != no_letters: self.contact_var.set(no_letters)

    def validate_due_day(self, *args):
        cv = self.due_day_var.get()
        no_letters = ''.join(filter(str.isdigit, cv))
        if no_letters and int(no_letters) > 31: no_letters = "31"
        if cv != no_letters: self.due_day_var.set(no_letters)

    def upload_id_image(self):
        file_path = filedialog.askopenfilename(title="Select ID Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            filename = f"{int(time.time())}_{os.path.basename(file_path)}"
            destination = os.path.join("uploads", filename)
            shutil.copy(file_path, destination)
            ent = self.entries["Valid ID"]
            ent.configure(state="normal")
            ent.delete(0, 'end')
            ent.insert(0, destination)
            ent.configure(state="readonly")

    def view_tenant_details(self):
        selected = self.tenant_table.selection()
        if not selected: return 
        vals = self.tenant_table.item(selected[0])['values']
        t_name = str(vals[2])
        win = ctk.CTkToplevel(self)
        win.title(f"Tenant Card: {t_name}")
        win.geometry("550x800")
        win.attributes("-topmost", True) 
        
        ctk.CTkLabel(win, text=f"Data for: {t_name}", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))
        scroll = ctk.CTkScrollableFrame(win, width=500, height=650)
        scroll.pack(padx=20, pady=10, fill="both", expand=True)
        
        for idx, col in enumerate(self.columns):
            val = vals[idx]
            d_val = str(val) if val not in ["None", ""] else "N/A"
            if col == "Notes":
                ctk.CTkLabel(scroll, text=f"{col}:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(15, 0), padx=5)
                box = ctk.CTkTextbox(scroll, width=460, height=100)
                box.pack(anchor="w", pady=(0, 10), padx=5)
                box.insert("1.0", d_val)
                box.configure(state="disabled") 
            elif col == "Valid ID" and d_val != "N/A" and os.path.exists(d_val):
                ctk.CTkLabel(scroll, text="Valid ID Image:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0), padx=5)
                try:
                    img = Image.open(d_val)
                    w, h = img.size
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(450, int(h * (450/w))))
                    ctk.CTkLabel(scroll, image=ctk_img, text="").pack(anchor="w", pady=(5, 10), padx=5)
                except: ctk.CTkLabel(scroll, text="[Image could not be loaded]").pack(anchor="w", padx=5)
            else:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=4, padx=5)
                ctk.CTkLabel(row, text=f"{col}:", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=d_val, anchor="w", wraplength=340, justify="left").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(win, text="Close Window", command=win.destroy, fg_color="#565b5e", hover_color="#343638").pack(pady=(10, 20))

    def show_context_menu(self, event):
        if self.tenant_table.identify_region(event.x, event.y) == "cell":
            self.r_row = self.tenant_table.identify_row(event.y)
            self.r_col = self.tenant_table.identify_column(event.x)
            self.tenant_table.selection_set(self.r_row)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_cell(self):
        if hasattr(self, 'r_row') and hasattr(self, 'r_col'):
            idx = int(self.r_col.replace('#', '')) - 1
            vals = self.tenant_table.item(self.r_row)['values']
            if 0 <= idx < len(vals):
                self.clipboard_clear()
                self.clipboard_append(str(vals[idx]))
                self.update() 
                self.title("TenantTracker Admin - Copied to Clipboard!")
                self.after(1500, lambda: self.title("TenantTracker Admin"))

    def reset_table_columns(self):
        widths = {"ID": 40, "Status": 80, "Name": 180, "Address": 280, "Room": 60, "Started": 100, "Term": 80, "Move Out": 100, "Monthly": 90, "Due Day": 80, "Valid ID": 130, "Job": 140, "Messenger": 180, "Email": 220, "Contact": 120, "Notes": 250, "Agreement": 80, "Advance": 80, "Deposit": 80, "Last Edited": 170}
        for col, w in widths.items():
            self.tenant_table.column(col, width=w, anchor="w" if col in ["Name", "Address", "Messenger", "Email", "Notes", "Job", "Valid ID"] else "center")

    def toggle_form(self):
        if self.form_visible:
            self.form_frame.pack_forget()
            self.toggle_btn.configure(text="+ Add New Tenant", fg_color="#1f538d", hover_color="#14375e")
            self.form_visible = False
            if self.editing_tenant_id: self.clear_form()
        else:
            self.form_frame.pack(side="left", fill="y", padx=(0, 10), before=self.table_frame)
            self.toggle_btn.configure(text="- Close Form", fg_color="#8B0000", hover_color="#660000")
            self.form_visible = True

    def load_for_editing(self):
        selected = self.tenant_table.selection()
        if not selected: return
        vals = self.tenant_table.item(selected[0])['values']
        if not self.form_visible: self.toggle_form()
        self.editing_tenant_id = vals[0]
        self.save_btn.configure(text="Update Tenant", fg_color="#B8860B", hover_color="#8B6508")
        
        for idx, field in enumerate(self.fields):
            v = str(vals[idx + 1]) if vals[idx + 1] != "None" else ""
            if field in ["Date Started", "Move Out Date"]: self.entries[field].set_date(v)
            elif field == "Status": self.entries[field].set(v)
            elif field == "Valid ID":
                self.entries[field].configure(state="normal")
                self.entries[field].delete(0, 'end')
                self.entries[field].insert(0, v)
                self.entries[field].configure(state="readonly")
            else:
                self.entries[field].delete(0, 'end')
                self.entries[field].insert(0, v)
        self.notes_box.delete("1.0", "end")
        self.notes_box.insert("1.0", str(vals[15]) if vals[15] != "None" else "")
        self.check_vars["Agreement Signed"].set(1 if vals[16] == "Yes" else 0)
        self.check_vars["Advance Paid"].set(1 if vals[17] == "Yes" else 0)
        self.check_vars["Deposit Paid"].set(1 if vals[18] == "Yes" else 0)

    def delete_tenant(self):
        selected = self.tenant_table.selection()
        if not selected: return
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this tenant?\n\nThis action cannot be undone.")
        if confirm:
            conn = sqlite3.connect('tenant_tracker.db')
            conn.cursor().execute("DELETE FROM tenants WHERE id = ?", (self.tenant_table.item(selected[0])['values'][0],))
            conn.commit()
            conn.close()
            self.load_tenants_from_db()

    def clear_form(self):
        for f, e in self.entries.items():
            if f in ["Date Started", "Move Out Date"]: e.set_date(time.strftime('%Y-%m-%d'))
            elif f == "Status": e.set("Active")
            elif f == "Valid ID":
                e.configure(state="normal")
                e.delete(0, 'end')
                e.configure(state="readonly")
            else: e.delete(0, 'end')
        self.notes_box.delete("1.0", "end")
        for v in self.check_vars.values(): v.set(0)
        self.editing_tenant_id = None
        self.save_btn.configure(text="Save Tenant", fg_color="green", hover_color="darkgreen")

    def save_tenant_to_db(self):
        data = [self.entries[f].get() for f in self.fields]
        data.append(self.notes_box.get("1.0", "end-1c")) 
        data.extend([self.check_vars[c].get() for c in self.check_vars])
        data.append(time.strftime('%Y-%m-%d %I:%M %p'))

        conn = sqlite3.connect('tenant_tracker.db')
        if self.editing_tenant_id:
            data.append(self.editing_tenant_id)
            conn.cursor().execute('''UPDATE tenants SET status=?, full_name=?, address=?, room_number=?, date_started=?, lease_term=?, move_out_date=?, monthly_due=?, rent_due_day=?, valid_id=?, job=?, messenger_link=?, email=?, contact_number=?, notes=?, agreement_signed=?, advance_paid=?, deposit_paid=?, last_edited=? WHERE id=?''', data)
        else:
            conn.cursor().execute('''INSERT INTO tenants (status, full_name, address, room_number, date_started, lease_term, move_out_date, monthly_due, rent_due_day, valid_id, job, messenger_link, email, contact_number, notes, agreement_signed, advance_paid, deposit_paid, last_edited) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()
        conn.close()
        self.clear_form()
        self.load_tenants_from_db()
        self.toggle_form()

    def load_tenants_from_db(self):
        for i in self.tenant_table.get_children(): self.tenant_table.delete(i)
        conn = sqlite3.connect('tenant_tracker.db')
        stat, search = self.filter_var.get(), self.search_var.get()
        q, p = "SELECT * FROM tenants WHERE 1=1", []
        if stat != "All": q += " AND status = ?"; p.append(stat)
        if search: q += " AND (full_name LIKE ? OR room_number LIKE ?)"; p.extend([f"%{search}%", f"%{search}%"])
        cursor = conn.cursor()
        cursor.execute(q, p)
        for r in cursor.fetchall():
            row = list(r)
            row[16], row[17], row[18] = ["Yes" if x == 1 else "No" for x in (row[16], row[17], row[18])]
            self.tenant_table.insert("", "end", values=row)
        conn.close()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = TenantTrackerApp()
    app.mainloop()