import customtkinter as ctk
import tkinter.ttk as ttk
import tkinter as tk
from tkinter import filedialog, messagebox
import time
from datetime import datetime
import sqlite3
import os
import shutil
import csv
import zipfile
import sys
import socket
import re
from PIL import Image
from database import init_db
from tkcalendar import DateEntry
import smtplib
from email.message import EmailMessage

# ==========================================
# PRE-DEPLOYMENT PATH SAFETY
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "tenant_tracker.db")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Initialize database on launch securely
init_db()

class TenantTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load saved settings on launch
        self.app_settings = self.load_settings()

        # Window Setup
        self.title("TenantTracker Admin")
        self.geometry("1200x750")
        
        # Load the custom icon
        icon_path = os.path.join(BASE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        self.tabview = ctk.CTkTabview(self, width=1150, height=700)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_tenants = self.tabview.add("Tenant Information")
        self.tab_financials = self.tabview.add("Financials")
        self.tab_summary = self.tabview.add("Monthly Summary")
        self.tab_settings = self.tabview.add("Settings")

        # States
        self.form_visible = False
        self.editing_tenant_id = None

        self.setup_tenant_tab()
        self.setup_financials_tab() 
        self.setup_summary_tab()
        self.setup_settings_tab()
        
        # Apply table themes immediately on boot
        self.apply_table_theme()

    def load_settings(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        settings = dict(cursor.fetchall())
        conn.close()

        theme = settings.get("theme", "System")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")
        return settings

    def apply_table_theme(self):
        mode = ctk.get_appearance_mode()
        style = ttk.Style()
        style.theme_use("default")
        
        if mode == "Light":
            bg_color = "#ffffff"
            fg_color = "#000000"
            head_bg = "#e0e0e0"
            head_fg = "#000000"
            head_active = "#d3d3d3"
            border = "#cccccc"
        else:
            bg_color = "#2b2b2b"
            fg_color = "white"
            head_bg = "#565b5e"
            head_fg = "white"
            head_active = "#343638"
            border = "#343638"

        style.configure("Treeview", background=bg_color, foreground=fg_color, rowheight=40, font=('Segoe UI', 11), fieldbackground=bg_color, bordercolor=border, borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')], foreground=[('selected', 'white')])
        style.configure("Treeview.Heading", background=head_bg, foreground=head_fg, font=('Segoe UI', 12, 'bold'), relief="flat")
        style.map("Treeview.Heading", background=[('active', head_active)])

    # ==========================================
    # ROBUST NUMBER PARSING
    # ==========================================
    def safe_float(self, value):
        """Strips out letters, spaces, and currency symbols so the app never crashes on bad input."""
        if not value: return 0.0
        clean = re.sub(r'[^\d.]', '', str(value))
        if clean.count('.') > 1:
            parts = clean.split('.')
            clean = parts[0] + '.' + ''.join(parts[1:])
        try:
            return float(clean) if clean else 0.0
        except ValueError:
            return 0.0

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

        self.search_frame = ctk.CTkFrame(self.tab_tenants, fg_color=("#e5e5e5", "#2b2b2b"))
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
            width=120, fg_color=("#d3d3d3", "#565b5e"), hover_color=("#c8c8c8", "#343638"), text_color=("black", "white")
        )
        self.reset_cols_btn.pack(side="right", padx=10, pady=10)

        self.tenant_content = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.tenant_content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.form_frame = ctk.CTkScrollableFrame(self.tenant_content, width=350, label_text="Tenant Details")

        self.contact_var = ctk.StringVar()
        self.contact_var.trace_add("write", self.validate_contact)
        self.monthly_var = ctk.StringVar()
        self.monthly_var.trace_add("write", lambda *args: self.validate_numeric_var(self.monthly_var))

        self.entries = {}
        self.fields = [
            "Status", "Full Name", "Address", "Room Number", "Date Started",
            "Lease Term", "Move Out Date", "Monthly Due", "Rent Due Date", "Valid ID", "Working/Job",
            "Messenger Link", "Email", "Contact Number"
        ]

        for field in self.fields:
            lbl = ctk.CTkLabel(self.form_frame, text=field)
            lbl.pack(anchor="w", padx=10, pady=(5, 0))

            if field in ["Date Started", "Move Out Date"]:
                ent = DateEntry(self.form_frame, width=45, font=('Segoe UI', 11), background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
                ent.pack(padx=10, pady=(0, 5), ipady=4)
                self.entries[field] = ent
            elif field == "Rent Due Date":
                ent = ctk.CTkEntry(self.form_frame, width=300, placeholder_text="e.g., 5 or 21 w/ int.")
                ent.pack(padx=10, pady=(0, 5))
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

        self.save_btn = ctk.CTkButton(self.form_frame, text="Save Tenant", command=self.save_tenant_to_db, fg_color="green", hover_color="darkgreen", text_color="white")
        self.save_btn.pack(pady=20, padx=10, fill="x")

        self.table_frame = ctk.CTkFrame(self.tenant_content)
        self.table_frame.pack(side="right", fill="both", expand=True)

        self.columns = (
            "ID", "Status", "Name", "Address", "Room", "Started", "Term", 
            "Move Out", "Monthly", "Due Date", "Valid ID", "Job", "Messenger", 
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

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy Cell Value", command=self.copy_cell)
        self.tenant_table.bind("<Button-3>", self.show_context_menu)

        self.action_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.view_btn = ctk.CTkButton(self.action_frame, text="View Selected", command=self.view_tenant_details, fg_color="#1f538d", hover_color="#14375e", text_color="white")
        self.view_btn.pack(side="left", padx=(0, 10))
        self.edit_btn = ctk.CTkButton(self.action_frame, text="Edit Selected", command=self.load_for_editing, fg_color="#B8860B", hover_color="#8B6508", text_color="white")
        self.edit_btn.pack(side="left", padx=(0, 10))
        self.delete_btn = ctk.CTkButton(self.action_frame, text="Delete Selected", command=self.delete_tenant, fg_color="#8B0000", hover_color="#660000", text_color="white")
        self.delete_btn.pack(side="left", padx=(0, 10))
        
        self.export_tenants_btn = ctk.CTkButton(self.action_frame, text="Export to CSV", command=lambda: self.export_to_csv('tenants'), fg_color=("#d3d3d3", "#2b2b2b"), hover_color=("#c8c8c8", "#565b5e"), text_color=("black", "white"), border_color="#1f538d", border_width=2)
        self.export_tenants_btn.pack(side="right")

        self.load_tenants_from_db()

    # ==========================================
    # TAB 2: FINANCIALS (LEDGER SYSTEM)
    # ==========================================
    def trigger_ledger_update(self, *args):
        self.ledger_month.set(f"{self.ledger_year_var.get()}-{self.ledger_month_var.get()}")
        self.load_ledger()

    def setup_financials_tab(self):
        self.fin_header = ctk.CTkFrame(self.tab_financials, fg_color="transparent")
        self.fin_header.pack(fill="x", padx=10, pady=10)

        self.fin_title = ctk.CTkLabel(self.fin_header, text="Monthly Rental Report", font=ctk.CTkFont(size=24, weight="bold"))
        self.fin_title.pack(side="left")

        current_year = str(datetime.now().year)
        current_month = str(datetime.now().strftime('%m'))
        
        self.ledger_year_var = ctk.StringVar(value=current_year)
        self.ledger_month_var = ctk.StringVar(value=current_month)
        self.ledger_month = ctk.StringVar(value=f"{current_year}-{current_month}")

        years = [str(y) for y in range(int(current_year) - 2, int(current_year) + 5)]
        months = [str(m).zfill(2) for m in range(1, 13)]

        self.ledger_year_menu = ctk.CTkOptionMenu(self.fin_header, values=years, variable=self.ledger_year_var, command=self.trigger_ledger_update, width=80)
        self.ledger_year_menu.pack(side="right", padx=(5, 10))
        self.ledger_year_menu.set(current_year) 

        self.ledger_month_menu = ctk.CTkOptionMenu(self.fin_header, values=months, variable=self.ledger_month_var, command=self.trigger_ledger_update, width=70)
        self.ledger_month_menu.pack(side="right", padx=(5, 0))
        self.ledger_month_menu.set(current_month) 
        
        ctk.CTkLabel(self.fin_header, text="Select Period:").pack(side="right")

        self.fin_content = ctk.CTkFrame(self.tab_financials, fg_color="transparent")
        self.fin_content.pack(fill="both", expand=True, padx=10, pady=10)

        self.fin_table_frame = ctk.CTkFrame(self.fin_content)
        self.fin_table_frame.pack(fill="both", expand=True)

        self.fin_columns = ("ID", "BEDSPACER", "Due date", "Monthly", "Remarks", "Last Edited")
        self.fin_table = ttk.Treeview(self.fin_table_frame, columns=self.fin_columns, show="headings")
        
        self.fin_scroll_y = ctk.CTkScrollbar(self.fin_table_frame, orientation="vertical", command=self.fin_table.yview)
        self.fin_scroll_y.pack(side="right", fill="y")
        self.fin_table.configure(yscrollcommand=self.fin_scroll_y.set)

        for col in self.fin_columns:
            self.fin_table.heading(col, text=col)
            
        self.fin_table.column("ID", width=0, stretch=False)
        self.fin_table.column("BEDSPACER", width=250, anchor="w")
        self.fin_table.column("Due date", width=120, anchor="center")
        self.fin_table.column("Monthly", width=120, anchor="center")
        self.fin_table.column("Remarks", width=250, anchor="w")
        self.fin_table.column("Last Edited", width=160, anchor="center")

        self.fin_table.pack(fill="both", expand=True)

        self.fin_table.bind("<Double-1>", self.open_remarks_popup)

        self.total_frame = ctk.CTkFrame(self.fin_content, fg_color="transparent")
        self.total_frame.pack(fill="x", pady=10)
        
        self.export_fin_btn = ctk.CTkButton(self.total_frame, text="Export to CSV", command=self.export_ledger_csv, fg_color=("#d3d3d3", "#2b2b2b"), hover_color=("#c8c8c8", "#565b5e"), text_color=("black", "white"), border_color="#1f538d", border_width=2)
        self.export_fin_btn.pack(side="left", padx=10)

        self.edit_remarks_btn = ctk.CTkButton(self.total_frame, text="✏️ Edit Remarks", command=self.open_remarks_popup, fg_color="#B8860B", hover_color="#8B6508", text_color="white", font=ctk.CTkFont(weight="bold"))
        self.edit_remarks_btn.pack(side="left", padx=10)

        self.total_container = ctk.CTkFrame(self.total_frame, fg_color="transparent")
        self.total_container.pack(side="right", padx=50)

        ctk.CTkLabel(self.total_container, text="A. TOTAL = ₱ ", font=("Segoe UI", 20, "bold"), text_color="#8B0000").pack(side="left")

        self.total_entry = ctk.CTkEntry(
            self.total_container, 
            font=("Segoe UI", 20, "bold"), 
            text_color="#8B0000", 
            width=180, 
            justify="center",
            placeholder_text="Enter Total Here"
        )
        self.total_entry.pack(side="left", padx=5)
        
        self.total_entry.bind("<Return>", self.save_manual_total)
        self.total_entry.bind("<FocusOut>", self.save_manual_total)

        self.load_ledger()

    def open_remarks_popup(self, event=None):
        selected = self.fin_table.selection()
        if not selected:
            messagebox.showwarning("Select Tenant", "Please click on a tenant in the list first to edit their remarks.")
            return
            
        item = selected[0]
        vals = self.fin_table.item(item)['values']
        tid = vals[0]
        tenant_name = vals[1]
        
        current_remarks = vals[4] if str(vals[4]) != "None" else ""

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit Remarks")
        dialog.geometry("400x250")
        dialog.attributes("-topmost", True)
        
        ctk.CTkLabel(dialog, text=f"Remarks for: {tenant_name}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        
        rem_entry = ctk.CTkTextbox(dialog, width=350, height=100)
        rem_entry.pack(padx=20, pady=10)
        
        if current_remarks:
            rem_entry.insert("1.0", str(current_remarks))
            
        def save():
            new_rem = rem_entry.get("1.0", "end-1c")
            self.save_ledger_entry(item, dialog, new_rem)
            
        ctk.CTkButton(dialog, text="Save Remarks", command=save, fg_color="green", hover_color="darkgreen", text_color="white").pack(pady=10)

    def save_manual_total(self, event=None):
        month_str = self.ledger_month.get()
        total_val = self.total_entry.get()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"ledger_total_{month_str}", total_val))
        conn.commit()
        conn.close()
        
        self.title("TenantTracker Admin - Saved Total!")
        self.after(1500, lambda: self.title("TenantTracker Admin"))
        self.focus() 

    def load_ledger(self, *args):
        for i in self.fin_table.get_children(): self.fin_table.delete(i)
        
        month_str = self.ledger_month.get()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, full_name, rent_due_date, monthly_due FROM tenants WHERE status='Active'")
        tenants = cursor.fetchall()
        
        for t in tenants:
            tid, name, due_date, monthly = t
            
            monthly_val = self.safe_float(monthly)
            
            cursor.execute("SELECT remarks, last_edited FROM rent_ledger WHERE tenant_id=? AND month_year=?", (tid, month_str))
            ledger_entry = cursor.fetchone()
            
            remarks = ledger_entry[0] if ledger_entry else ""
            last_edited = ledger_entry[1] if ledger_entry and ledger_entry[1] else ""
            
            self.fin_table.insert("", "end", values=(tid, name, due_date, f"₱ {monthly_val:,.2f}", remarks, last_edited))
            
        cursor.execute("SELECT value FROM settings WHERE key=?", (f"ledger_total_{month_str}",))
        saved_total = cursor.fetchone()
        
        self.total_entry.delete(0, 'end')
        if saved_total and saved_total[0]:
            self.total_entry.insert(0, saved_total[0])
            
        conn.close()

    def save_ledger_entry(self, item, dialog_window, rem_text):
        tid = self.fin_table.item(item, "values")[0]
        month_str = self.ledger_month.get()
        timestamp = time.strftime('%Y-%m-%d %I:%M %p')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT id FROM rent_ledger WHERE tenant_id=? AND month_year=?", (tid, month_str))
        exists = c.fetchone()
        
        if exists:
            c.execute("UPDATE rent_ledger SET remarks=?, last_edited=? WHERE id=?", (rem_text, timestamp, exists[0]))
        else:
            c.execute("INSERT INTO rent_ledger (tenant_id, month_year, remarks, last_edited) VALUES (?,?,?,?)", 
                      (tid, month_str, rem_text, timestamp))
        
        conn.commit()
        conn.close()
        
        if dialog_window: 
            dialog_window.destroy()
            
        self.load_ledger()

    def export_ledger_csv(self):
        month_str = self.ledger_month.get()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV Spreadsheet", "*.csv")],
            title="Export Monthly Rental Report",
            initialfile=f"Monthly_Rental_Report_{month_str}.csv"
        )

        if not file_path:
            return

        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                headers = ["BEDSPACER", "Due Date", "Monthly", "Remarks", "Last Edited"]
                writer.writerow(headers)

                for item in self.fin_table.get_children():
                    row_data = self.fin_table.item(item)['values']
                    writer.writerow(row_data[1:]) 

                writer.writerow([])
                
                total_val = self.total_entry.get()
                if not total_val:
                    total_val = "0"
                writer.writerow(["", "", "A. TOTAL =", f"₱ {total_val}", ""])

            messagebox.showinfo("Export Successful", f"Monthly Rental Report neatly formatted and saved to:\n\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export file: {str(e)}")
            # ==========================================
    # TAB 3: MONTHLY SUMMARY (GLORIFIED EXCEL)
    # ==========================================
    def trigger_summary_update(self, *args):
        self.selected_month.set(f"{self.sum_year_var.get()}-{self.sum_month_var.get()}")
        self.load_summary_table()

    def create_total_row(self, parent, label_text, color, suffix=""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label_text, font=("Segoe UI", 14, "bold"), text_color=color, width=170, anchor="e").pack(side="left", padx=5)
        entry = ctk.CTkEntry(row, font=("Segoe UI", 14, "bold"), text_color=color, width=170, justify="center")
        entry.pack(side="left")
        entry.bind("<Return>", self.save_summary_totals)
        entry.bind("<FocusOut>", self.save_summary_totals)
        if suffix:
            ctk.CTkLabel(row, text=suffix, font=("Segoe UI", 13), text_color=color).pack(side="left", padx=5)
        return entry

    def setup_summary_tab(self):
        self.dash_frame = ctk.CTkFrame(self.tab_summary, fg_color="transparent")
        self.dash_frame.pack(fill="x", padx=10, pady=10)
        
        self.header_top = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        self.header_top.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(self.header_top, text="Monthly Expenses & Summary", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        current_year = str(datetime.now().year)
        current_month = str(datetime.now().strftime('%m'))
        
        self.sum_year_var = ctk.StringVar(value=current_year)
        self.sum_month_var = ctk.StringVar(value=current_month)
        self.selected_month = ctk.StringVar(value=f"{current_year}-{current_month}")

        years = [str(y) for y in range(int(current_year) - 2, int(current_year) + 5)]
        months = [str(m).zfill(2) for m in range(1, 13)]

        self.sum_year_menu = ctk.CTkOptionMenu(self.header_top, values=years, variable=self.sum_year_var, command=self.trigger_summary_update, width=80)
        self.sum_year_menu.pack(side="right", padx=(5, 10))
        self.sum_year_menu.set(current_year)

        self.sum_month_menu = ctk.CTkOptionMenu(self.header_top, values=months, variable=self.sum_month_var, command=self.trigger_summary_update, width=70)
        self.sum_month_menu.pack(side="right", padx=(5, 0))
        self.sum_month_menu.set(current_month)
        
        ctk.CTkLabel(self.header_top, text="Select Period:").pack(side="right")

        self.sum_content = ctk.CTkFrame(self.tab_summary, fg_color="transparent")
        self.sum_content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.sum_table_frame = ctk.CTkFrame(self.sum_content)
        self.sum_table_frame.pack(fill="both", expand=True)

        self.sum_cols = ("ID", "Category", "Description", "Amount", "Total", "Remarks / OK")
        self.sum_table = ttk.Treeview(self.sum_table_frame, columns=self.sum_cols, show="headings")
        
        self.sum_scroll_y = ctk.CTkScrollbar(self.sum_table_frame, orientation="vertical", command=self.sum_table.yview)
        self.sum_scroll_y.pack(side="right", fill="y")
        self.sum_table.configure(yscrollcommand=self.sum_scroll_y.set)
        
        for col in self.sum_cols: self.sum_table.heading(col, text=col)
        self.sum_table.column("ID", width=0, stretch=False)
        self.sum_table.column("Category", width=200, anchor="w")
        self.sum_table.column("Description", width=250, anchor="w")
        self.sum_table.column("Amount", width=150, anchor="center")
        self.sum_table.column("Total", width=150, anchor="center")
        self.sum_table.column("Remarks / OK", width=150, anchor="center")
        self.sum_table.pack(fill="both", expand=True)

        self.sum_table.bind("<Double-1>", self.open_summary_edit_popup)

        self.sum_action_frame = ctk.CTkFrame(self.sum_content, fg_color="transparent")
        self.sum_action_frame.pack(fill="x", pady=(10, 0))

        self.add_row_btn = ctk.CTkButton(self.sum_action_frame, text="+ Add Blank Row", command=self.add_summary_row, fg_color="#1f538d", hover_color="#14375e", text_color="white", font=ctk.CTkFont(weight="bold"))
        self.add_row_btn.pack(side="left", padx=(0, 10))

        self.edit_row_btn = ctk.CTkButton(self.sum_action_frame, text="✏️ Edit Row", command=self.open_summary_edit_popup, fg_color="#B8860B", hover_color="#8B6508", text_color="white", font=ctk.CTkFont(weight="bold"))
        self.edit_row_btn.pack(side="left", padx=(0, 10))

        self.del_row_btn = ctk.CTkButton(self.sum_action_frame, text="- Delete Row", command=self.delete_summary_row, fg_color="#8B0000", hover_color="#660000", text_color="white")
        self.del_row_btn.pack(side="left", padx=(0, 10))

        self.export_sum_btn = ctk.CTkButton(self.sum_action_frame, text="Export to CSV", command=self.export_summary_csv, fg_color=("#d3d3d3", "#2b2b2b"), hover_color=("#c8c8c8", "#565b5e"), text_color=("black", "white"), border_color="#1f538d", border_width=2)
        self.export_sum_btn.pack(side="right")

        # BOTTOM COMPUTATIONS & NOTES AREA
        self.bottom_math_frame = ctk.CTkFrame(self.tab_summary, height=220)
        self.bottom_math_frame.pack(fill="x", padx=10, pady=10)

        self.notes_frame = ctk.CTkFrame(self.bottom_math_frame, fg_color="transparent")
        self.notes_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(self.notes_frame, text="Custom Computations & Notes", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.summary_notes_box = ctk.CTkTextbox(self.notes_frame, height=150)
        self.summary_notes_box.pack(fill="both", expand=True)
        self.summary_notes_box.bind("<FocusOut>", self.save_summary_totals)

        self.totals_frame = ctk.CTkFrame(self.bottom_math_frame, fg_color="transparent", width=500)
        self.totals_frame.pack(side="right", fill="y", padx=10, pady=10)

        self.tot_exp_entry = self.create_total_row(self.totals_frame, "C. TOTAL EXPENSES =", "#8B0000")
        
        ctk.CTkLabel(self.totals_frame, text="Total Net Income = A - B - C - D - E", font=("Segoe UI", 11, "italic")).pack(anchor="e", padx=30, pady=(5, 0))
        self.tot_net_entry = self.create_total_row(self.totals_frame, "TOTAL NET INCOME =", "#000000")

        box1 = ctk.CTkFrame(self.totals_frame, fg_color=("#e5e5e5", "#2b2b2b"), corner_radius=5)
        box1.pack(fill="x", pady=(10, 5))
        self.reyan_jp_entry = self.create_total_row(box1, "Reyan & JP tig", "#1f538d") 
        self.ricky_upa_entry = self.create_total_row(box1, "LESS RICKY UPA =", "#565b5e", suffix="for IPE") 

        box2 = ctk.CTkFrame(self.totals_frame, fg_color=("#e5e5e5", "#2b2b2b"), corner_radius=5)
        box2.pack(fill="x", pady=5)
        self.prev_sav_entry = self.create_total_row(box2, "Previous Savings =", "#006400") 
        self.tot_left_entry = self.create_total_row(box2, "Total Savings Left =", "#000000")

        self.load_summary_table()

    def open_summary_edit_popup(self, event=None):
        selected = self.sum_table.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please click on a row first to edit it.")
            return

        item = selected[0]
        vals = self.sum_table.item(item)['values']
        row_id = vals[0]
        
        cat = vals[1] if str(vals[1]) != "None" else ""
        desc = vals[2] if str(vals[2]) != "None" else ""
        amt = vals[3] if str(vals[3]) != "None" else ""
        tot = vals[4] if str(vals[4]) != "None" else ""
        rem = vals[5] if str(vals[5]) != "None" else ""

        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Summary Row")
        dialog.geometry("450x450")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Edit Row Data", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))

        def make_entry(lbl_text, default_val):
            frame = ctk.CTkFrame(dialog, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(frame, text=lbl_text, width=100, anchor="e").pack(side="left", padx=(0, 10))
            ent = ctk.CTkEntry(frame, width=250)
            ent.pack(side="left")
            ent.insert(0, default_val)
            return ent

        ent_cat = make_entry("Category:", cat)
        ent_desc = make_entry("Description:", desc)
        ent_amt = make_entry("Amount:", amt)
        ent_tot = make_entry("Total:", tot)
        ent_rem = make_entry("Remarks / OK:", rem)

        def save():
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute('''
                UPDATE summary_rows 
                SET col_category=?, col_description=?, col_amount=?, col_total=?, col_remarks=? 
                WHERE id=?
            ''', (ent_cat.get(), ent_desc.get(), ent_amt.get(), ent_tot.get(), ent_rem.get(), row_id))
            conn.commit()
            conn.close()
            dialog.destroy()
            self.load_summary_table()

        ctk.CTkButton(dialog, text="Save Changes", command=save, fg_color="green", hover_color="darkgreen", text_color="white").pack(pady=20)

    def load_summary_table(self):
        for i in self.sum_table.get_children(): self.sum_table.delete(i)
        
        month_str = self.selected_month.get()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, col_category, col_description, col_amount, col_total, col_remarks FROM summary_rows WHERE month_year=?", (month_str,))
        rows = cursor.fetchall()

        if not rows:
            template = [
                (month_str, "MAYNILAD", "HOUSE A", "", "", ""),
                (month_str, "", "HOUSE B", "", "", ""),
                (month_str, "", "HOUSE C", "", "", ""),
                (month_str, "MERALCO", "HOUSE A", "", "", ""),
                (month_str, "", "HOUSE B", "", "", ""),
                (month_str, "CONVERGE", "MONTHLY FEE", "", "", ""),
                (month_str, "MONTHLY SAVINGS", "", "", "", ""),
                (month_str, "MAINTENANCE", "REYAN", "", "", ""),
                (month_str, "PICK UP BASURA", "200/week", "", "", ""),
                (month_str, "D. REFUND NG UMALIS", "none", "", "", ""),
                (month_str, "E. REWARD NG NAG REFER", "", "", "", ""),
                (month_str, "F. MISCELLANEOUS", "celyn banyo pagkain pasahe", "", "", ""),
                (month_str, "", "pagkain /pamasahe", "", "", ""),
                (month_str, "", "Total", "", "", "")
            ]
            cursor.executemany("INSERT INTO summary_rows (month_year, col_category, col_description, col_amount, col_total, col_remarks) VALUES (?, ?, ?, ?, ?, ?)", template)
            conn.commit()
            
            cursor.execute("SELECT id, col_category, col_description, col_amount, col_total, col_remarks FROM summary_rows WHERE month_year=?", (month_str,))
            rows = cursor.fetchall()

        for row in rows:
            self.sum_table.insert("", "end", values=row)

        def _load_field(key, widget):
            cursor.execute("SELECT value FROM settings WHERE key=?", (f"{key}_{month_str}",))
            res = cursor.fetchone()
            widget.delete(0, 'end')
            if res and res[0]: widget.insert(0, res[0])

        cursor.execute("SELECT value FROM settings WHERE key=?", (f"sum_notes_{month_str}",))
        notes = cursor.fetchone()
        self.summary_notes_box.delete("1.0", "end")
        if notes and notes[0]: self.summary_notes_box.insert("1.0", notes[0])

        _load_field("sum_exp", self.tot_exp_entry)
        _load_field("sum_net", self.tot_net_entry)
        _load_field("sum_reyan_jp", self.reyan_jp_entry)
        _load_field("sum_ricky_upa", self.ricky_upa_entry)
        _load_field("sum_prev_sav", self.prev_sav_entry)
        _load_field("sum_left", self.tot_left_entry)

        conn.close()

    def add_summary_row(self):
        month_str = self.selected_month.get()
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("INSERT INTO summary_rows (month_year, col_category, col_description, col_amount, col_total, col_remarks) VALUES (?, '', '', '', '', '')", (month_str,))
        conn.commit()
        conn.close()
        self.load_summary_table()

    def delete_summary_row(self):
        selected = self.sum_table.selection()
        if not selected: return
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this row from the summary?")
        if confirm:
            row_id = self.sum_table.item(selected[0])['values'][0]
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("DELETE FROM summary_rows WHERE id=?", (row_id,))
            conn.commit()
            conn.close()
            self.load_summary_table()

    def save_summary_totals(self, event=None):
        month_str = self.selected_month.get()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"sum_notes_{month_str}", self.summary_notes_box.get("1.0", "end-1c")))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"sum_exp_{month_str}", self.tot_exp_entry.get()))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"sum_net_{month_str}", self.tot_net_entry.get()))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"sum_reyan_jp_{month_str}", self.reyan_jp_entry.get()))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"sum_ricky_upa_{month_str}", self.ricky_upa_entry.get()))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"sum_prev_sav_{month_str}", self.prev_sav_entry.get()))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"sum_left_{month_str}", self.tot_left_entry.get()))
        
        conn.commit()
        conn.close()
        self.title("TenantTracker Admin - Saved Totals!")
        self.after(1500, lambda: self.title("TenantTracker Admin"))

    def export_summary_csv(self):
        month_str = self.selected_month.get()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV Spreadsheet", "*.csv")],
            title="Export Monthly Summary",
            initialfile=f"Monthly_Summary_{month_str}.csv"
        )
        if not file_path: return

        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(self.sum_cols[1:]) 

                for item in self.sum_table.get_children():
                    row_data = self.sum_table.item(item)['values']
                    writer.writerow(row_data[1:]) 

                writer.writerow([])
                writer.writerow(["", "", "C. TOTAL EXPENSES =", self.tot_exp_entry.get()])
                writer.writerow(["", "", "Total Net Income =", "A - B - C - D - E"])
                writer.writerow(["", "", "TOTAL NET INCOME =", self.tot_net_entry.get()])
                writer.writerow([])
                writer.writerow(["", "", "Reyan & JP tig", self.reyan_jp_entry.get()])
                writer.writerow(["", "", "LESS RICKY UPA =", self.ricky_upa_entry.get(), "for IPE"])
                writer.writerow([])
                writer.writerow(["", "", "Previous Savings =", self.prev_sav_entry.get()])
                writer.writerow(["", "", "Total Savings Left =", self.tot_left_entry.get()])
                writer.writerow([])
                writer.writerow(["Custom Computations & Notes:"])
                for line in self.summary_notes_box.get("1.0", "end-1c").split('\n'):
                    writer.writerow([line])

            messagebox.showinfo("Export Successful", f"Summary cleanly exported to:\n\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export file: {str(e)}")

    # ==========================================
    # TAB 4: SETTINGS & BACKUPS
    # ==========================================
    def setup_settings_tab(self):
        self.set_header = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.set_header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.set_header, text="System Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        self.set_content = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.set_content.pack(fill="both", expand=True, padx=10, pady=10)

        self.left_settings = ctk.CTkScrollableFrame(self.set_content, width=450)
        self.left_settings.pack(side="left", fill="y", padx=(0, 10), expand=True)

        ctk.CTkLabel(self.left_settings, text="Preferences", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 10), anchor="w", padx=10)
        
        ctk.CTkLabel(self.left_settings, text="UI Theme Appearance").pack(anchor="w", padx=10)
        self.theme_var = ctk.StringVar(value=self.app_settings.get("theme", "System"))
        self.theme_menu = ctk.CTkOptionMenu(self.left_settings, values=["System", "Dark", "Light"], variable=self.theme_var, command=self.change_theme)
        self.theme_menu.pack(anchor="w", padx=10, pady=(0, 20))

        ctk.CTkLabel(self.left_settings, text="Email Automations (For Reminders)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 10), anchor="w", padx=10)
        
        ctk.CTkLabel(self.left_settings, text="Sender Email Address").pack(anchor="w", padx=10)
        self.email_entry = ctk.CTkEntry(self.left_settings, width=350)
        self.email_entry.insert(0, self.app_settings.get("sender_email", ""))
        self.email_entry.pack(anchor="w", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.left_settings, text="App Password (Not your normal password)").pack(anchor="w", padx=10)
        self.pass_entry = ctk.CTkEntry(self.left_settings, width=350, show="*")
        self.pass_entry.insert(0, self.app_settings.get("sender_password", ""))
        self.pass_entry.pack(anchor="w", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.left_settings, text="Send Reminder How Many Days Before Due?").pack(anchor="w", padx=10)
        self.days_combo = ctk.CTkComboBox(self.left_settings, values=["1", "2", "3", "5", "7", "10"], width=350)
        self.days_combo.set(self.app_settings.get("reminder_days", "3"))
        self.days_combo.pack(anchor="w", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.left_settings, text="Custom Email Template").pack(anchor="w", padx=10)
        ctk.CTkLabel(self.left_settings, text="Use exact tags: {name}, {amount}, {date}", text_color="gray", font=ctk.CTkFont(size=11, slant="italic")).pack(anchor="w", padx=10)
        self.template_box = ctk.CTkTextbox(self.left_settings, width=350, height=120)
        
        default_template = "Hi {name},\n\nThis is a friendly reminder from management that your rent of ₱{amount} is due on {date}.\n\nPlease ensure your payment is ready.\n\nThank you!"
        saved_template = self.app_settings.get("email_template", default_template)
        self.template_box.insert("1.0", saved_template)
        self.template_box.pack(anchor="w", padx=10, pady=(0, 20))

        self.save_settings_btn = ctk.CTkButton(self.left_settings, text="Save Email & Automation Settings", command=self.save_app_settings, fg_color="green", hover_color="darkgreen", text_color="white")
        self.save_settings_btn.pack(anchor="w", padx=10, pady=10)

        # TEST EMAIL BUTTON
        self.test_email_btn = ctk.CTkButton(self.left_settings, text="Test Email Connection", command=self.send_test_email, fg_color="#B8860B", hover_color="#8B6508", text_color="white")
        self.test_email_btn.pack(anchor="w", padx=10, pady=10)

        # THE REAL BUTTON: Process and Send to Tenants
        self.send_reminders_btn = ctk.CTkButton(self.left_settings, text="🚀 Scan & Send Reminders Now", command=self.send_real_reminders, fg_color="#8B0000", hover_color="#660000", text_color="white", font=ctk.CTkFont(weight="bold"))
        self.send_reminders_btn.pack(anchor="w", padx=10, pady=(10, 20))

        self.right_settings = ctk.CTkFrame(self.set_content, width=400)
        self.right_settings.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(self.right_settings, text="Data Security & Backups", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 15), anchor="w", padx=20)
        
        backup_desc = ctk.CTkLabel(self.right_settings, text="Create a secure portable ZIP file containing your database and all uploaded ID pictures. Keep this safe on a USB drive!", wraplength=350, justify="left")
        backup_desc.pack(anchor="w", padx=20, pady=(0, 10))

        self.backup_btn = ctk.CTkButton(self.right_settings, text="💾 Create Full System Backup", command=self.create_backup, fg_color="#B8860B", hover_color="#8B6508", text_color="white", font=ctk.CTkFont(weight="bold"))
        self.backup_btn.pack(anchor="w", padx=20, pady=10)

        restore_desc = ctk.CTkLabel(self.right_settings, text="Restore your entire system from a previously saved backup file. WARNING: This will overwrite all current data!", wraplength=350, justify="left", text_color="#8B0000")
        restore_desc.pack(anchor="w", padx=20, pady=(15, 10))

        self.restore_btn = ctk.CTkButton(self.right_settings, text="📂 Restore from Backup", command=self.restore_backup, fg_color="#8B0000", hover_color="#660000", text_color="white", font=ctk.CTkFont(weight="bold"))
        self.restore_btn.pack(anchor="w", padx=20, pady=(0, 10))

    # --- Settings Functions ---
    def change_theme(self, new_theme):
        ctk.set_appearance_mode(new_theme)
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?)", (new_theme,))
        conn.commit()
        conn.close()
        self.apply_table_theme()

    def save_app_settings(self):
        email = self.email_entry.get()
        password = self.pass_entry.get()
        days = self.days_combo.get()
        template = self.template_box.get("1.0", "end-1c")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sender_email', ?)", (email,))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sender_password', ?)", (password,))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('reminder_days', ?)", (days,))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('email_template', ?)", (template,))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Success", "Email configuration and reminder settings saved securely.")

    def create_backup(self):
        folder = filedialog.askdirectory(title="Select Backup Folder")
        if not folder: return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(folder, f"TenantTracker_Backup_{timestamp}.zip")

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                if os.path.exists(DB_PATH): backup_zip.write(DB_PATH, os.path.basename(DB_PATH))
                if os.path.exists(UPLOADS_DIR):
                    for root, dirs, files in os.walk(UPLOADS_DIR):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, BASE_DIR)
                            backup_zip.write(file_path, arcname)
            messagebox.showinfo("Backup Successful!", f"System completely backed up to:\n\n{zip_path}")
        except Exception as e:
            messagebox.showerror("Backup Failed", f"An error occurred: {str(e)}")

    def restore_backup(self):
        zip_path = filedialog.askopenfilename(title="Select Backup ZIP File", filetypes=[("ZIP Files", "*.zip")])
        if not zip_path: return

        confirm = messagebox.askyesno("WARNING: OVERWRITE DATA", "Are you sure you want to restore from this backup?\n\nThis will OVERWRITE your current database and all images. ALL changes made since this backup will be permanently lost!", icon="warning")
        if confirm:
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(BASE_DIR)
                messagebox.showinfo("Restore Successful", "Backup has been restored successfully! The application will now close to apply changes.")
                self.destroy()
                sys.exit()
            except Exception as e:
                messagebox.showerror("Restore Failed", f"An error occurred: {str(e)}")
                # ==========================================
    # HELPER AND GLOBAL FUNCTIONS
    # ==========================================
    def get_active_tenant_names(self):
        conn = sqlite3.connect(DB_PATH)
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

    def upload_id_image(self):
        file_path = filedialog.askopenfilename(title="Select ID Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            filename = f"{int(time.time())}.jpg"
            destination = os.path.join(UPLOADS_DIR, filename)
            
            try:
                img = Image.open(file_path)
                img.convert("RGB").save(destination, "JPEG", optimize=True, quality=75)
                
                ent = self.entries["Valid ID"]
                ent.configure(state="normal")
                ent.delete(0, 'end')
                ent.insert(0, destination)
                ent.configure(state="readonly")
            except Exception as e:
                messagebox.showerror("Image Error", f"Could not process image: {str(e)}")

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
        ctk.CTkButton(win, text="Close Window", command=win.destroy, fg_color=("#d3d3d3", "#565b5e"), hover_color=("#c8c8c8", "#343638"), text_color=("black", "white")).pack(pady=(10, 20))

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
        widths = {"ID": 40, "Status": 80, "Name": 180, "Address": 280, "Room": 60, "Started": 100, "Term": 80, "Move Out": 100, "Monthly": 90, "Due Date": 100, "Valid ID": 130, "Job": 140, "Messenger": 180, "Email": 220, "Contact": 120, "Notes": 250, "Agreement": 80, "Advance": 80, "Deposit": 80, "Last Edited": 170}
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
            row_vals = self.tenant_table.item(selected[0])['values']
            t_id = row_vals[0]
            valid_id_path = row_vals[10]
            
            if valid_id_path and str(valid_id_path) != "None" and os.path.exists(valid_id_path):
                try:
                    os.remove(valid_id_path)
                except Exception:
                    pass

            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("DELETE FROM tenants WHERE id = ?", (t_id,))
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

        conn = sqlite3.connect(DB_PATH)
        if self.editing_tenant_id:
            data.append(self.editing_tenant_id)
            conn.cursor().execute('''UPDATE tenants SET status=?, full_name=?, address=?, room_number=?, date_started=?, lease_term=?, move_out_date=?, monthly_due=?, rent_due_date=?, valid_id=?, job=?, messenger_link=?, email=?, contact_number=?, notes=?, agreement_signed=?, advance_paid=?, deposit_paid=?, last_edited=? WHERE id=?''', data)
        else:
            conn.cursor().execute('''INSERT INTO tenants (status, full_name, address, room_number, date_started, lease_term, move_out_date, monthly_due, rent_due_date, valid_id, job, messenger_link, email, contact_number, notes, agreement_signed, advance_paid, deposit_paid, last_edited) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()
        conn.close()
        self.clear_form()
        self.load_tenants_from_db()
        self.toggle_form()

    def load_tenants_from_db(self):
        for i in self.tenant_table.get_children(): self.tenant_table.delete(i)
        conn = sqlite3.connect(DB_PATH)
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

    # ==========================================
    # EMAIL AUTOMATION ENGINE
    # ==========================================
    def send_test_email(self):
        email_addr = self.email_entry.get()
        app_pass = self.pass_entry.get()

        if not email_addr or not app_pass:
            messagebox.showerror("Missing Info", "Please enter your Gmail Address and Google App Password first.")
            return

        try:
            self.test_email_btn.configure(text="Connecting to Gmail...", state="disabled")
            self.update()

            msg = EmailMessage()
            msg.set_content("Success! Your TenantTracker email system is fully connected and ready to send reminders.")
            msg['Subject'] = "TenantTracker System Test"
            msg['From'] = email_addr
            msg['To'] = email_addr 

            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(email_addr, app_pass)
            server.send_message(msg)
            server.quit()
            
            self.test_email_btn.configure(text="Test Email Connection", state="normal")
            messagebox.showinfo("Success!", "Test email sent successfully! Check your inbox.")
        except Exception as e:
            self.test_email_btn.configure(text="Test Email Connection", state="normal")
            messagebox.showerror("Email Error", f"Connection failed. Please ensure you generated a Google APP PASSWORD (not your normal password).\n\nError: {str(e)}")

    def send_real_reminders(self):
        email_addr = self.email_entry.get()
        app_pass = self.pass_entry.get()
        days_notice = int(self.days_combo.get())
        template = self.template_box.get("1.0", "end-1c")

        if not email_addr or not app_pass:
            messagebox.showerror("Error", "Please configure your email settings first.")
            return

        confirm = messagebox.askyesno("Confirm Automation", f"Are you sure you want to scan the database and send emails to tenants whose rent is due in {days_notice} days?")
        if not confirm: return

        # 1. Get today's day of the month
        current_day = int(datetime.now().strftime("%d"))
        target_due_day = current_day + days_notice

        # Handle end of month rollover
        if target_due_day > 30: 
            target_due_day = target_due_day - 30

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, monthly_due, rent_due_date, email FROM tenants WHERE status='Active'")
        tenants = cursor.fetchall()
        conn.close()

        sent_count = 0
        errors = []

        self.send_reminders_btn.configure(text="Sending Emails...", state="disabled")
        self.update()

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(email_addr, app_pass)

            for t in tenants:
                name, monthly, due_date_str, t_email = t
                
                if not t_email or str(t_email) == "None" or not due_date_str:
                    continue

                try:
                    due_day = int(re.search(r'\d+', str(due_date_str)).group())
                    
                    if due_day == target_due_day:
                        msg = EmailMessage()
                        
                        custom_msg = template.replace("{name}", str(name))
                        custom_msg = custom_msg.replace("{amount}", f"{self.safe_float(monthly):,.2f}")
                        custom_msg = custom_msg.replace("{date}", f"the {due_day}th")
                        
                        msg.set_content(custom_msg)
                        msg['Subject'] = "Upcoming Rent Reminder - TenantTracker"
                        msg['From'] = email_addr
                        msg['To'] = t_email

                        server.send_message(msg)
                        sent_count += 1
                        
                except Exception as parse_err:
                    errors.append(f"Could not read due date for {name}")

            server.quit()

            self.send_reminders_btn.configure(text="🚀 Scan & Send Reminders Now", state="normal")
            
            if sent_count > 0:
                messagebox.showinfo("Complete!", f"Successfully sent {sent_count} reminder email(s)!")
            else:
                messagebox.showinfo("Scan Complete", f"No tenants have rent due in exactly {days_notice} days. 0 emails sent.")
                
            if errors:
                print("Reminder Errors:", errors) 

        except Exception as e:
            self.send_reminders_btn.configure(text="🚀 Scan & Send Reminders Now", state="normal")
            messagebox.showerror("Error", f"An error occurred while sending: {str(e)}")


if __name__ == "__main__":
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        lock_socket.bind(('127.0.0.1', 47200)) 
    except socket.error:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("App Already Running", "TenantTracker is already open!\n\nPlease check your taskbar. Running two windows at the same time can break your database.")
        sys.exit()

    app = TenantTrackerApp()
    app.mainloop()